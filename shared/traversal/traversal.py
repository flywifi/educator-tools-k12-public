#!/usr/bin/env python3
"""Traversal + evidence-accumulation engine (offline, stdlib) — Area 2 of the capability roadmap.

Takes multiple inputs (uploaded files, connector hits, record ids, prior findings) and **recursively
expands** them into a growing, provenance-tagged evidence envelope that downstream skills consume. It is
a **companion pass**: append-only, never overwrites upstream facts, records gaps instead of guessing, and
hands off without owning the final interpretation. Adapts the mature traversal-companion design (seed
manifest -> layered traverse -> graph + evidence + gaps -> handoff) to TOS sources (docintel files,
connectors, records, standards), with a **sequential, checkpointed loop** that stops on saturation, a
depth cap (~4 meaningful layers), or a size cap, then gates to a human.

Core (Finding/Seed/TraversalState/run_traversal/to_envelope) has NO dependencies; fetchers are injected.
A docintel file-fetcher + a router-based handoff are provided as optional helpers.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_STATES = ("referenced", "metadata_only", "content_ingested", "local_artifact_saved")
DEFAULT_MAX_LAYERS = 4   # the mature system's "~4 meaningful layers before asking to go deeper"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Seed:
    seed_id: str
    seed_type: str                       # file | connector | record | url | person | query | other
    value: str
    source_hint: Optional[str] = None
    discovered_from: Optional[str] = None
    confidence: str = "medium"


@dataclass
class Finding:
    finding_id: str
    summary: str
    source: str                          # which source/skill produced it
    added_by: str                        # the fetcher/skill that added it (provenance)
    confidence: str = "medium"
    locator: Optional[str] = None
    retrieval_state: str = "content_ingested"
    layer: int = 0


@dataclass
class FetchResult:
    findings: List[Finding] = field(default_factory=list)
    seeds: List[Seed] = field(default_factory=list)     # newly discovered seeds (recursion)
    gaps: List[dict] = field(default_factory=list)


# A fetcher takes a Seed and returns a FetchResult. Fetchers are injected so the core stays dependency-free.
Fetcher = Callable[[Seed], FetchResult]


@dataclass
class TraversalState:
    objective: str
    seeds: List[Seed] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    edges: List[dict] = field(default_factory=list)          # relationship graph (duplicate_of, derived_from, ...)
    gaps: List[dict] = field(default_factory=list)
    log: List[dict] = field(default_factory=list)
    visited: set = field(default_factory=set)
    completed_layers: int = 0
    stop_reason: Optional[str] = None
    scheduler: str = "sequential"
    _seen_keys: set = field(default_factory=set)

    def add_finding(self, f: Finding) -> bool:
        """Append-only with dedup. Returns True if new; a duplicate is recorded as a graph edge, never dropped."""
        key = (f.source, " ".join(f.summary.lower().split()))
        if key in self._seen_keys:
            self.edges.append({"edge_type": "duplicate_of", "finding": f.finding_id, "source": f.source})
            return False
        self._seen_keys.add(key)
        self.findings.append(f)
        return True

    def add_gap(self, seed: Seed, reason: str, detail: str = "") -> None:
        self.gaps.append({"seed_id": seed.seed_id, "value": seed.value, "reason": reason, "detail": detail})

    def checkpoint(self) -> dict:
        return {"completed_layers": self.completed_layers, "visited": sorted(self.visited),
                "findings": len(self.findings), "stop_reason": self.stop_reason}


def run_traversal(objective: str, seeds: List[Seed], fetchers: Dict[str, Fetcher],
                  max_layers: int = DEFAULT_MAX_LAYERS, max_findings: int = 200,
                  scheduler: str = "sequential", max_workers: int = 8) -> TraversalState:
    """Sequential (default) or parallel, breadth-first-by-layer traversal that accumulates findings with
    provenance and stops on saturation / depth cap / size cap. In `parallel` mode each layer's
    independent fetches (file reads, connector calls, external searches) run concurrently in a bounded
    ThreadPoolExecutor (I/O-bound), but the state **merge stays single-threaded** after the gather — so
    the dedup reducer is race-free and the result is identical to sequential, just faster. Sequential
    remains the default for stability; parallel is opt-in (the mature traversal-companion rule)."""
    state = TraversalState(objective=objective, seeds=list(seeds), scheduler=scheduler)
    frontier = list(seeds)
    layer = 0

    def _fetch(seed: Seed):
        fetcher = fetchers.get(seed.seed_type)
        if fetcher is None:
            return seed, None, "no_fetcher"
        try:
            return seed, fetcher(seed), None
        except Exception as exc:  # a source failing is a gap, not a crash
            return seed, None, f"{exc.__class__.__name__}: {exc}"

    while frontier:
        if layer >= max_layers:
            state.stop_reason = "depth_cap_reached"
            break
        if len(state.findings) >= max_findings:
            state.stop_reason = "size_cap_reached"
            break
        layer += 1
        new_this_layer, next_frontier = 0, []
        # De-dupe the frontier against visited BEFORE fetching (so parallel workers never double-fetch).
        todo = []
        for seed in frontier:
            if seed.value in state.visited:
                continue
            state.visited.add(seed.value)
            todo.append(seed)
        # Fetch (concurrent I/O when parallel + >1 task), then MERGE single-threaded (race-free reducer).
        if scheduler == "parallel" and len(todo) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(max_workers, len(todo))) as ex:
                results = list(ex.map(_fetch, todo))
        else:
            results = [_fetch(s) for s in todo]
        for seed, result, err in results:
            if result is None:
                state.add_gap(seed, "no_fetcher" if err == "no_fetcher" else "fetch_error", err or "")
                continue
            for f in result.findings:
                f.layer = layer
                if state.add_finding(f):
                    new_this_layer += 1
            next_frontier.extend(result.seeds)
            state.gaps.extend(result.gaps)
        state.completed_layers = layer
        state.log.append({"layer": layer, "expanded": len(todo), "new_findings": new_this_layer,
                          "scheduler": scheduler})
        if new_this_layer == 0:                      # saturation: a layer added nothing new
            state.stop_reason = state.stop_reason or "saturated"
            break
        frontier = [s for s in next_frontier if s.value not in state.visited]
    if state.stop_reason is None:
        state.stop_reason = "frontier_exhausted"
    return state


def _confidence_rollup(findings: List[Finding]) -> str:
    if not findings:
        return "low"
    order = {"low": 0, "medium": 1, "high": 2}
    # Convergence: 2+ corroborating findings raise confidence; a single weak finding stays low.
    best = max(order.get(f.confidence, 1) for f in findings)
    if len(findings) >= 2 and best >= 1:
        best = min(best + 1, 2)
    return ["low", "medium", "high"][best]


def to_envelope(state: TraversalState, best_next_owner: Optional[str] = None) -> dict:
    """The reusable handoff envelope (stable field names) — accumulated evidence + graph + gaps + log."""
    return {
        "skill_metadata": {"engine": "traversal", "schema_version": "0.1.0", "generated_at": _now(),
                           "mode": "companion_pass", "scheduler": state.scheduler},
        "objective": state.objective,
        "seed_manifest": [asdict(s) for s in state.seeds],
        "evidence": [asdict(f) for f in state.findings],
        "relationship_graph": {"edges": state.edges},
        "retrieval_gaps": state.gaps,
        "traversal_log": state.log,
        "checkpoint_state": state.checkpoint(),
        "confidence": _confidence_rollup(state.findings),
        "handoff": {"primary_artifact": "traversal_envelope",
                    "what_this_pass_added": [f.summary for f in state.findings[:10]],
                    "best_next_owner": best_next_owner},
        "human_review_required": True,
    }


# --------------------------------------------------------------------------- optional helpers (lazy deps)
def docintel_file_fetcher() -> Fetcher:
    """A fetcher that reads a file seed via docintel and emits findings (+ discovers attachment seeds)."""
    sys.path.insert(0, str(ROOT / "shared"))
    import docintel  # type: ignore

    pipeline = docintel.Pipeline()

    def fetch(seed: Seed) -> FetchResult:
        path = Path(seed.value)
        if not path.exists() and (ROOT / seed.value).exists():
            path = ROOT / seed.value
        if not path.exists():
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "file_missing", "value": seed.value}])
        doc = pipeline.run(path.read_bytes(), str(path))
        rec = doc.diagnostics.get("recovery", {})
        state = doc.diagnostics.get("retrieval_state", "referenced")
        findings, new_seeds, gaps = [], [], []
        text = " ".join(b.text for _, b in doc.iter_blocks() if b.text)
        if text:
            findings.append(Finding(finding_id=f"{seed.seed_id}:text", summary=text[:280],
                                    source=rec.get("parser", "docintel"), added_by="docintel_file_fetcher",
                                    confidence="high" if state == "content_ingested" else "low",
                                    locator=path.name, retrieval_state=state))
        else:
            gaps.append({"seed_id": seed.seed_id, "reason": rec.get("status", "no_content"),
                         "value": path.name, "capability_gaps": rec.get("capability_gaps", [])})
        # Recursion: email attachments become new file seeds for the next layer.
        for att in (rec.get("email") or {}).get("attachments", []) or []:
            new_seeds.append(Seed(seed_id=f"{seed.seed_id}:att:{att}", seed_type="file", value=att,
                                  source_hint="email_attachment", discovered_from=seed.seed_id, confidence="medium"))
        return FetchResult(findings=findings, seeds=new_seeds, gaps=gaps)

    return fetch


def route_handoff(objective: str) -> Optional[str]:
    """Use the shared router (Area 3) to suggest the best next skill for the accumulated objective."""
    try:
        sys.path.insert(0, str(ROOT / "shared"))
        from routing import router  # type: ignore
        return router.route({"text": objective})["recommended_skill"]
    except Exception:
        return None


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Accumulate evidence across multiple inputs via traversal (offline).")
    ap.add_argument("--objective", default="", help="what the traversal is trying to support")
    ap.add_argument("--file", action="append", dest="files", default=[], help="an input file seed (repeatable)")
    ap.add_argument("--url", action="append", dest="urls", default=[], help="a public URL seed (repeatable)")
    ap.add_argument("--max-layers", type=int, default=DEFAULT_MAX_LAYERS)
    ap.add_argument("--scheduler", choices=["sequential", "parallel"], default="sequential",
                    help="parallel runs each layer's independent fetches concurrently (I/O-bound)")
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument("--rate", type=float, default=5.0, help="max external fetches/sec (token bucket)")
    a = ap.parse_args(argv)
    seeds = [Seed(seed_id=f"f-{i}", seed_type="file", value=f) for i, f in enumerate(a.files, 1)]
    seeds += [Seed(seed_id=f"u-{i}", seed_type="url", value=u) for i, u in enumerate(a.urls, 1)]
    from .parallel_search import RateLimiter, web_fetch_fetcher
    fetchers = {"file": docintel_file_fetcher(), "url": web_fetch_fetcher(RateLimiter(a.rate))}
    state = run_traversal(a.objective, seeds, fetchers, max_layers=a.max_layers,
                          scheduler=a.scheduler, max_workers=a.max_workers)
    env = to_envelope(state, best_next_owner=route_handoff(a.objective))
    print(json.dumps(env, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
