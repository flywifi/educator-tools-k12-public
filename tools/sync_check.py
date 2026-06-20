#!/usr/bin/env python3
"""Drift guard for the TOS SKILL.md ecosystem.

Asserts INVARIANTS (not textual diffs) so that:
  - the governed core (shared/, protocols/) and each skill's synced copies can
    never silently diverge, and
  - every skill honors the Quality Gates repository invariants and governance wiring.

Uses an invariants-based approach (assert invariants, not textual diffs; exit codes).

Run:   python3 tools/sync_check.py
Exit:  0 if every invariant holds, 1 (with a report) otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "tools" / "sync_manifest.json"

# Quality Gates §96 repository invariants (canonical phrases) must appear in the
# authoritative quality files.
REPO_INVARIANTS = [
    "Integrity precedes approval",
    "Evidence precedes certification",
    "Validation precedes release",
    "Audits remain independent",
    "Critical failures block approval",
    "Repository history remains traceable",
    "Quality decisions remain auditable",
    "Certification requires evidence",
]
INVARIANT_FILES = [ROOT / "protocols" / "quality-gates.md", ROOT / "QUALITY_MODEL.md"]

# Markers every SKILL.md must contain: the pipeline pointer, the metadata schema,
# and the always-on human-review flag.
REQUIRED_IN_SKILL = ["method.md", "metadata-schema.md", "human_review_required"]

# Tokens that must never ship inside a skill's markdown.
FORBIDDEN = ["TODO", "FIXME", "PLACEHOLDER", "<<<<<<<", ">>>>>>>"]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    # 0. Manifest + canonical sources exist.
    if not MANIFEST.exists():
        print(f"[!] Missing manifest: {MANIFEST}")
        return 1
    synced = json.loads(read(MANIFEST)).get("synced_references", {})
    canonical: dict[str, str] = {}
    for refname, relpath in synced.items():
        cpath = ROOT / relpath
        if not cpath.exists():
            failures.append(f"  x canonical source missing: {relpath} (for {refname})")
        else:
            canonical[refname] = read(cpath)

    # 1. Repository invariants present in the authoritative quality files.
    for f in INVARIANT_FILES:
        if not f.exists():
            failures.append(f"  x invariant file missing: {f.relative_to(ROOT)}")
            continue
        text = read(f)
        for inv in REPO_INVARIANTS:
            if inv not in text:
                failures.append(f'  x invariant absent: "{inv}" not in {f.relative_to(ROOT)}')

    # Per-skill checks.
    skill_dirs = sorted(d for d in SKILLS.iterdir() if d.is_dir()) if SKILLS.exists() else []
    for sd in skill_dirs:
        rel = sd.relative_to(ROOT)
        skillmd = sd / "SKILL.md"
        if not skillmd.exists():
            failures.append(f"  x {rel}: missing SKILL.md")
            continue
        body = read(skillmd)

        # 2. Synced references present and byte-identical to canon.
        for refname, content in canonical.items():
            rpath = sd / "references" / refname
            if not rpath.exists():
                failures.append(f"  x {rel}: missing synced reference references/{refname}")
            elif read(rpath) != content:
                failures.append(f"  x {rel}: references/{refname} drifted from {synced[refname]}")

        # 3-5. Required governance/pipeline wiring in SKILL.md.
        for marker in REQUIRED_IN_SKILL:
            if marker not in body:
                failures.append(f"  x {rel}: SKILL.md does not reference '{marker}'")

        # 6. No forbidden tokens anywhere in the skill's markdown.
        for md in sorted(sd.rglob("*.md")):
            mtext = read(md)
            for tok in FORBIDDEN:
                if tok in mtext:
                    failures.append(f"  x {md.relative_to(ROOT)}: forbidden token '{tok}'")

    print("TOS ecosystem - drift guard\n")
    if failures:
        print("DRIFT / INVARIANT FAILURES:\n")
        print("\n".join(failures))
        print(
            f"\n{len(failures)} check(s) failed. Edit the canonical file in shared/ or protocols/ "
            "and re-sync; do not hand-edit synced copies."
        )
        return 1

    print(
        f"OK - {len(skill_dirs)} skill(s) checked; {len(REPO_INVARIANTS)} repository invariants "
        f"present; {len(canonical)} synced reference(s) in sync."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
