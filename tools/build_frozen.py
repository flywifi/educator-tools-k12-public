#!/usr/bin/env python3
"""Build the per-OS `tos-tools` launcher (tools/frozen/tos_launcher.py) with PyInstaller.

One-FOLDER mode, never one-file: one-file unpacks itself to a temp dir on every start, leaves that dir
behind whenever the process is killed (every time a chat app closes its tool server), and cannot run
where /tmp is mounted noexec (PyInstaller docs, "Operating Mode"). The .mcpb is already a folder.

The launcher must carry every standard-library module the TOS server can import, because the TOS code
itself is NOT frozen in (it is read from the plugin folder at run time). That list is derived here with
modulefinder from the real server's import graph, so it cannot silently drift from the code.

Run on each target OS (PyInstaller is not a cross-compiler):
    python -m pip install -r tools/requirements-frozen.txt
    python tools/build_frozen.py            # -> dist/frozen/tos-tools/ (+ a smoke test)
    python tools/build_frozen.py --list     # print the derived stdlib module list only
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "tools" / "frozen" / "tos_launcher.py"
OUT = ROOT / "dist" / "frozen"
TOS_MODULES = ["mcp_server", "mcp_tooldefs", "offline_index", "verify_standards", "validate_outputs"]
# Never needed by a stdio tool server; excluding keeps the folder small.
NEVER = ("tkinter", "idlelib", "turtle", "turtledemo", "test", "lib2to3", "ensurepip", "venv",
         "pydoc_data", "unittest", "doctest", "pydoc")


def stdlib_modules() -> list[str]:
    """Standard-library modules the TOS server can import, read from the SOURCE with the ast module:
    every `import x` / `from x import y` (top-level or inside functions) in the server and in every
    TOS module it reaches (tools/, shared/, shared/health/ by name). PyInstaller then analyses those
    stdlib modules' own imports, so transitive needs are covered by PyInstaller, not by us.
    Was modulefinder — which crashes inside the stdlib on Python 3.12 (`spec.loader` is None for
    namespace packages), the exact version CI builds with (found in R8 pre-testing)."""
    import ast
    search = [ROOT / "tools", ROOT / "shared", ROOT / "shared" / "health"]
    std = set(sys.stdlib_module_names)
    todo, seen, found = [ROOT / "tools" / "mcp_server.py", LAUNCHER], set(), set()
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top in std:
                    found.add(n)
                    continue
                for d in search:  # a TOS module (module or package): follow it
                    for cand in (d / f"{top}.py", d / top / "__init__.py"):
                        if cand.is_file():
                            todo.append(cand)
                            if cand.name == "__init__.py":
                                todo.extend(sorted(cand.parent.glob("*.py")))
    return sorted(m for m in found if m.split(".")[0] not in NEVER and m != "__future__")


def build(target_arch: str | None = None) -> Path:
    mods = stdlib_modules()
    cmd = [sys.executable, "-m", "PyInstaller", "--onedir", "--name", "tos-tools", "--noconfirm",
           "--clean", "--log-level", "WARN", "--distpath", str(OUT), "--workpath", str(OUT / "_build"),
           "--specpath", str(OUT / "_build")]
    cmd += [f"--hidden-import={m}" for m in mods]
    cmd += [f"--exclude-module={m}" for m in TOS_MODULES + list(NEVER)]
    if platform.system() == "Darwin":
        cmd += ["--osx-bundle-identifier", "org.tos.tos-tools"]
        if target_arch:  # universal2 = one Mac executable for Apple silicon AND Intel; needs a
            cmd += ["--target-arch", target_arch]  # universal2 Python (python.org's macOS builds are)
    cmd.append(str(LAUNCHER))
    subprocess.run(cmd, check=True)
    shutil.rmtree(OUT / "_build", ignore_errors=True)
    exe = OUT / "tos-tools" / ("tos-tools.exe" if os.name == "nt" else "tos-tools")
    print(f"built {exe} ({len(mods)} stdlib modules)")
    return exe


def smoke(exe: Path, strip_path: bool = False) -> int:
    """Start the real server through the built launcher with NO other runtime allowed, and check the
    MCP handshake + a fabrication check. Mirrors the R7 proof; CI runs it on every OS."""
    import json
    frames = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                          "clientInfo": {"name": "smoke", "version": "0"}}},
              {"jsonrpc": "2.0", "method": "notifications/initialized"},
              {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
              {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
               "params": {"name": "verify_standard_codes",
                          "arguments": {"codes": ["MA.3.NSO.1.1", "MA.3.NSO.9.99"]}}}]
    env = {"TOS_ROOT": str(ROOT), "TOS_FORCE_BUILTIN": "1", "PATH": os.defpath,
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "TEMP": os.environ.get("TEMP", ""),
           "HOME": os.environ.get("HOME", ""), "USERPROFILE": os.environ.get("USERPROFILE", "")}
    if strip_path:
        # The real teacher case: no hint, and NOTHING on PATH — the launcher must find no other
        # runtime by itself and start on its built-in Python (level 0).
        import tempfile
        empty = tempfile.mkdtemp(prefix="tos-empty-path-")
        env.pop("TOS_FORCE_BUILTIN")
        env["PATH"] = empty
        env["HOME"] = env["USERPROFILE"] = empty   # no ~/.tos/venv either
    p = subprocess.run([str(exe)], input="\n".join(json.dumps(f) for f in frames) + "\n",
                       capture_output=True, text=True, timeout=300, env=env)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    msgs, junk = [], []
    for ln in lines:
        try:
            msgs.append(json.loads(ln))
        except json.JSONDecodeError:
            junk.append(ln)
    by_id = {m.get("id"): m for m in msgs}
    sys.path.insert(0, str(ROOT / "tools"))
    import mcp_tooldefs  # the stdio leg serves every registered tool
    expected = len(mcp_tooldefs.TOOLS)
    tools = by_id.get(2, {}).get("result", {}).get("tools", [])
    try:
        states = {r["code"]: r["state"] for r in
                  json.loads(by_id[3]["result"]["content"][0]["text"])["results"]}
    except Exception:  # noqa: BLE001
        states = {}
    checks = {"stdout carries only JSON-RPC": not junk,
              "initialize answered": "result" in by_id.get(1, {}),
              f"{expected} tools listed (the registry's count)": len(tools) == expected,
              "real code resolves": states.get("MA.3.NSO.1.1") == "resolved",
              "fabricated code rejected": states.get("MA.3.NSO.9.99") not in (None, "resolved")}
    if strip_path:
        checks["chose level 0 by itself (no runtime on PATH)"] = "level 0" in p.stderr
    for name, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + name)
    if not all(checks.values()):
        print("stderr tail:", p.stderr[-800:])
    return 0 if all(checks.values()) else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the derived stdlib module list")
    ap.add_argument("--no-smoke", action="store_true")
    ap.add_argument("--smoke-only", action="store_true", help="test an existing build")
    ap.add_argument("--strip-path", action="store_true",
                    help="smoke with an EMPTY PATH and no hints (the no-runtime teacher case)")
    ap.add_argument("--target-arch", choices=["x86_64", "arm64", "universal2"],
                    help="macOS only; universal2 needs a universal2 Python")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(stdlib_modules()))
        return 0
    exe = (OUT / "tos-tools" / ("tos-tools.exe" if os.name == "nt" else "tos-tools")) if a.smoke_only \
        else build(a.target_arch)
    return 0 if a.no_smoke else smoke(exe, strip_path=a.strip_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
