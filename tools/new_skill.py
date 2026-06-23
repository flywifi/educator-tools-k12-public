#!/usr/bin/env python3
"""Scaffold a new TOS skill from the standard template, with synced references.

Usage: python3 tools/new_skill.py <skill-name>

Creates skills/<skill-name>/ from tools/skill-template/, fills in the skill name,
and copies the canonical synced references named in tools/sync_manifest.json so the
new skill passes tools/sync_check.py immediately.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "skill-template"
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "tools" / "sync_manifest.json"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python3 tools/new_skill.py <skill-name>")
        return 2
    name = argv[0].strip().strip("/")
    if not name or not all(c.isalnum() or c == "-" for c in name):
        print(f"[!] invalid skill name: {name!r} (use lowercase letters, digits, hyphens)")
        return 2

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

    print(f"created {dest.relative_to(ROOT)} (synced refs: {', '.join(synced) or 'none'})")
    print("next: edit SKILL.md + references/artifact-types.md + MAINTAINER.md (fill the <…> placeholders),")
    print("      then run: python3 tools/sync_check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
