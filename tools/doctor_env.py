#!/usr/bin/env python3
"""doctor_env — diagnose your local Python so the offline TOS scripts run reliably.

Run this FIRST on your own machine if anything "dependency" related acts up. It is PURE STDLIB,
so it always runs no matter how messy your environment is, and it tells you:

  1. Which Python is actually running this (path + version).
  2. Every OTHER Python it can find (the classic "python vs pip point at different installs" trap).
  3. Whether `pip` installs into the SAME interpreter that runs the tools.
  4. Which packages the TOS offline tools need — and which are present (with the truth that the
     core workflow needs NONE).
  5. A live smoke test: import each offline tool + parse a tiny saved-EDS HTML snippet.
  6. A plain verdict with the exact command(s) to fix anything broken.

Usage:
  python tools/doctor_env.py            # full report
  python tools/doctor_env.py --json     # machine-readable (for pasting back to Claude)

What the offline data workflow actually requires:
  - Saving the FLDOE EDS page + parsing it (.html)  -> Python 3.8+ stdlib ONLY. No pip installs.
  - Reading an Excel MSID file (.xlsx)               -> openpyxl   (optional)
  - Live web fetch (blocked by FLDOE anyway)         -> requests, beautifulsoup4 (optional)
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What each capability needs. Core workflow = stdlib only.
STDLIB_NEEDED = ["csv", "io", "json", "re", "urllib.request", "html", "argparse", "pathlib"]
OPTIONAL = {
    "openpyxl": "only to read an .xlsx MSID file (the .html path needs nothing)",
    "requests": "only for live --fetch (FLDOE blocks bots; use the saved .html instead)",
    "bs4": "only for ocps_resources.py live crawl (optional)",
}
TOOLS = [
    ("tools/msid_lookup.py", "msid_lookup"),
    ("canonical-sources/schools/schools.py", "schools"),
    ("tools/local_harvest.py", "local_harvest"),
]


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr or "").strip()
    except Exception as e:
        return f"<error: {e}>"


def find_pythons() -> list[dict]:
    """Locate every python/py interpreter (on PATH + registered) and report version + path."""
    found: list[dict] = []
    seen: set[str] = set()

    def _add(name: str, p: str) -> None:
        p = p.strip().strip('"')
        if not p or p in seen or not Path(p).exists():
            return
        seen.add(p)
        ver = _run([p, "-c", "import sys;print('%d.%d.%d'%sys.version_info[:3])"])
        found.append({"name": name, "path": p, "version": ver})

    names = ["python", "python3", "py"]
    # `where` (Windows) / `which -a` (POSIX) — interpreters on PATH
    for name in names:
        locator = ["where", name] if os.name == "nt" else ["which", "-a", name]
        out = _run(locator)
        if out.startswith("<error") or "Could not find" in out or not out:
            continue
        for line in out.splitlines():
            _add(name, line)

    # Windows py launcher lists ALL registered installs, even those NOT on PATH
    # (e.g. one under your user profile AND one in a shared/all-users location).
    if os.name == "nt":
        out = _run(["py", "-0p"])  # e.g. " -V:3.13 *        C:\Users\me\...\python.exe"
        if not out.startswith("<error"):
            for line in out.splitlines():
                parts = line.split()
                # the path is the last token that ends in python.exe
                for tok in reversed(parts):
                    if tok.lower().endswith("python.exe"):
                        _add("py-registered", tok)
                        break

    # Always include the interpreter actually running this script
    _add("running", sys.executable)
    return found


def pip_target() -> dict:
    """Where does `pip` install? Compare to the running interpreter."""
    # The correct, unambiguous form is `python -m pip`. Show both plain pip and -m pip.
    plain = _run(["pip", "--version"])
    mpip = _run([sys.executable, "-m", "pip", "--version"])
    return {"plain_pip": plain, "running_python_-m_pip": mpip}


def check_imports() -> dict:
    res = {"stdlib": {}, "optional": {}}
    for mod in STDLIB_NEEDED:
        try:
            __import__(mod)
            res["stdlib"][mod] = "ok"
        except Exception as e:
            res["stdlib"][mod] = f"MISSING ({e})"
    for mod, why in OPTIONAL.items():
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            res["optional"][mod] = f"present ({ver}) — {why}"
        except Exception:
            res["optional"][mod] = f"absent — {why}"
    return res


def smoke_test() -> dict:
    """Import the offline tools and parse a tiny saved-EDS HTML snippet end to end."""
    out: dict = {}
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT / "canonical-sources" / "schools"))
    for rel, mod in TOOLS:
        if not (ROOT / rel).exists():
            out[mod] = f"NOT FOUND at {rel} (are you in the repo root?)"
            continue
        try:
            __import__(mod)
            out[mod] = "imports OK"
        except Exception as e:
            out[mod] = f"IMPORT FAILED: {e}"
    # Parse-a-snippet test (the core .html path, fully offline)
    try:
        import importlib
        ml = importlib.import_module("msid_lookup")
        snippet = ('<a href="Schooldisplay.cfm?DIST=48&amp;SCHL=1401">ALOMA ELEMENTARY</a>')
        tmp = ROOT / "_doctor_snippet.html"
        tmp.write_text(snippet, encoding="utf-8")
        rows = ml.load_msid_csv(tmp)
        tmp.unlink(missing_ok=True)
        ok = rows and ml._msid_col(rows[0]) == "481401"
        out["html_parse_smoke_test"] = "PASS (parsed 481401 ALOMA ELEMENTARY)" if ok else f"FAIL: {rows}"
    except Exception as e:
        out["html_parse_smoke_test"] = f"FAIL: {e}"
    return out


def build_report() -> dict:
    running = {
        "executable": sys.executable,
        "version": "%d.%d.%d" % sys.version_info[:3],
        "platform": platform.platform(),
        "in_repo_root": (ROOT / "tools" / "msid_lookup.py").exists() and Path.cwd() == ROOT,
        "cwd": str(Path.cwd()),
        "repo_root": str(ROOT),
    }
    return {
        "running_python": running,
        "all_pythons_found": find_pythons(),
        "pip_target": pip_target(),
        "imports": check_imports(),
        "smoke": smoke_test(),
    }


def verdict(rep: dict) -> list[str]:
    msgs: list[str] = []
    v = rep["running_python"]["version"]
    major, minor = (int(x) for x in v.split(".")[:2])
    if (major, minor) < (3, 8):
        msgs.append(f"[BLOCKER] Python {v} is too old. Install Python 3.8+ (3.11+ recommended).")
    else:
        msgs.append(f"[OK] Python {v} is fine for every offline TOS tool.")

    stdlib_missing = [k for k, val in rep["imports"]["stdlib"].items() if val != "ok"]
    if stdlib_missing:
        msgs.append(f"[BLOCKER] Missing stdlib modules: {stdlib_missing} — your Python install is broken; reinstall it.")
    else:
        msgs.append("[OK] All required stdlib modules present — the save-page->parse->stamp->query "
                    "workflow needs NOTHING else installed.")

    pythons = rep["all_pythons_found"]

    def _is_store_alias(path: str) -> bool:
        # Microsoft Store shims live under ...\Microsoft\WindowsApps\ — they are redirects to a
        # real install (or the Store), NOT separate interpreters. Benign unless there is NO real one.
        return "windowsapps" in path.lower()

    real = [p for p in pythons if not _is_store_alias(p["path"])]
    aliases = [p for p in pythons if _is_store_alias(p["path"])]
    distinct_real = {p["path"] for p in real}

    if len(distinct_real) > 1:
        msgs.append(f"[WARN] {len(distinct_real)} DIFFERENT real Python installs found "
                    "(this is the split that causes pip/import mismatches):")
        for p in real:
            here = "  <-- running THIS one" if p["path"] == sys.executable else ""
            msgs.append(f"        {p['name']}: {p['version']}  {p['path']}{here}")
        msgs.append("        If `pip install X` says 'already satisfied' but a script says "
                    "'ModuleNotFoundError: X', they're pointing at different installs. FIX: always use")
        msgs.append(f"        {Path(sys.executable).name} -m pip install <pkg>   (binds pip to the python that runs the tools)")
    else:
        msgs.append("[OK] One real Python install — no interpreter/pip split to worry about.")
    if aliases:
        msgs.append(f"[INFO] {len(aliases)} Microsoft Store alias(es) in WindowsApps (benign redirects, "
                    "not separate installs): " + ", ".join(sorted({Path(a['path']).name for a in aliases})))

    if not rep["running_python"]["in_repo_root"]:
        msgs.append(f"[NOTE] You're not in the repo root ({rep['running_python']['repo_root']}). "
                    "cd there before running the tools, or the relative paths won't resolve.")

    smoke = rep["smoke"]
    if smoke.get("html_parse_smoke_test", "").startswith("PASS"):
        msgs.append("[OK] Live smoke test passed — the offline HTML MSID parser works on this machine.")
    else:
        msgs.append(f"[CHECK] Smoke test: {smoke.get('html_parse_smoke_test')}")
    return msgs


def main(argv: list[str] | None = None) -> int:
    rep = build_report()
    if argv and "--json" in argv:
        print(json.dumps(rep, indent=2))
        return 0
    print("=" * 70)
    print("TOS offline-tools environment doctor")
    print("=" * 70)
    print(f"Running Python : {rep['running_python']['version']}  ({rep['running_python']['executable']})")
    print(f"Platform       : {rep['running_python']['platform']}")
    print(f"Repo root      : {rep['running_python']['repo_root']}")
    print(f"Current dir    : {rep['running_python']['cwd']}")
    print("\n--- pip target ---")
    for k, val in rep["pip_target"].items():
        print(f"  {k}: {val}")
    print("\n--- required stdlib (must all be ok) ---")
    for k, val in rep["imports"]["stdlib"].items():
        print(f"  {k:18} {val}")
    print("\n--- optional packages (NOT needed for the .html workflow) ---")
    for k, val in rep["imports"]["optional"].items():
        print(f"  {k:12} {val}")
    print("\n--- tool import + smoke test ---")
    for k, val in rep["smoke"].items():
        print(f"  {k:24} {val}")
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    for line in verdict(rep):
        print(line)
    print("\nTip: `python tools/doctor_env.py --json` gives output you can paste back to Claude.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
