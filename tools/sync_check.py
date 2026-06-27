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
import re
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
INVARIANT_FILES = [ROOT / "protocol-layer" / "quality-gates.md", ROOT / "docs" / "QUALITY_MODEL.md"]

# Markers every SKILL.md must contain: the pipeline pointer, the metadata schema,
# and the always-on human-review flag.
REQUIRED_IN_SKILL = ["method.md", "metadata-schema.md", "human_review_required"]

# Every skill ships update instructions (MAINTAINER.md) with these sections (lowercased match),
# so skills stay consistent and route conflicts through the canonical resolver (tools/skill-maintenance.md).
REQUIRED_IN_MAINTAINER = [
    "non-negotiable invariants", "known failure modes", "regression cases",
    "approval-gated", "minority-report", "update checklist",
]

# Tokens that must never ship inside a skill's markdown.
FORBIDDEN = ["TODO", "FIXME", "PLACEHOLDER", "<<<<<<<", ">>>>>>>"]

# SKILL.md frontmatter rules (Claude Skill spec): only these top-level keys are allowed,
# name is hyphen-case <=64, description is <=1024 chars with no angle brackets.
ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata"}
MAX_NAME, MAX_DESC = 64, 1024

# Resource-integrity: backticked repo paths in a SKILL.md must exist. A reference is valid if it
# resolves under the skill dir OR the repo root (so skill-local `examples/...` and repo-root
# `shared/...` both work). Conservative anchors/extensions on purpose; assets/ is intentionally
# excluded (output templates may be absent by design).
_REF_ANCHORS = ("references/", "scripts/", "evals/", "examples/",
                "protocol-layer/", "protocols/", "shared/", "tools/", "ledger/")
_REF_EXTS = (".md", ".py", ".json", ".yaml", ".yml", ".txt", ".csv")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def parse_frontmatter(body: str):
    """Return (frontmatter_text|None, keys, name, description) for a SKILL.md body."""
    m = re.match(r"^---\n(.*?)\n---", body, re.DOTALL)
    if not m:
        return None, [], None, None
    fm = m.group(1)
    keys = re.findall(r"^([A-Za-z0-9_-]+):", fm, re.MULTILINE)
    nm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    dm = re.search(r"^description:\s*(.+)$", fm, re.DOTALL | re.MULTILINE)
    name = nm.group(1).strip().strip('"').strip("'") if nm else None
    desc = dm.group(1).strip().strip('"').strip("'") if dm else None
    return fm, keys, name, desc


def validate_frontmatter(name, desc, keys, folder: str) -> list[str]:
    out: list[str] = []
    if name is None:
        out.append("frontmatter missing 'name'")
    else:
        if name != folder:
            out.append(f"frontmatter name '{name}' != folder '{folder}'")
        if not re.match(r"^[a-z0-9-]+$", name) or "--" in name or name[0] == "-" or name[-1] == "-":
            out.append(f"name '{name}' is not clean hyphen-case")
        if len(name) > MAX_NAME:
            out.append(f"name >{MAX_NAME} chars ({len(name)})")
    if desc is None:
        out.append("frontmatter missing 'description'")
    else:
        if len(desc) > MAX_DESC:
            out.append(f"description >{MAX_DESC} chars ({len(desc)})")
        if "<" in desc or ">" in desc:
            out.append("description contains angle brackets (< or >)")
    bad = sorted(set(keys) - ALLOWED_FRONTMATTER)
    if bad:
        out.append("unexpected frontmatter key(s): " + ", ".join(bad))
    return out


def check_references(sd: Path, text: str) -> list[str]:
    """Every backticked repo path with a known extension must resolve to a real file
    (under the skill dir or the repo root)."""
    out: list[str] = []
    for tok in re.findall(r"`([^`]+)`", text):
        tok = tok.strip()
        if "/" not in tok or not tok.endswith(_REF_EXTS):
            continue
        if any(c in tok for c in "<>*| "):
            continue
        if not tok.startswith(_REF_ANCHORS):
            continue
        if (sd / tok).exists() or (ROOT / tok).exists():
            continue
        out.append(f"broken reference: `{tok}`")
    return out


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

    # Per-skill checks. Skills are now sub-grouped (core/, educator/, operations/, atoms/);
    # find every directory that contains a SKILL.md, recursively.
    skill_dirs = sorted(p.parent for p in SKILLS.rglob("SKILL.md")) if SKILLS.exists() else []
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

        # 7. SKILL.md frontmatter is a valid Claude Skill header.
        fm, keys, name, desc = parse_frontmatter(body)
        if fm is None:
            failures.append(f"  x {rel}: SKILL.md has no YAML frontmatter")
        else:
            for w in validate_frontmatter(name, desc, keys, sd.name):
                failures.append(f"  x {rel}: {w}")

        # 8. Resource integrity: referenced repo files must exist.
        for w in check_references(sd, body):
            failures.append(f"  x {rel}: {w}")

        # 9. Update instructions: a MAINTAINER.md with the required sections must exist.
        maint = sd / "MAINTAINER.md"
        if not maint.exists():
            failures.append(f"  x {rel}: missing MAINTAINER.md (update instructions; see tools/skill-maintenance.md)")
        else:
            low = read(maint).lower()
            for marker in REQUIRED_IN_MAINTAINER:
                if marker not in low:
                    failures.append(f"  x {rel}: MAINTAINER.md missing section '{marker}'")

    # 10. Routing integrity: every shared/routing/routing.json target is a real skill (or the fallback).
    routing_path = ROOT / "shared" / "routing" / "routing.json"
    if routing_path.exists():
        rj = json.loads(read(routing_path))
        skill_names = {d.name for d in skill_dirs}  # leaf names are stable after sub-grouping
        fallback = rj.get("fallback", "manual_review")
        targets = set(rj.get("skills", {})) | set(rj.get("meeting_routes", {}).values())
        for t in sorted(targets):
            if t != fallback and t not in skill_names:
                failures.append(f"  x routing.json: route target '{t}' is not an installed skill")

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
        f"present; {len(canonical)} synced reference(s) in sync; frontmatter + resource integrity OK; "
        f"MAINTAINER.md present in all skills."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
