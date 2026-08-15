#!/usr/bin/env python3
"""Ecosystem version registry — list + check consistency (offline, stdlib).

Reads versions.json (the single source of truth), the root VERSION file, and .claude-plugin/
(plugin.json AND marketplace.json) and verifies they agree and that the skill list matches what's
installed. Run in CI / before a release so versions never drift. tools/rollback.py uses this
registry to restore a component to a prior version.

Version numbers are gated HERE; the generated descriptions/catalog are gated by
tools/export_plugin_manifest.py (sync_check check 21) — two tools, one authority each.

Usage:
  python3 tools/version.py --list
  python3 tools/version.py --check     # non-zero exit on any mismatch
  python3 tools/version.py --bump <skill|engine|ecosystem> <semver>
  python3 tools/version.py --self-test # fixture probes (offline; CI)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_SEMVER = re.compile(r"\d+\.\d+\.\d+")


def _paths(root: Path) -> dict[str, Path]:
    return {"versions": root / "versions.json",
            "version_file": root / "VERSION",
            "plugin": root / ".claude-plugin" / "plugin.json",
            "marketplace": root / ".claude-plugin" / "marketplace.json",
            "skills": root / "skills"}


def _load(root: Path) -> dict:
    return json.loads(_paths(root)["versions"].read_text(encoding="utf-8"))


def check(root: Path | None = None) -> dict:
    p = _paths(root or ROOT)
    v = _load(root or ROOT)
    issues = []
    eco = v.get("ecosystem")
    # A MISSING file is an issue, never a silent pass: an exists() guard here once meant a
    # deleted VERSION or plugin.json would sail through CI reporting "ok".
    if not p["version_file"].exists():
        issues.append("VERSION file missing")
    elif p["version_file"].read_text(encoding="utf-8").strip() != eco:
        issues.append(f"VERSION file ({p['version_file'].read_text(encoding='utf-8').strip()}) "
                      f"!= versions.json ecosystem ({eco})")
    if not p["plugin"].exists():
        issues.append(".claude-plugin/plugin.json missing")
    else:
        pv = json.loads(p["plugin"].read_text(encoding="utf-8")).get("version")
        if pv != eco:
            issues.append(f".claude-plugin/plugin.json version ({pv}) != ecosystem ({eco})")
    # marketplace.json carries TWO version fields that were bumped by hand at every release and
    # checked by nothing — the 15-vs-62-skills listing survived two releases because of it.
    if not p["marketplace"].exists():
        issues.append(".claude-plugin/marketplace.json missing")
    else:
        mk = json.loads(p["marketplace"].read_text(encoding="utf-8"))
        mv = mk.get("metadata", {}).get("version")
        if mv != eco:
            issues.append(f"marketplace.json metadata.version ({mv}) != ecosystem ({eco})")
        for i, entry in enumerate(mk.get("plugins", [])):
            if entry.get("version") != eco:
                issues.append(f"marketplace.json plugins[{i}].version "
                              f"({entry.get('version')}) != ecosystem ({eco})")
    # Skills are sub-grouped (core/ educator/ operations/ atoms/) — every dir holding a SKILL.md.
    on_disk = ({q.parent.name for q in p["skills"].rglob("SKILL.md")}
               if p["skills"].exists() else set())
    listed = set(v.get("skills", {}))
    for missing in sorted(on_disk - listed):
        issues.append(f"skill '{missing}' installed but missing from versions.json")
    for extra in sorted(listed - on_disk):
        issues.append(f"skill '{extra}' in versions.json but not installed")
    return {"ecosystem": eco, "skills": len(listed), "engines": len(v.get("engines", {})),
            "issues": issues, "status": "ok" if not issues else "mismatch"}


def bump(name: str, semver: str, root: Path | None = None) -> dict:
    p = _paths(root or ROOT)
    if not _SEMVER.fullmatch(semver):
        return {"status": "error",
                "detail": f"'{semver}' is not X.Y.Z semver (no 'v' prefix, no prerelease tags)"}
    v = _load(root or ROOT)
    if name == "ecosystem":
        v["ecosystem"] = semver
        # `updated` accompanies every ecosystem bump. It sat at the 1.1.0 date through the 1.2.0
        # release because no tool wrote it (the 1.1.0 commit message claimed this tool did).
        v["updated"] = date.today().isoformat()
        p["version_file"].write_text(semver + "\n", encoding="utf-8")
        if p["plugin"].exists():
            pl = json.loads(p["plugin"].read_text(encoding="utf-8"))
            pl["version"] = semver
            p["plugin"].write_text(json.dumps(pl, indent=2) + "\n", encoding="utf-8")
    elif name in v.get("skills", {}):
        v["skills"][name] = semver
    elif name in v.get("engines", {}):
        v["engines"][name] = semver
    else:
        return {"status": "error", "detail": f"unknown target '{name}'"}
    p["versions"].write_text(json.dumps(v, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok", "bumped": name, "to": semver}


def release(spec: str, root: Path | None = None) -> dict:
    """One-command release: the whole chain moves together, or nothing does.

    Replaces the manual dance that shipped real drift twice (5 version fields across 4 files,
    marketplace 'by hand', versions.json `updated` forgotten at 1.2.0): computes the next semver
    (`patch`/`minor`/`major`, or an explicit X.Y.Z), bumps ecosystem (versions.json + updated +
    VERSION + plugin.json), regenerates every generated manifest/description/catalog via
    export_plugin_manifest, and rolls changelog `[Unreleased]` into a dated release section.
    Refuses an EMPTY [Unreleased]: a release with no recorded changes is a numbering mistake.
    Never commits — a human (or the autobump workflow) reviews and commits the printed file list.
    Installed plugins update on version bumps, so this command is what actually ships."""
    r = root or ROOT
    p = _paths(r)
    cur = _load(r).get("ecosystem", "")
    if spec in ("patch", "minor", "major"):
        if not _SEMVER.fullmatch(cur):
            return {"status": "error", "detail": f"current ecosystem '{cur}' is not X.Y.Z"}
        ma, mi, pa = (int(x) for x in cur.split("."))
        new = {"patch": f"{ma}.{mi}.{pa + 1}", "minor": f"{ma}.{mi + 1}.0",
               "major": f"{ma + 1}.0.0"}[spec]
    elif _SEMVER.fullmatch(spec):
        new = spec
    else:
        return {"status": "error",
                "detail": f"'{spec}' is neither patch/minor/major nor X.Y.Z"}
    log = r / "changes" / "CHANGELOG.md"
    text = log.read_text(encoding="utf-8")
    m = re.search(r"^## \[Unreleased\]\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    if not m:
        return {"status": "error", "detail": "changes/CHANGELOG.md has no [Unreleased] section"}
    if not m.group(1).strip():
        return {"status": "error",
                "detail": "[Unreleased] is empty — a release with no recorded changes is a "
                          "numbering mistake; write the changelog entry first"}
    rep = bump("ecosystem", new, r)
    if rep["status"] != "ok":
        return rep
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import export_plugin_manifest
    export_plugin_manifest.write(r)
    stamp = f"## [{new}] — {date.today().isoformat()}"
    text = log.read_text(encoding="utf-8")
    text = text.replace("## [Unreleased]", f"## [Unreleased]\n\n{stamp}", 1)
    log.write_text(text, encoding="utf-8")
    residue = check(r)["issues"] + export_plugin_manifest.check(r)
    files = ["VERSION", "versions.json", ".claude-plugin/plugin.json",
             ".claude-plugin/marketplace.json", "skills/README.md", "changes/CHANGELOG.md"]
    return {"status": "ok" if not residue else "error", "released": new,
            "commit_these": files, "residue": residue}


# --------------------------------------------------------------------------------------- self-test
def self_test() -> int:
    """Fixture probes. Every check is demonstrated able to FAIL (the broken-twin rule)."""
    import shutil
    import tempfile
    fails = 0

    def ck(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    tmp = Path(tempfile.mkdtemp(prefix="version-st-"))
    (tmp / ".claude-plugin").mkdir()
    (tmp / "skills" / "core" / "hub").mkdir(parents=True)
    (tmp / "skills" / "core" / "hub" / "SKILL.md").write_text("---\nname: hub\n---\n",
                                                              encoding="utf-8")

    def reset() -> None:
        (tmp / "versions.json").write_text(json.dumps(
            {"ecosystem": "1.0.0", "updated": "2020-01-01",
             "skills": {"hub": "1.0.0"}, "engines": {"eng": "0.1.0"}}), encoding="utf-8")
        (tmp / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (tmp / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "x", "version": "1.0.0"}), encoding="utf-8")
        (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
            {"name": "m", "metadata": {"version": "1.0.0"},
             "plugins": [{"name": "x", "version": "1.0.0"}]}), encoding="utf-8")

    def issues() -> list[str]:
        return check(tmp)["issues"]

    reset()
    ck("clean twin passes everything", issues() == [])

    reset()
    (tmp / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    ck("VERSION != ecosystem flagged", any("VERSION file (9.9.9)" in i for i in issues()))

    reset()
    pl = {"name": "x", "version": "9.9.9"}
    (tmp / ".claude-plugin" / "plugin.json").write_text(json.dumps(pl), encoding="utf-8")
    ck("plugin.json version drift flagged", any("plugin.json version" in i for i in issues()))

    reset()
    mk = json.loads((tmp / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    mk["metadata"]["version"] = "9.9.9"
    (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(mk), encoding="utf-8")
    ck("marketplace metadata.version drift flagged",
       any("metadata.version" in i for i in issues()))

    reset()
    mk = json.loads((tmp / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    mk["plugins"][0]["version"] = "9.9.9"
    (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(mk), encoding="utf-8")
    ck("marketplace plugins[0].version drift flagged",
       any("plugins[0].version" in i for i in issues()))

    reset()
    (tmp / "VERSION").unlink()
    ck("MISSING VERSION file flagged (no silent pass)",
       any("VERSION file missing" in i for i in issues()))

    reset()
    (tmp / ".claude-plugin" / "plugin.json").unlink()
    ck("MISSING plugin.json flagged (no silent pass)",
       any("plugin.json missing" in i for i in issues()))

    reset()
    (tmp / ".claude-plugin" / "marketplace.json").unlink()
    ck("MISSING marketplace.json flagged", any("marketplace.json missing" in i
                                               for i in issues()))

    reset()
    d = tmp / "skills" / "atoms" / "orphan"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: orphan\n---\n", encoding="utf-8")
    ck("on-disk skill absent from registry flagged",
       any("'orphan' installed but missing" in i for i in issues()))
    shutil.rmtree(tmp / "skills" / "atoms")

    reset()
    v = json.loads((tmp / "versions.json").read_text(encoding="utf-8"))
    v["skills"]["ghost"] = "1.0.0"
    (tmp / "versions.json").write_text(json.dumps(v), encoding="utf-8")
    ck("registry skill absent from disk flagged",
       any("'ghost' in versions.json but not installed" in i for i in issues()))

    reset()
    ck("unknown --bump target is an ERROR (was a silent exit-0 no-op)",
       bump("nonsense", "1.0.0", tmp)["status"] == "error")
    ck("malformed semver rejected: 'v1.2.3' / '1.2' / '1.2.3.4'",
       all(bump("ecosystem", s, tmp)["status"] == "error"
           for s in ("v1.2.3", "1.2", "1.2.3.4")))

    # --- release() probes (need a fuller fixture: changelog + generator inputs) ---------------
    reset()
    (tmp / "changes").mkdir(exist_ok=True)
    (tmp / "ledger").mkdir(exist_ok=True)
    (tmp / "ledger" / "cpalms-run-manifest.json").write_text(
        json.dumps({"totals": {"verified": 7}}), encoding="utf-8")
    (tmp / "skills" / "README.md").write_text(
        "# cat\n<!-- BEGIN GENERATED: skills-catalog -->\n"
        "<!-- END GENERATED: skills-catalog -->\n", encoding="utf-8")
    (tmp / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "x", "version": "1.0.0", "description": "old"}), encoding="utf-8")
    (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"name": "m", "metadata": {"version": "1.0.0"},
         "plugins": [{"name": "x", "version": "1.0.0", "description": "old"}]}),
        encoding="utf-8")
    (tmp / "changes" / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] — 2026-01-01\n- old\n", encoding="utf-8")
    ck("release: refuses an EMPTY [Unreleased] (a bumped nothing is a numbering mistake)",
       release("patch", tmp)["status"] == "error")

    (tmp / "changes" / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n### Added\n- a thing\n\n## [1.0.0] — 2026-01-01\n- old\n",
        encoding="utf-8")
    rep = release("patch", tmp)
    log = (tmp / "changes" / "CHANGELOG.md").read_text(encoding="utf-8")
    mk = json.loads((tmp / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    ck("release: patch computes 1.0.1, regenerates manifests, rolls the changelog, no residue",
       rep["status"] == "ok" and rep["released"] == "1.0.1"
       and f"## [1.0.1] — {date.today().isoformat()}" in log
       and "## [Unreleased]" in log and log.index("[Unreleased]") < log.index("[1.0.1]")
       and "- a thing" in log.split("[1.0.1]")[1]
       and mk["metadata"]["version"] == "1.0.1" and mk["plugins"][0]["version"] == "1.0.1"
       and "7 FL standards" in mk["plugins"][0]["description"])
    ck("release: second release without new changelog content is refused (fresh [Unreleased] "
       "is empty)", release("patch", tmp)["status"] == "error")
    ck("release: bad spec rejected", release("banana", tmp)["status"] == "error")
    (tmp / "changes" / "CHANGELOG.md").write_text(
        "# C\n\n## [Unreleased]\n- more\n\n## [1.0.1] — x\n", encoding="utf-8")
    ck("release: explicit X.Y.Z accepted", release("2.0.0", tmp).get("released") == "2.0.0")

    reset()
    rep = bump("ecosystem", "1.0.1", tmp)
    v = json.loads((tmp / "versions.json").read_text(encoding="utf-8"))
    ck("bump ecosystem writes VERSION + plugin.json + versions.json AND stamps `updated` today",
       rep["status"] == "ok"
       and (tmp / "VERSION").read_text(encoding="utf-8").strip() == "1.0.1"
       and json.loads((tmp / ".claude-plugin" / "plugin.json")
                      .read_text(encoding="utf-8"))["version"] == "1.0.1"
       and v["ecosystem"] == "1.0.1" and v["updated"] == date.today().isoformat())

    shutil.rmtree(tmp)
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Ecosystem version registry (offline).")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--bump", nargs=2, metavar=("TARGET", "SEMVER"))
    ap.add_argument("--release", metavar="PATCH|MINOR|MAJOR|X.Y.Z",
                    help="one-command release: bump chain + regenerate manifests + roll changelog")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.release:
        rep = release(a.release.lower() if a.release.lower() in ("patch", "minor", "major")
                      else a.release)
        print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "ok" else 1
    if a.bump:
        rep = bump(*a.bump)
        print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "ok" else 1
    if a.check:
        rep = check()
        print(json.dumps(rep, indent=2))
        return 1 if rep["issues"] else 0
    print(json.dumps(_load(ROOT), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
