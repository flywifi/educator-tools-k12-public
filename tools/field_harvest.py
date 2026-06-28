#!/usr/bin/env python3
"""field_harvest.py — ONE-FILE local updater. Run it on your own machine (open network); it collects
everything Claude needs to refresh the TOS data and packages it for you to send back.

WHY: the Claude web sandbox can't reach ocps.net / fldoe.org (allowlist egress). Your machine can.
This does the network + parsing locally (no tokens), then bundles a single ZIP you upload to Claude.

NO DEPENDENCY HELL — by design:
  * The script builds its OWN isolated virtual environment (.harvest-venv/) with PINNED versions and
    re-runs itself inside it. Your system/user Python and other projects are never touched.
  * If anything about the venv ever breaks:  python field_harvest.py --reset-venv  (deletes + rebuilds).
  * If venv/pip can't be used at all, it FALLS BACK to a pure-stdlib mode automatically (fewer niceties,
    still works for parsing saved pages).
  * Run with --no-venv to force pure-stdlib mode and skip the venv entirely.

WHAT IT GATHERS
  1. Environment report (doctor_env.py)                    -> so Claude can spot setup issues
  2. School MSIDs: ingests saved pages in harvest_inbox/ (+ any live fetch), stamps real FLDOE MSIDs
     onto all 7 Central FL districts (msid_lookup.py --force)
  3. Live OCPS/district pages (best-effort, requests+bs4)  -> raw HTML saved for Claude to parse
  4. Coverage summary + change deltas
  5. Packages everything into  tos_update_<timestamp>.zip  -> upload this to Claude

USAGE (run from anywhere)
  python field_harvest.py                 # first run builds the venv, then collects + packages
  python field_harvest.py --push          # also git commit+push the refreshed data to the branch
  python field_harvest.py --inbox-only    # skip live fetches; only ingest saved pages
  python field_harvest.py --reset-venv    # delete + rebuild the isolated venv
  python field_harvest.py --no-venv       # force stdlib-only mode (no installs)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Isolated-venv bootstrap (the anti-dependency-hell layer). Runs BEFORE any
# third-party import. Pinned, isolated, disposable.
# ---------------------------------------------------------------------------

# PURE-PYTHON ONLY — no C extensions, so nothing ever compiles (no lxml/bs4 needed; the parsing
# is stdlib regex in msid_lookup.py). `requests` ships universal wheels and pulls only pure-Python
# deps (urllib3, certifi, idna, charset-normalizer). This is the whole anti-dependency-hell trick:
# if a wheel would need a compiler, it does NOT belong here.
PINNED_DEPS = ["requests>=2.31,<3"]


def _find_root(start: Path) -> Path:
    for base in (Path(start).resolve().parent, Path.cwd()):
        p = base
        for _ in range(6):
            if (p / "tools" / "sync_check.py").exists():
                return p
            if p.parent == p:
                break
            p = p.parent
    return Path(start).resolve().parent.parent


ROOT = _find_root(__file__)
VENV_DIR = ROOT / ".harvest-venv"


def _venv_python(venv: Path) -> Path:
    sub = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    return venv / sub / exe


def _venv_healthy(vpy: Path) -> bool:
    """A venv is only 'healthy' if its python exists AND the deps actually import."""
    if not vpy.exists():
        return False
    try:
        r = subprocess.run([str(vpy), "-c", "import requests"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def _build_venv() -> bool:
    """Create the isolated venv + install pure-Python deps. Verifies, and cleans up on failure
    so a half-built venv can never strand future runs. Returns True only if deps import."""
    import shutil as _sh
    print(f"[venv] building isolated environment at {VENV_DIR} (one-time)...", file=sys.stderr)
    try:
        _sh.rmtree(VENV_DIR, ignore_errors=True)  # start clean
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        vpy = _venv_python(VENV_DIR)
        subprocess.run([str(vpy), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)
        # --only-binary=:all: guarantees NO source build (no compiler ever); pure-Python deps qualify.
        subprocess.run([str(vpy), "-m", "pip", "install", "--quiet", "--only-binary=:all:", *PINNED_DEPS],
                       check=True)
        if not _venv_healthy(vpy):
            raise RuntimeError("deps did not import after install")
        print("[venv] ready.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[venv] could not build venv ({e}); cleaning up, using stdlib-only mode "
              f"(urllib fetch — fully functional).", file=sys.stderr)
        _sh.rmtree(VENV_DIR, ignore_errors=True)
        return False


def bootstrap() -> None:
    """If not already inside the venv (and not --no-venv), build it and re-run self inside it."""
    if os.environ.get("HARVEST_VENV") == "1":
        return  # already running inside the isolated env
    argv = sys.argv[1:]
    if "--no-venv" in argv:
        return  # user opted out -> stdlib-only
    if "--reset-venv" in argv and VENV_DIR.exists():
        import shutil
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        print("[venv] reset.", file=sys.stderr)
    vpy = _venv_python(VENV_DIR)
    # Rebuild if missing OR unhealthy (e.g. a previous half-finished install).
    if not _venv_healthy(vpy):
        if not _build_venv():
            return  # fall through to stdlib-only in this same process
    # re-run this script using the venv's python
    env = dict(os.environ, HARVEST_VENV="1")
    forwarded = [a for a in argv if a != "--reset-venv"]
    r = subprocess.run([str(_venv_python(VENV_DIR)), os.path.abspath(__file__), *forwarded], env=env)
    sys.exit(r.returncode)


bootstrap()  # <-- everything below this line may run inside the venv

# ---------------------------------------------------------------------------
# Main harvest (third-party imports are OPTIONAL; stdlib fallback always works)
# ---------------------------------------------------------------------------

import json          # noqa: E402
import shutil        # noqa: E402
import ssl           # noqa: E402
import time          # noqa: E402
import urllib.request  # noqa: E402
import zipfile       # noqa: E402
from datetime import datetime, timezone  # noqa: E402

try:
    import requests  # noqa: E402
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

DISTRICTS = "48,59,49,35,05,64,53"  # Orange, Seminole, Osceola, Lake, Brevard, Volusia, Polk
INBOX = ROOT / "harvest_inbox"
TOOLS = ROOT / "tools"
SCHOOLS = ROOT / "canonical-sources" / "schools"

LIVE_TARGETS = {
    "ocps_school_directory": "https://www.ocps.net/school-directory",
    "ocps_school_choice":    "https://www.ocps.net/departments/school_choice",
    "ocps_charter_list":     "https://www.ocps.net/current-list-of-charter-schools",
}
SAVE_MANUALLY = {
    "FLDOE Master School ID (all FL schools + MSIDs)":
        "https://eds.fldoe.org/EDS/MasterSchoolID/Selection.cfm",
}


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, f"ERROR: {e}"


def _fetch(url: str, dest: Path, log: list) -> bool:
    time.sleep(1.5)
    try:
        if _HAS_REQUESTS:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
            r.raise_for_status()
            data = r.content
        else:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                data = resp.read()
        dest.write_bytes(data)
        log.append(f"  [OK]   {url}  ({len(data):,} bytes)")
        return True
    except Exception as e:
        log.append(f"  [GAP]  {url}  -> {str(e)[:90]}")
        return False


def _coverage() -> dict:
    out = {}
    for f in sorted(SCHOOLS.glob("*/schools.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            s = d.get("schools", [])
            real = sum(1 for x in s if "X" not in str(x.get("msid", "")).upper()
                       and len(str(x.get("msid", ""))) == 6)
            out[f.parent.name] = {"total": len(s), "real_msid": real, "placeholder": len(s) - real}
        except Exception as e:
            out[f.parent.name] = {"error": str(e)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--push", action="store_true", help="git commit+push refreshed data to the branch")
    ap.add_argument("--inbox-only", action="store_true", help="skip live fetches; only ingest saved pages")
    ap.add_argument("--no-venv", action="store_true", help="force stdlib-only mode (no venv/installs)")
    ap.add_argument("--reset-venv", action="store_true", help="delete + rebuild the isolated venv")
    args = ap.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    pkg = ROOT / f"_harvest_{stamp}"
    raw = pkg / "raw_pages"
    raw.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(exist_ok=True)
    log: list[str] = []

    def say(m=""):
        print(m)
        log.append(m)

    say("=" * 68)
    say(f"TOS field harvest  —  {stamp} UTC")
    say(f"Repo root: {ROOT}")
    _in_venv = os.environ.get("HARVEST_VENV") == "1"
    _fetcher = "requests" if _HAS_REQUESTS else "urllib (stdlib)"
    say(f"Mode: {'isolated venv' if _in_venv else 'stdlib-only'}  |  fetcher: {_fetcher}")
    say("=" * 68)

    # 1. Environment doctor
    say("\n[1/5] Environment doctor")
    rc, doc = _run([sys.executable, str(TOOLS / "doctor_env.py"), "--json"])
    (pkg / "env.json").write_text(doc if rc == 0 else json.dumps({"error": doc}), encoding="utf-8")
    say("      saved env.json")

    # 2. Live fetches
    before = _coverage()
    if not args.inbox_only:
        say("\n[2/5] Live fetch (best-effort, polite, browser UA)")
        for name, url in LIVE_TARGETS.items():
            _fetch(url, raw / f"{name}.html", log)
        _fetch("https://eds.fldoe.org/EDS/MasterSchoolID/Selection.cfm", raw / "fldoe_msid_live.html", log)
        for line in log[-5:]:
            print(line) if line.strip().startswith("[") else None
    else:
        say("\n[2/5] Live fetch skipped (--inbox-only)")

    # 3. Ingest + stamp MSIDs
    say("\n[3/5] Ingest school lists + stamp FLDOE MSIDs")
    sources = list(INBOX.glob("*.html")) + list(INBOX.glob("*.csv")) + list(INBOX.glob("*.xlsx"))
    live_msid = raw / "fldoe_msid_live.html"
    if live_msid.exists() and live_msid.stat().st_size > 50_000:
        sources.insert(0, live_msid)
    if not sources:
        say("      no MSID source found.")
        say(f"      ACTION: save this page from a browser into  {INBOX}")
        for label, url in SAVE_MANUALLY.items():
            say(f"        - {label}\n          {url}   (Ctrl+S -> 'Webpage, HTML Only')")
        say("      then re-run:  python tools/field_harvest.py --inbox-only")
    else:
        src = sources[0]
        say(f"      MSID source: {src.name}")
        rc, out = _run([sys.executable, str(TOOLS / "msid_lookup.py"),
                        "--match", "--district", DISTRICTS, "--apply", "--confirm", "--force",
                        "--msid-file", str(src)])
        for line in out.splitlines():
            if "District" in line and "matched" in line:
                say("      " + line.strip())

    # 4. Coverage
    say("\n[4/5] Coverage")
    after = _coverage()
    (pkg / "coverage.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
    for k, v in after.items():
        delta = v.get("real_msid", 0) - before.get(k, {}).get("real_msid", 0)
        say(f"      {k:10} {v.get('real_msid',0):3}/{v.get('total',0):3} real{f'  (+{delta})' if delta else ''}")
    dst = pkg / "schools"
    shutil.copytree(SCHOOLS, dst,
                    ignore=shutil.ignore_patterns("*.md", "*.py", "*.schema.json", "__pycache__"))

    # 5. Package
    say("\n[5/5] Package")
    (pkg / "REPORT.md").write_text("# TOS Field Harvest\n\n```\n" + "\n".join(log) + "\n```\n", encoding="utf-8")
    zip_path = ROOT / f"tos_update_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pkg.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(pkg.parent))
    shutil.rmtree(pkg, ignore_errors=True)

    say("\n" + "=" * 68)
    say(f"DONE.  Upload this file to Claude:\n    {zip_path}")
    say("=" * 68)

    if args.push:
        say("\n[push] commit + push refreshed data")
        rc, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch.strip() or "HEAD"
        _run(["git", "add", "canonical-sources/schools"])
        rc, out = _run(["git", "commit", "-m", f"data(schools): field harvest {stamp}"])
        if "nothing to commit" in out.lower():
            say("      nothing changed.")
        else:
            rc, out = _run(["git", "push", "-u", "origin", branch])
            say(f"      push exit={rc} (branch {branch})")

    print(f"\nNext: drag  {zip_path.name}  into the Claude chat (or re-run with --push).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
