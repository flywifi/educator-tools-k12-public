#!/usr/bin/env python3
"""TOS — "work more offline" setup (Windows, Mac, Linux). Safe to re-run. Installs nothing without asking.

Level 0 needs nothing: TOS's verified tools already run on your computer.
This takes you to Level 1: optional LOCAL tools (reading scanned documents, transcribing audio,
converting files, meaning-based search) go into ONE private folder, ~/.tos/venv. Your system Python
and other programs are never touched. To undo everything, delete the ~/.tos folder.

Windows:   py setup\\tos_setup.py            Mac/Linux:   python3 setup/tos_setup.py
  --yes          don't ask (for Claude to run on your behalf after you said yes)
  --only ID      add one tool (e.g. ocr) instead of all
  --check        only report what is installed

Written in Python on purpose: a PowerShell script would be blocked on most Windows PCs (the default
execution policy for Windows clients is Restricted, and school Group Policy can disable scripts
outright), while this step needs Python anyway.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN = (3, 10)


def local_report(python: str) -> list[dict]:
    """The LOCAL optional tools and their status, as seen by `python` (the private env)."""
    code = ("import json,sys; sys.path.insert(0, r'%s'); import capabilities as c; "
            "print(json.dumps([x for x in c.report()['capabilities'] if x['tier']=='local_optional']))"
            % str(ROOT / "shared" / "health"))
    out = subprocess.run([python, "-c", code], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return []


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="TOS: add the optional offline tools (asks first).")
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--only", metavar="ID")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    if sys.version_info < MIN:
        print(f"This Python is {sys.version_info[0]}.{sys.version_info[1]}; TOS's offline tools need 3.10 or "
              "newer. Install it from https://www.python.org/downloads/ (on Windows no admin rights are "
              "needed), then run this again with the new Python.")
        return 0

    venv = Path(os.environ.get("TOS_VENV") or Path.home() / ".tos" / "venv").expanduser()
    env = dict(os.environ, TOS_VENV=str(venv))
    deps = [sys.executable, str(ROOT / "tools" / "deps_preflight.py")]

    if a.check:
        vpy = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        rows = local_report(str(vpy) if vpy.exists() else sys.executable)
        for r in rows:
            print(f"  {'ready  ' if r['status'] == 'ready' else 'not yet'}  {r['id']:20} {r['beats_baseline']}")
        return 0

    known = {c["id"] for c in json.loads((ROOT / "tools" / "dependencies.json").read_text(encoding="utf-8"))
             ["capabilities"] if c.get("tier") == "local_optional"}
    if a.only and a.only not in known:
        print(f"unknown local tool {a.only!r}; choose from: {', '.join(sorted(known))}")
        return 2

    print(f"This will add TOS's optional local tools to: {venv}")
    print(f"  using Python {sys.version_info[0]}.{sys.version_info[1]} at {sys.executable}")
    if a.only:
        print(f"  tool: {a.only}")
    else:
        print("  tools: complex/scanned PDFs, OCR, Office files, file conversion, audio transcription,")
        print("         web and feeds, meaning-based search, and more.")
        print("  space: plan for about 0.5-1 GB (a headless browser for rendering is the largest part).")
    print(f"  Nothing outside {venv.parent} changes. Undo any time: delete {venv.parent}")
    if not a.yes:
        try:
            ans = input("Continue? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("Nothing installed.")
            return 0

    cmd = deps + (["--install", a.only] if a.only else ["--install-all"])
    rc = subprocess.run(cmd, env=env).returncode
    vpy = subprocess.run(deps + ["--python-path"], env=env, capture_output=True, text=True).stdout.strip()
    rows = local_report(vpy) if vpy else []
    ready = [r["id"] for r in rows if r["status"] == "ready"]
    print(f"\nReady offline now: {', '.join(ready) or 'none yet'}")
    if rc != 0:
        print("Some tools could not be installed (often one needs a separate program, e.g. Tesseract for OCR); "
              "everything else is ready. Run with --check to see the list.")
    print("Restart Claude (or your chat app) so TOS starts on the new local tools.")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
