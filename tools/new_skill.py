#!/usr/bin/env python3
"""Scaffold a new TOS skill from the standard template, with synced references.

Usage:
  python3 tools/new_skill.py <skill-name>                        # → skills/<skill-name>/
  python3 tools/new_skill.py --group atoms <skill-name>          # → skills/atoms/<skill-name>/
  python3 tools/new_skill.py --group educator <skill-name>       # → skills/educator/<skill-name>/
  python3 tools/new_skill.py --group operations <skill-name>     # → skills/operations/<skill-name>/
  python3 tools/new_skill.py --group core <skill-name>           # → skills/core/<skill-name>/

Creates the skill directory from tools/skill-template/, fills in the skill name,
and copies the canonical synced references named in tools/sync_manifest.json so the
new skill passes tools/sync_check.py immediately.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "skill-template"
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "tools" / "sync_manifest.json"

VALID_GROUPS = {"core", "educator", "operations", "atoms"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new TOS skill.")
    ap.add_argument("name", help="skill name (lowercase, hyphens ok)")
    ap.add_argument("--group", choices=sorted(VALID_GROUPS), default=None,
                    help="sub-group directory (core, educator, operations, atoms)")
    a = ap.parse_args(argv)

    name = a.name.strip().strip("/")
    if not name or not all(c.isalnum() or c == "-" for c in name):
        print(f"[!] invalid skill name: {name!r} (use lowercase letters, digits, hyphens)")
        return 2

    if a.group:
        dest = SKILLS / a.group / name
    else:
        dest = SKILLS / name

    if dest.exists():
        print(f"[!] already exists: {dest.relative_to(ROOT)}")
        return 1
    if not TEMPLATE.exists():
        print(f"[!] template missing: {TEMPLATE.relative_to(ROOT)}")
        return 1

    # 1. Copy the template tree.
    shutil.copytree(TEMPLATE, dest)

    # 2. Fill the skill name into SKILL.md and MAINTAINER.md (update instructions).
    for fn in ("SKILL.md", "MAINTAINER.md"):
        f = dest / fn
        if f.exists():
            f.write_text(f.read_text(encoding="utf-8").replace("__SKILL_NAME__", name),
                         encoding="utf-8")

    # 3. Copy canonical synced references so the skill is self-contained + drift-clean.
    synced = json.loads(MANIFEST.read_text(encoding="utf-8")).get("synced_references", {})
    refs_dir = dest / "references"
    refs_dir.mkdir(exist_ok=True)
    for refname, relpath in synced.items():
        shutil.copyfile(ROOT / relpath, refs_dir / refname)

    loc = dest.relative_to(ROOT)
    print(f"created {loc} (synced refs: {', '.join(synced) or 'none'})")
    print("next: edit SKILL.md + references/artifact-types.md + MAINTAINER.md (fill the <…> placeholders),")
    print("      then run: python3 tools/sync_check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
