#!/usr/bin/env python3
"""Ecosystem version registry — list + check consistency (offline, stdlib).

Reads versions.json (the single source of truth), the root VERSION file, and .claude-plugin/plugin.json
and verifies they agree and that the skill list matches what's installed. Run in CI / before a release so
versions never drift. tools/rollback.py uses this registry to restore a component to a prior version.

Usage:
  python3 tools/version.py --list
  python3 tools/version.py --check     # non-zero exit on any mismatch
  python3 tools/version.py --bump <skill|engine|ecosystem> <semver>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / "versions.json"
VERSION_FILE = ROOT / "VERSION"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
SKILLS = ROOT / "skills"


def _load() -> dict:
    return json.loads(VERSIONS.read_text(encoding="utf-8"))


def check() -> dict:
    v = _load()
    issues = []
    eco = v.get("ecosystem")
    if VERSION_FILE.exists() and VERSION_FILE.read_text(encoding="utf-8").strip() != eco:
        issues.append(f"VERSION file ({VERSION_FILE.read_text(encoding='utf-8').strip()}) != versions.json ecosystem ({eco})")
    if PLUGIN.exists():
        pv = json.loads(PLUGIN.read_text(encoding="utf-8")).get("version")
        if pv != eco:
            issues.append(f".claude-plugin/plugin.json version ({pv}) != ecosystem ({eco})")
    # Skills are sub-grouped (core/ educator/ operations/ atoms/) — find every dir holding a SKILL.md.
    on_disk = {p.parent.name for p in SKILLS.rglob("SKILL.md")} if SKILLS.exists() else set()
    listed = set(v.get("skills", {}))
    for missing in sorted(on_disk - listed):
        issues.append(f"skill '{missing}' installed but missing from versions.json")
    for extra in sorted(listed - on_disk):
        issues.append(f"skill '{extra}' in versions.json but not installed")
    return {"ecosystem": eco, "skills": len(listed), "engines": len(v.get("engines", {})),
            "issues": issues, "status": "ok" if not issues else "mismatch"}


def bump(name: str, semver: str) -> dict:
    v = _load()
    if name == "ecosystem":
        v["ecosystem"] = semver
        VERSION_FILE.write_text(semver + "\n", encoding="utf-8")
        if PLUGIN.exists():
            p = json.loads(PLUGIN.read_text(encoding="utf-8"))
            p["version"] = semver
            PLUGIN.write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    elif name in v.get("skills", {}):
        v["skills"][name] = semver
    elif name in v.get("engines", {}):
        v["engines"][name] = semver
    else:
        return {"status": "error", "detail": f"unknown target '{name}'"}
    VERSIONS.write_text(json.dumps(v, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok", "bumped": name, "to": semver}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Ecosystem version registry (offline).")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--bump", nargs=2, metavar=("TARGET", "SEMVER"))
    a = ap.parse_args(argv)
    if a.bump:
        print(json.dumps(bump(*a.bump), indent=2))
        return 0
    if a.check:
        rep = check()
        print(json.dumps(rep, indent=2))
        return 1 if rep["issues"] else 0
    print(json.dumps(_load(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
