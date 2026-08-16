#!/usr/bin/env python3
"""Stage the Claude Desktop extension bundle (.mcpb) for the TOS MCP server.

Produces `dist/mcpb-staging/` — a self-contained tree that `mcpb pack` (the npm tool
`@anthropic-ai/mcpb`; MAINTAINER runs it, teachers never touch npm) zips into `tos-tools.mcpb`
for one-click install via Claude Desktop Settings → Extensions. The bundle REPLICATES the
repo-relative layout (tools/, canonical-sources/index/, shared/standards/resources/florida/
data/, VERSION), so the stdlib server's `ROOT = parents[1]` path math works unchanged — no
bundle-specific shims to drift.

What ships: the five stdlib tool files, the PREBUILT offline index (building on first run
inside a possibly read-only install dir is strictly worse than ~4 MB zipped), its manifest
(so `index_status` stays honest about staleness), and the FL standards data + overlays that
verify_standards reads. No secrets, no student data — public CPALMS-derived reference data.

Maintainer flow (release step, not CI):
  python3 tools/build_mcpb.py            # stage + verify
  npm i -g @anthropic-ai/mcpb && cd dist/mcpb-staging && mcpb pack   # -> tos-tools.mcpb
  attach tos-tools.mcpb to the GitHub Release

Usage:  python3 tools/build_mcpb.py [--self-test]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "dist" / "mcpb-staging"

SERVER_FILES = ["tools/mcp_server.py", "tools/mcp_tooldefs.py", "tools/offline_index.py",
                "tools/verify_standards.py", "tools/validate_outputs.py"]
DATA_TREES = ["shared/standards/resources/florida/data"]
INDEX_FILES = ["canonical-sources/index/offline.db", "canonical-sources/index/index-manifest.json"]


def _manifest(version: str) -> dict:
    # Shape per the MCPB spec (github.com/modelcontextprotocol/mcpb); `mcpb pack` validates —
    # a shape drift fails loudly at pack time, never silently at a teacher's install.
    #
    # manifest_version 0.3 (was 0.2 at first ship — the spec had moved and nothing here checked).
    # platform_overrides.win32 is the H-4 fix for this leg: python.org's Windows installer ships
    # python.exe and py.exe and NO python3.exe, so a bare "python3" command is a bundle that
    # cannot start on Windows. macOS/Linux keep python3, where "python" may be absent or be
    # Python 2.
    return {"manifest_version": "0.3",
            "name": "tos-tools",
            "display_name": "TOS verified teacher tools",
            "version": version,
            "description": "Read-only verified Florida standards lookups, fabrication-blocking "
                           "code verification, citation-mutation detection, and artifact "
                           "validation from the Teacher Operating System. Offline; no accounts; "
                           "decision support for human review.",
            "author": {"name": "Teacher Operating System"},
            "compatibility": {"platforms": ["darwin", "win32", "linux"],
                              "runtimes": {"python": ">=3.10"}},
            "server": {"type": "python",
                       "entry_point": "tools/mcp_server.py",
                       "mcp_config": {"command": "python3",
                                      "args": ["${__dirname}/tools/mcp_server.py"],
                                      "platform_overrides": {"win32": {"command": "python"}}}}}


def stage(root: Path | None = None, staging: Path | None = None) -> Path:
    root = root or ROOT
    staging = staging or STAGING
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    for rel in SERVER_FILES:
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    for rel in DATA_TREES:
        shutil.copytree(root / rel, staging / rel)
    db = root / INDEX_FILES[0]
    if not db.exists():  # build from the committed sources so the bundle always carries it
        subprocess.run([sys.executable, str(root / "tools" / "offline_index.py"), "--build"],
                       check=True)
    for rel in INDEX_FILES:
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    shutil.copy2(root / "VERSION", staging / "VERSION")
    (staging / "manifest.json").write_text(json.dumps(_manifest(version), indent=2) + "\n",
                                           encoding="utf-8")
    return staging


def verify(staging: Path | None = None) -> list[str]:
    staging = staging or STAGING
    issues = []
    for rel in ["manifest.json", "VERSION", *SERVER_FILES, *INDEX_FILES]:
        if not (staging / rel).exists():
            issues.append(f"missing from staging: {rel}")
    m = json.loads((staging / "manifest.json").read_text(encoding="utf-8")) \
        if (staging / "manifest.json").exists() else {}
    if m and m.get("version") != (staging / "VERSION").read_text(encoding="utf-8").strip():
        issues.append("manifest version != bundled VERSION")
    if m.get("manifest_version") != "0.3":
        issues.append(f"manifest_version is {m.get('manifest_version')!r}, want '0.3' — check "
                      f"the MCPB spec before changing this")
    cfg = (m.get("server") or {}).get("mcp_config") or {}
    if (cfg.get("platform_overrides") or {}).get("win32", {}).get("command") != "python":
        issues.append("no win32 platform override — a bare python3 command cannot start on "
                      "Windows (python.org ships python.exe/py.exe, never python3.exe)")
    # the staged server must answer over real stdio from INSIDE the staging tree
    probe = subprocess.run([sys.executable, str(staging / "tools" / "mcp_server.py")],
                           input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n',
                           capture_output=True, text=True, timeout=120)
    try:
        n = len(json.loads(probe.stdout.strip().splitlines()[-1])["result"]["tools"])
        if n != 8:
            issues.append(f"staged server lists {n} tools, want 8")
    except Exception as exc:
        issues.append(f"staged server did not answer tools/list: {exc.__class__.__name__} "
                      f"(stderr: {probe.stderr[-200:]})")
    return issues


def self_test() -> int:
    import tempfile
    fails = 0

    def ck(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    tmp = Path(tempfile.mkdtemp(prefix="mcpb-st-")) / "staging"
    stage(staging=tmp)
    issues = verify(staging=tmp)
    ck("staged bundle verifies (files + version + live stdio tools/list from inside "
       "the staging tree)", issues == [])
    for i in issues:
        print("   ", i)
    man = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))
    ck("manifest declares the win32 interpreter (H-4: python3.exe does not exist there)",
       man["server"]["mcp_config"]["platform_overrides"]["win32"]["command"] == "python")
    ck("manifest_version tracks the current MCPB spec", man["manifest_version"] == "0.3")

    # twin: the manifest exactly as it shipped — 0.2, no override — must now be refused
    shipped = {**man, "manifest_version": "0.2"}
    shipped["server"] = {**man["server"],
                         "mcp_config": {k: v for k, v in man["server"]["mcp_config"].items()
                                        if k != "platform_overrides"}}
    (tmp / "manifest.json").write_text(json.dumps(shipped, indent=2) + "\n", encoding="utf-8")
    twin = verify(staging=tmp)
    ck("twin: the as-shipped manifest (0.2, no win32 override) is caught on both counts",
       any("manifest_version" in i for i in twin) and any("win32" in i for i in twin))
    (tmp / "manifest.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")

    (tmp / "canonical-sources" / "index" / "offline.db").unlink()
    ck("twin: a bundle missing its index is caught",
       any("offline.db" in i for i in verify(staging=tmp)))
    shutil.rmtree(tmp.parent)
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    staging = stage()
    issues = verify()
    for i in issues:
        print("  x " + i)
    if not issues:
        size = sum(f.stat().st_size for f in staging.rglob("*") if f.is_file())
        print(f"staged {staging.relative_to(ROOT)} ({size/1e6:.1f} MB unpacked) — "
              f"next: mcpb pack (see docstring)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
