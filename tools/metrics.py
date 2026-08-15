#!/usr/bin/env python3
"""Phase E analytics — compute TOS success metrics and write METRICS.md.

Reads the artifact registry (shared/ontology/artifact-types.json), the Quality Ledger
(ledger/ledger.json), the skill directories, the protocol layer, and the differentiation
engine, then renders the success-metric dashboard (build outline section 10 / Charter section 22).

Usage:
  python3 tools/metrics.py            # writes METRICS.md
  python3 tools/metrics.py --print    # also print the dashboard
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
REGISTRY = ROOT / "shared" / "ontology" / "artifact-types.json"
LEDGER = ROOT / "ledger" / "ledger.json"
PROTOCOLS = ROOT / "protocol-layer"
DIFF = ROOT / "shared" / "differentiation"


def has_md(d: Path) -> bool:
    return d.exists() and any(d.glob("*.md"))



def _verified_coverage() -> str:
    """Live standards-verification coverage, computed from the CPALMS overlays themselves so the
    dashboard can never drift from the data (tools/cpalms_verify.py writes them; the parsed corpus
    is never mutated). Reported as verified/total per subject — never as a quality claim."""
    fl = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
    parts, gaps, total_v, total_r = [], [], 0, 0
    for subj in ("math", "ela", "science", "social_studies", "computer_science", "eld"):
        corpus = fl / f"{subj}.json"
        if not corpus.exists():
            continue
        std = json.loads(corpus.read_text(encoding="utf-8")).get("standards", [])
        ov = fl / "overlays" / f"{subj}.cpalms.json"
        entries = (json.loads(ov.read_text(encoding="utf-8")).get("entries", {})
                   if ov.exists() else {})
        done = set(entries)
        codes = {e["code"] for e in std}
        # VERIFIED is strictly narrower than DEALT WITH: an entry recorded as near_match,
        # statement_differs, ambiguous or not_on_cpalms was reached and judged, but it is NOT a
        # verification and must never be counted as coverage.
        verified = {c for c, e in entries.items()
                    if c in codes and e.get("state") == "confirmed"}
        n_v, n_c = len(verified), len(codes)
        total_v += n_v
        n_rev = len((codes & done) - verified)
        total_r += n_rev
        parts.append(f"{subj.replace('_', ' ')} {n_v}/{n_c} ({100 * n_v / max(1, n_c):.1f}%)"
                     + (f" +{n_rev} needing review" if n_rev else ""))
        # Per-subject remaining gap, COMPUTED — never asserted. Two shipped mistakes shaped this
        # line: a whole-corpus "elementary complete" claim went out while 189 K-5 computer-science
        # codes were unverified, and later a hardcoded "grades 6-12 not yet verified" tail kept
        # re-asserting incomplete coverage on every regeneration after the sweep had finished.
        # Nothing here may state a scope's status that the overlays do not prove.
        n_gap = len(codes - verified)
        if n_gap:
            gaps.append(f"{subj.replace('_', ' ')} {n_gap}")
    if not parts:
        return "none yet"
    status = ("all subjects fully verified" if not gaps and total_r == 0
              else "still unverified: " + ", ".join(gaps) + " code(s)" if gaps
              else "all reached; review pending")
    return (f"{total_v} FL codes verified code-by-code against CPALMS "
            f"(+{total_r} reached but needing human review, not counted as verified) — "
            + "; ".join(parts) + f" — {status} "
            "(live breakdown: `ledger/cpalms-run-manifest.json`, authoritative over this line)")

def render() -> str:
    """Compute the dashboard and return it as Markdown text (pure — no file write).
    Split out of main() so tools/sync_check.py can compare committed vs. freshly-rendered
    METRICS.md without writing the file (the freshness gate, check 16)."""
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    frameworks = reg.get("frameworks", [])
    artifact_types = sorted({t for ts in reg.get("skills", {}).values() for t in ts})

    # Skills are sub-grouped (core/ educator/ operations/ atoms/) — every dir holding a SKILL.md.
    skill_dirs = sorted((p.parent for p in SKILLS.rglob("SKILL.md")), key=lambda p: p.name)
    rows = []
    for sd in skill_dirs:
        tmpl = has_md(sd / "assets" / "templates")
        ex = has_md(sd / "examples")
        evals = sd / "evals" / "evals.json"
        n_eval = 0
        if evals.exists():
            try:
                n_eval = len(json.loads(evals.read_text(encoding="utf-8")).get("evals", []))
            except json.JSONDecodeError:
                n_eval = 0
        skillmd = sd / "SKILL.md"
        hr = skillmd.exists() and "human_review_required" in skillmd.read_text(encoding="utf-8")
        rows.append((sd.name, tmpl, ex, n_eval, hr))

    decisions = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    n_dec = len(decisions)
    n_appr = sum(1 for d in decisions if d.get("decision") == "Approved")
    appr_rate = (100 * n_appr / n_dec) if n_dec else 0.0

    protocols = sorted(p.name for p in PROTOCOLS.glob("*.md"))
    diff_engines = sorted(p.stem for p in DIFF.glob("*.md"))

    n_skills = len(skill_dirs)
    n_capable = sum(1 for (_, t, e, n, _) in rows if t and e and n > 0)
    n_hr = sum(1 for r in rows if r[4])
    n_eval_total = sum(r[3] for r in rows)

    out: list[str] = []
    out.append("# METRICS.md")
    out.append("## TOS success-metric dashboard")
    out.append(f"_Generated by `tools/metrics.py` on {date.today().isoformat()}. Do not hand-edit._\n")
    out.append("| Metric | Value |")
    out.append("|---|---|")
    out.append(f"| Skills | {n_skills} |")
    out.append(f"| Artifact types (registry) | {len(artifact_types)} |")
    out.append(f"| Skills with template + example + eval | {n_capable}/{n_skills} |")
    out.append(f"| Eval cases (total) | {n_eval_total} |")
    out.append(f"| Standards frameworks wired | {len(frameworks)} ({', '.join(frameworks)}) |")
    out.append(f"| Standards verified against CPALMS | {_verified_coverage()} |")
    out.append(f"| Differentiation engines | {len(diff_engines)} ({', '.join(diff_engines)}) |")
    out.append(f"| Governance protocols | {len(protocols)}/6 |")
    out.append(f"| Quality coverage (ledger approval rate) | {appr_rate:.0f}% ({n_appr}/{n_dec}) |")
    out.append(f"| AI-safety: skills emitting human_review_required | {n_hr}/{n_skills} |")
    out.append("")
    out.append("## Per-skill coverage")
    out.append("| Skill | template | example | eval cases | human_review |")
    out.append("|---|---|---|---|---|")
    for (name, t, e, n, hr) in rows:
        out.append(f"| `{name}` | {'yes' if t else '—'} | {'yes' if e else '—'} | {n} | {'yes' if hr else '—'} |")
    out.append("")
    out.append("## Mapping to charter success metrics (outline §10 / Charter §22)")
    out.append("- **Artifact Coverage** → artifact types + skills with template/example/eval.")
    out.append("- **Standards Coverage** → frameworks wired (state corpora added as a data task).")
    out.append("- **Differentiation Coverage** → differentiation engines + per-skill differentiation.")
    out.append("- **Quality Coverage** → ledger approval rate (Approved, no critical failure).")
    out.append("- **Governance Coverage** → protocols present + the drift guard (`tools/sync_check.py`).")
    out.append("- **AI-Safety Coverage** → human_review_required across skills + placeholders-only design.")
    out.append("")
    out.append("> Note: hub/governance skills (`teacher-core`, `quality-review`) intentionally have no")
    out.append("> output templates — the template/example metric targets artifact-producing skills.")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    (ROOT / "docs" / "METRICS.md").write_text(text, encoding="utf-8")
    n_skills = sum(1 for _ in SKILLS.rglob("SKILL.md"))
    print(f"wrote docs/METRICS.md — {n_skills} skills, {len(text)} bytes")
    if "--print" in argv:
        print("\n" + text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
