#!/usr/bin/env python3
"""Package a TOS skill into an installable .skill bundle (a zip).

Validates the skill (SKILL.md present with name + description frontmatter and the required
governance markers), then zips the skill directory into dist/<name>.skill.

Usage:
  python3 tools/package_skill.py <skill-name>
  python3 tools/package_skill.py --all
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"

REQUIRED_MARKERS = ["method.md", "metadata-schema.md", "human_review_required"]


def validate(skill_dir: Path) -> list[str]:
    """Return a list of problems (empty = valid)."""
    problems: list[str] = []
    skillmd = skill_dir / "SKILL.md"
    if not skillmd.exists():
        return [f"missing SKILL.md"]
    text = skillmd.read_text(encoding="utf-8")
    if not text.startswith("---"):
        problems.append("SKILL.md missing YAML frontmatter")
    if "name:" not in text.split("---", 2)[1 if text.startswith("---") else 0]:
        problems.append("frontmatter missing name:")
    if "description:" not in text:
        problems.append("frontmatter missing description:")
    for m in REQUIRED_MARKERS:
        if m not in text:
            problems.append(f"SKILL.md does not reference '{m}'")
    return problems


def package(skill_dir: Path) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill_dir.name}.skill"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file() and f.name != ".gitkeep":
                z.write(f, f.relative_to(skill_dir.parent))
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 tools/package_skill.py <skill-name> | --all")
        return 2

    targets = (
        sorted(d for d in SKILLS.iterdir() if d.is_dir())
        if argv[0] == "--all"
        else [SKILLS / argv[0]]
    )

    rc = 0
    for sd in targets:
        if not sd.exists():
            print(f"  x {sd.name}: not found")
            rc = 1
            continue
        problems = validate(sd)
        if problems:
            print(f"  x {sd.name}: " + "; ".join(problems))
            rc = 1
            continue
        out = package(sd)
        size = out.stat().st_size
        print(f"  ok {sd.name} -> {out.relative_to(ROOT)} ({size} bytes)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
