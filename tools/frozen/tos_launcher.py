#!/usr/bin/env python3
"""tos-tools launcher — the entry point that makes the local verified tools start on ANY computer.

Compiled (PyInstaller, one-folder mode) into a small per-OS program that carries its own Python, so a
teacher needs to install nothing. It does NOT contain TOS's code: it finds the plugin/bundle folder on
disk and runs the real tools/mcp_server.py from there, so data and tool updates never need a rebuild.

The offline ladder — it starts the server with the MOST capable runtime it can find:
  1. $TOS_PYTHON, if set (a teacher/maintainer pin)
  2. the managed environment from `deps_preflight --install-all` (the optional local tools: OCR,
     transcription, conversion, vector search) — Level 1
  3. a system Python >= 3.10 on PATH — Level 1 without the extras
  4. its own built-in Python — Level 0, the 8 core tools, always available
So installing Python (and the local tools) makes TOS more capable immediately, with no reconfiguration.

STDOUT IS THE MCP WIRE: this file never prints to stdout. Diagnostics go to stderr only.
"""
from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path

MIN_PY = (3, 10)
MARKER = Path("tools") / "mcp_server.py"


def _log(msg: str) -> None:
    sys.stderr.write(f"[tos-launcher] {msg}\n")
    sys.stderr.flush()


def find_root() -> Path | None:
    """The TOS folder: $TOS_ROOT, else the nearest parent of this program holding tools/mcp_server.py.
    Desktop bundle: the bundle root. Claude Code plugin: the plugin root (bundles unpack beneath it)."""
    env = os.environ.get("TOS_ROOT")
    if env and (Path(env) / MARKER).is_file():
        return Path(env)
    here = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
    for p in here.parents:
        if (p / MARKER).is_file():
            return p
    return None


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _is_store_alias(p: str) -> bool:
    """Windows ships `python`/`python3` stubs in WindowsApps that open the Microsoft Store when no
    real Python is installed. Never treat those as a runtime."""
    return os.name == "nt" and "windowsapps" in p.replace("/", "\\").lower()


def _probe(python: str) -> tuple[int, int] | None:
    """(major, minor) of a candidate interpreter, or None. Short timeout; never inherits our stdin."""
    try:
        out = subprocess.run([python, "-c", "import sys,sqlite3;print('%d.%d'%sys.version_info[:2])"],
                             stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return None
        major, minor = out.stdout.strip().split(".")
        return int(major), int(minor)
    except Exception:  # noqa: BLE001 — any failure just means "not usable"
        return None


def candidates(root: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if os.environ.get("TOS_PYTHON"):
        found.append(("pinned ($TOS_PYTHON)", os.environ["TOS_PYTHON"]))
    for venv in (os.environ.get("TOS_VENV"), str(Path.home() / ".tos" / "venv"), str(root / ".harvest-venv")):
        if venv and _venv_python(Path(venv)).is_file():
            found.append(("managed local-tools environment", str(_venv_python(Path(venv)))))
    import shutil
    for name in ("python3", "python"):
        p = shutil.which(name)
        if p and not _is_store_alias(p):
            found.append(("system Python", p))
    return found


def choose(root: Path) -> tuple[str, str] | None:
    if os.environ.get("TOS_FORCE_BUILTIN") == "1":
        return None
    seen = set()
    for label, py in candidates(root):
        real = os.path.realpath(py)
        if real in seen:
            continue
        seen.add(real)
        ver = _probe(py)
        if ver and ver >= MIN_PY:
            return label, py
        _log(f"skipping {py}: " + (f"Python {ver[0]}.{ver[1]} < 3.10" if ver else "not a working Python"))
    return None


def main() -> int:
    root = find_root()
    if root is None:
        _log("cannot find the TOS folder (tools/mcp_server.py) — set TOS_ROOT")
        return 2
    server = root / MARKER
    picked = choose(root)
    if picked:
        label, py = picked
        _log(f"level 1 — running on {label}: {py}")
        # stdin/stdout/stderr are inherited, so the client talks straight to the child server.
        return subprocess.run([py, str(server), *sys.argv[1:]]).returncode
    _log("level 0 — running on the built-in Python (install Python 3.10+ for more offline tools)")
    sys.path[:0] = [str(root / "tools"), str(root / "shared")]
    sys.argv = [str(server), *sys.argv[1:]]
    try:
        runpy.run_path(str(server), run_name="__main__")
    except SystemExit as e:
        return int(e.code or 0) if not isinstance(e.code, str) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
