#!/usr/bin/env python3
"""Manifest-driven sync for the Local-First cache (L3) — Scoop-bucket model, human-approved.

Keeps the local L1/L2 standards cache fresh and portable by tying together the pieces that already
exist instead of inventing a new fetcher:

  * UPSTREAM freshness (web sources: CPALMS/FLDOE/WIDA/...) is checked by the F2 engine
    `tools/source_currency.py` — conditional GET (ETag/Last-Modified) + content sha256 + supersession
    keywords. Changes are ADVISORY + human-verified; baselines only move with `--update-baselines`.
  * LOCAL freshness (the enumerated data files vs the built index) comes from the L1 cache's own
    sha256 baseline (`shared/cache` drift_report) — tells us exactly when to rebuild.
  * PORTABILITY is a Scoop-style **bucket manifest**: a small JSON listing every cached resource with
    its sha256 + size + version, so the corpus can be distributed and re-verified offline (the same
    `version` + `hash` model Scoop app manifests use).

Human-approved by default: `--sync` is a dry-run plan; rebuilding the index needs `--apply`; moving
upstream baselines stays behind `source_currency.py --update-baselines`. Nothing is fabricated.

Usage:
  python3 tools/sync_cache.py --status                 # combined upstream + local + L2 view (offline-ok)
  python3 tools/sync_cache.py --manifest [--write P]   # emit/save the Scoop-style bucket manifest
  python3 tools/sync_cache.py --sync                   # dry-run plan: what would rebuild / re-verify
  python3 tools/sync_cache.py --apply                  # rebuild the L1 index (+ L2 if opted-in & ready)
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "shared" / "cache"
DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
MANIFEST_VERSION = "0.1.0"

# Reuse the engines rather than reimplementing them.
sys.path.insert(0, str(CACHE_DIR))
sys.path.insert(0, str(ROOT / "tools"))
import cache as l1            # noqa: E402  shared/cache/cache.py
import semantic as l2         # noqa: E402  shared/cache/semantic.py
import source_currency        # noqa: E402  tools/source_currency.py


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------- Scoop-style bucket manifest
def bucket_manifest() -> dict:
    """A portable, hash-verified description of the local cached corpus (Scoop app-manifest shape)."""
    resources = []
    for f in l1._source_files():
        resources.append({
            "path": str(f.relative_to(ROOT)),
            "sha256": l1._sha256(f),
            "bytes": f.stat().st_size,
        })
    drift = l1.drift_report()
    return {
        "name": "florida-standards-cache",
        "version": MANIFEST_VERSION,
        "generated": _now(),
        "source_dir": str(DATA.relative_to(ROOT)) if DATA.exists() else None,
        "resource_count": len(resources),
        "resources": resources,
        "index": {"built": drift["built"], "stale": drift["stale"]},
        "rebuild": "python3 shared/cache/cache.py --build",
        "advisory": "standards are authoritative on CPALMS; this manifest verifies the local copy only",
    }


# --------------------------------------------------------------- combined status
def status(offline: bool, timeout: int) -> dict:
    drift = l1.drift_report()
    sem = l2.capability_status()
    # Upstream currency is best-effort: offline mode (age-only) or a network check; never fabricate.
    # Reuse source_currency's own computed tallies rather than recomputing them.
    try:
        upstream = source_currency.check(domain=None, offline=offline, timeout=timeout)
        states = upstream.get("state_counts", {})
        up = {"checked": True, "offline": offline, "states": states,
              "stale_count": upstream.get("stale_count", 0),
              "stale_sources": [s.get("id") for s in upstream.get("stale_sources", [])]}
        if states.get("uncertain"):
            up["note"] = ("some sources are 'uncertain' — baselines not yet seeded; run "
                          "tools/source_currency.py --update-baselines (human-approved) to enable "
                          "change detection")
    except Exception as e:  # network/egress/registry issues must degrade honestly
        up = {"checked": False, "offline": offline, "error": str(e),
              "note": "run tools/source_currency.py --summary for detail"}
    return {
        "local_cache": {"built": drift["built"], "stale": drift["stale"],
                        "changed": drift.get("changed", []), "added": drift.get("added", []),
                        "removed": drift.get("removed", [])},
        "semantic_l2": {"ready": sem["ready"], "reason": sem["reason"],
                        "consent": sem["consent"]},
        "upstream_sources": up,
        "human_review_required": True,
    }


# --------------------------------------------------------------- sync plan / apply
def sync(apply: bool) -> dict:
    drift = l1.drift_report()
    plan: list[str] = []
    actions: list[str] = []

    if not drift["built"]:
        plan.append("L1 index not built — will build from canonical JSON")
    elif drift["stale"]:
        moved = drift.get("changed", []) + drift.get("added", []) + drift.get("removed", [])
        plan.append(f"L1 index stale ({', '.join(moved) or 'source set changed'}) — will rebuild")
    else:
        plan.append("L1 index current — no rebuild needed")

    sem = l2.capability_status()
    rebuild_l2 = sem["ready"] and (drift["stale"] or not drift["built"])
    if sem["ready"]:
        plan.append("L2 opted-in & ready — will rebuild vector index alongside L1" if rebuild_l2
                    else "L2 opted-in & ready — current")
    else:
        plan.append(f"L2 skipped ({sem['reason']})")

    if apply:
        # Capture the sub-tools' human output so this orchestrator emits clean JSON.
        if not drift["built"] or drift["stale"]:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = l1.build()
            actions.append(f"cache.build rc={rc}")
        if rebuild_l2:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = l2.build()
            actions.append(f"semantic.build rc={rc}")
        if not actions:
            actions.append("nothing to do — cache already current")

    return {"mode": "apply" if apply else "dry-run", "plan": plan, "actions": actions,
            "upstream_note": "to re-verify/refresh authoritative web sources, run "
                             "tools/source_currency.py --summary then --update-baselines (human-approved)",
            "human_review_required": True}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Manifest-driven sync for the Local-First cache (L3)")
    ap.add_argument("--status", action="store_true", help="combined upstream + local + L2 view")
    ap.add_argument("--manifest", action="store_true", help="emit the Scoop-style bucket manifest")
    ap.add_argument("--write", metavar="PATH", help="with --manifest: write the manifest to PATH")
    ap.add_argument("--sync", action="store_true", help="dry-run plan of what would be rebuilt")
    ap.add_argument("--apply", action="store_true", help="rebuild the L1 index (+ L2 if ready)")
    ap.add_argument("--offline", action="store_true", help="status: age-only upstream triage, no network")
    ap.add_argument("--timeout", type=int, default=20)
    a = ap.parse_args(argv)

    if a.manifest:
        m = bucket_manifest()
        if a.write:
            Path(a.write).write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "manifest_written", "path": a.write,
                              "resources": m["resource_count"]}, indent=2))
        else:
            print(json.dumps(m, indent=2))
        return 0
    if a.status:
        print(json.dumps(status(a.offline, a.timeout), indent=2, ensure_ascii=False))
        return 0
    if a.sync or a.apply:
        print(json.dumps(sync(apply=a.apply), indent=2, ensure_ascii=False))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
