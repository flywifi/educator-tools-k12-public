#!/usr/bin/env python3
"""deps_preflight.py — dependency preflight for the local harvesting pipeline.

Runs BEFORE any acquisition/parsing so EVERY OCR + document-parsing tool a run might touch is present
and up to date — without ever risking "dependency hell". Same anti-dependency-hell contract as
field_harvest.py:

  * ALL third-party packages live in ONE isolated, disposable venv (.harvest-venv/). Your system /
    user Python and other projects are never touched. Rebuild anytime:  --reset-venv.
  * EVERY install is wheels-only (`pip install --only-binary=:all:`), so nothing ever compiles from
    source — no lxml/libxml2-class build traps on any machine. A package with no matching wheel is an
    honest capability gap (skipped, reported), never a crash.
  * Each package is best-effort and independent: one failing wheel never blocks the others (a combined
    install that fails is retried per-package for maximum partial success).
  * Tesseract is a SYSTEM binary (the OCR engine pytesseract drives) — it CANNOT be pip-installed.
    We DETECT it and print OS-specific install instructions if it's missing; we never pretend it's there.
  * "Up to date": packages are upgraded at most once/day (a stamp avoids needless network calls);
    force an upgrade now with --update-deps, or skip the upgrade pass with --no-update.

COVERED (all pure-Python / wheels-only — see PINNED_DEPS):
  requests, beautifulsoup4, openpyxl   fetch + HTML/XLSX parsing
  pymupdf, pdfplumber                  PDF text/layout extraction
  pillow, pytesseract                  screenshot OCR (drives the tesseract system binary)
  markitdown                           universal document -> markdown (best-effort)
  playwright (+ chromium)              headless render + full-page screenshot

INTEGRATION (callers run this first; nothing third-party is imported until after it returns):
  import deps_preflight
  deps_preflight.preflight()           # builds/enters .harvest-venv, ensures deps, prints honest gaps

USAGE (standalone)
  python3 tools/deps_preflight.py                  # build/verify the env + print a capability report
  python3 tools/deps_preflight.py --update-deps    # force an upgrade pass now
  python3 tools/deps_preflight.py --reset-venv     # delete + rebuild the isolated venv
  python3 tools/deps_preflight.py --no-venv        # report what the CURRENT interpreter has (no install)
  python3 tools/deps_preflight.py --no-deps        # disable the preflight entirely (escape hatch)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# --- PINNED, WHEELS-ONLY deps. A package belongs here ONLY if it (and its transitive deps) ship
# universal/binary wheels — never anything that would compile from source. Each is independent and
# best-effort. dist name -> import name lives in IMPORT_NAME below. ----------------------------------
PINNED_DEPS = [
    "requests>=2.31,<3",        # resilient fetch
    "charset-normalizer>=3,<4", # encoding detection for i18n decode (foreign scripts/legacy encodings)
    "beautifulsoup4>=4.12,<5",  # HTML parsing helper
    "openpyxl>=3.1,<4",         # .xlsx (CPALMS course exports)
    "pymupdf>=1.24",            # PDF text + links (ships wheels; --only-binary keeps it source-free)
    "pdfplumber>=0.11",         # PDF layout/tables (pure-Python + pdfminer.six/pillow wheels)
    "pillow>=10.0",             # imaging for OCR (ships wheels; --only-binary keeps it source-free)
    "pytesseract>=0.3.10",      # OCR wrapper — DRIVES the tesseract SYSTEM binary (detected separately)
    "markitdown>=0.0.1a2",      # universal document -> markdown (best-effort; isolated so it can't sink the rest)
    "scrapling>=0.2",           # PARSER ONLY (no [fetchers]/stealth) — resilient HTML extraction via lxml;
                                # best-effort + wheels-only so its lxml dep installs from a wheel or is an
                                # honest gap (the docintel HTML parser falls back to stdlib either way)
    "playwright>=1.40",         # headless Chromium render + screenshot (browser fetched separately)
]

IMPORT_NAME = {
    "requests": "requests",
    "charset-normalizer": "charset_normalizer",
    "beautifulsoup4": "bs4",
    "openpyxl": "openpyxl",
    "pymupdf": "fitz",
    "pdfplumber": "pdfplumber",
    "pillow": "PIL",
    "pytesseract": "pytesseract",
    "markitdown": "markitdown",
    "scrapling": "scrapling",
    "playwright": "playwright",
}

# markitdown + scrapling pull wider transitive sets (scrapling -> lxml) than the others; keep their
# failure from blocking the run — each is isolated and best-effort, with a stdlib fallback downstream.
BEST_EFFORT = {"markitdown", "scrapling"}

_UPGRADE_INTERVAL = 24 * 3600  # upgrade pass at most once/day unless --update-deps forces it
_LAST_REPORT: dict | None = None


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
VENV_DIR = ROOT / ".harvest-venv"   # shared with field_harvest.py — one isolated env for the pipeline
STAMP = VENV_DIR / ".deps-stamp"


# --------------------------------------------------------------------------- venv plumbing
def _venv_python(venv: Path) -> Path:
    sub = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    return venv / sub / exe


def _dist_name(spec: str) -> str:
    import re
    return re.split(r"[<>=!~;\[\s]", spec, 1)[0].strip().lower()


def _capability_venv(cap: dict | None) -> Path:
    """Where a capability's packages go: the shared venv, or its own if it declares isolation.

    One shared venv is right for the harvest pipeline (its capabilities compose). It is wrong when
    two capabilities pin incompatible versions of the same package, because pip resolves that by
    silently DOWNGRADING the loser — audit finding H-5: installing the security_scan capability
    pulled semgrep, semgrep pins `mcp<2`, and mcp 2.0.0 was replaced with 1.29.0, after which the
    hosted MCP leg could not import MCPServer at all. `"isolated": true` in dependencies.json opts
    a capability out of that shared fate."""
    if cap and cap.get("isolated"):
        return ROOT / f".harvest-venv-{cap['id']}"
    return VENV_DIR


def _ensure_venv(venv: Path) -> Path | None:
    """Create `venv` if absent; return its interpreter, or None if it could not be built."""
    vpy = _venv_python(venv)
    if vpy.exists():
        return vpy
    try:
        print(f"[deps] building isolated environment at {venv} (one-time)...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run([str(vpy), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
                       check=False)
        return vpy if vpy.exists() else None
    except Exception as e:  # noqa: BLE001
        print(f"[deps] could not build {venv.name} ({e})", file=sys.stderr)
        shutil.rmtree(venv, ignore_errors=True)
        return None


def _create_base_venv() -> bool:
    """Create an empty isolated venv (python + fresh pip). Cleans up on failure so a half-built env
    can never strand a future run. Returns True only if the venv python exists afterward."""
    try:
        print(f"[deps] building isolated environment at {VENV_DIR} (one-time)...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        vpy = _venv_python(VENV_DIR)
        subprocess.run([str(vpy), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
        return vpy.exists()
    except Exception as e:  # noqa: BLE001
        print(f"[deps] could not build venv ({e}); using the current interpreter in probe-only mode "
              f"(stdlib paths still work — third-party features become honest capability gaps).",
              file=sys.stderr)
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        return False


def _bootstrap_into_venv() -> None:
    """If not already inside the isolated venv, build it (if needed) and RE-RUN the entry script
    (sys.argv[0]) inside it, then exit. No-ops when already inside, or when --no-venv/--no-deps."""
    argv = sys.argv[1:]
    if "--no-deps" in argv or os.environ.get("HARVEST_VENV") == "1":
        return  # explicitly skipped, or already running inside the managed env
    if "--no-venv" in argv:
        return  # caller wants the current interpreter -> ensure() will probe only, never install
    if "--reset-venv" in argv:
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        print("[deps] venv reset.", file=sys.stderr)
    vpy = _venv_python(VENV_DIR)
    if not vpy.exists() and not _create_base_venv():
        return  # couldn't build a venv -> degrade to probe-only on the current interpreter
    env = dict(os.environ, HARVEST_VENV="1")
    forwarded = [a for a in argv if a != "--reset-venv"]
    r = subprocess.run([str(_venv_python(VENV_DIR)), os.path.abspath(sys.argv[0]), *forwarded], env=env)
    sys.exit(r.returncode)


# --------------------------------------------------------------------------- probing + installing
_PROBE_SRC = (
    "import json, importlib\n"
    "out = {}\n"
    "for imp in %r:\n"
    "    try:\n"
    "        m = importlib.import_module(imp)\n"
    "        out[imp] = getattr(m, '__version__', '') or 'present'\n"
    "    except Exception:\n"
    "        out[imp] = None\n"
    "print(json.dumps(out))\n"
)


def _probe(py: str) -> dict:
    """Return {import_name: version-or-None} for every covered package, via a subprocess so the
    answer reflects the target interpreter exactly (no stale already-imported modules)."""
    imps = sorted(set(IMPORT_NAME.values()))
    try:
        r = subprocess.run([py, "-c", _PROBE_SRC % imps], capture_output=True, text=True, timeout=90)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {}


def _pip_install(py: str, specs: list[str], upgrade: bool) -> None:
    """Wheels-only install (never compiles). Try one combined command; if it fails (usually a single
    unavailable wheel), retry per-package so every installable dep still lands."""
    base = [py, "-m", "pip", "install", "--quiet", "--only-binary=:all:"]
    if upgrade:
        base.append("--upgrade")
    r = subprocess.run(base + list(specs), capture_output=True, text=True)
    if r.returncode == 0:
        return
    for spec in specs:  # best-effort fallback: isolate the failing wheel(s)
        subprocess.run(base + [spec], capture_output=True, text=True)


def _should_upgrade(update: bool | None) -> bool:
    if update is True:
        return True
    if update is False:
        return False
    if "--update-deps" in sys.argv:
        return True
    if "--no-update" in sys.argv:
        return False
    try:
        return (time.time() - STAMP.stat().st_mtime) > _UPGRADE_INTERVAL
    except OSError:
        return True  # never upgraded yet


def _write_stamp() -> None:
    try:
        STAMP.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def _snapshot(present: dict) -> dict:
    pkgs = {}
    for spec in PINNED_DEPS:
        dist = _dist_name(spec)
        imp = IMPORT_NAME[dist]
        ver = present.get(imp)
        pkgs[dist] = {"import": imp, "present": ver is not None, "version": ver,
                      "best_effort": dist in BEST_EFFORT}
    return pkgs


# --------------------------------------------------------------------------- browser + tesseract
def _ensure_chromium(py: str, install: bool) -> dict:
    probe = ("from playwright.sync_api import sync_playwright\n"
             "p = sync_playwright().start()\n"
             "print(p.chromium.executable_path)\n"
             "p.stop()\n")
    r = subprocess.run([py, "-c", probe], capture_output=True, text=True)
    path = (r.stdout or "").strip().splitlines()[-1].strip() if r.stdout.strip() else ""
    if r.returncode == 0 and path and Path(path).exists():
        return {"ok": True, "path": path}
    if not install:
        return {"ok": False, "path": None, "note": "chromium not installed (run inside the venv to install)"}
    print("[deps] installing Chromium for the headless render/screenshot prong...", file=sys.stderr)
    subprocess.run([py, "-m", "playwright", "install", "chromium"], check=False)
    r = subprocess.run([py, "-c", probe], capture_output=True, text=True)
    path = (r.stdout or "").strip().splitlines()[-1].strip() if r.stdout.strip() else ""
    ok = r.returncode == 0 and bool(path) and Path(path).exists()
    return {"ok": ok, "path": path if ok else None,
            "note": "" if ok else "could not provision Chromium — render/screenshot disabled"}


def _tesseract_install_hint() -> str:
    if sys.platform.startswith("win"):
        return ("Windows: install the UB-Mannheim build from "
                "https://github.com/UB-Mannheim/tesseract/wiki, then add it to PATH "
                "(or set pytesseract.pytesseract.tesseract_cmd to the tesseract.exe path).")
    if sys.platform == "darwin":
        return "macOS: brew install tesseract tesseract-lang  (tesseract-lang = non-English OCR scripts)"
    return ("Linux: sudo apt-get install -y tesseract-ocr   (add language packs for foreign scripts, "
            "e.g. tesseract-ocr-jpn / -chi-sim / -ara / -spa; Fedora/RHEL: sudo dnf install tesseract)")


def _detect_tesseract() -> dict:
    exe = shutil.which("tesseract")
    if not exe:
        return {"present": False, "path": None, "version": "", "install": _tesseract_install_hint()}
    ver = ""
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        lines = (r.stdout or r.stderr or "").splitlines()
        ver = lines[0].strip() if lines else ""
    except Exception:  # noqa: BLE001
        pass
    return {"present": True, "path": exe, "version": ver}


# --------------------------------------------------------------------------- public API
def ensure_dependencies(update: bool | None = None, install: bool | None = None) -> dict:
    """Probe -> (install missing / upgrade) -> provision Chromium -> detect tesseract. Returns an
    honest capability report. Installs ONLY into the managed venv; with install=False it reports the
    current interpreter's capabilities without touching it."""
    py = sys.executable
    if install is None:
        install = os.environ.get("HARVEST_VENV") == "1"  # only the managed venv ever gets writes

    present = _probe(py)
    report = {"python": py, "install": bool(install), "packages": _snapshot(present),
              "chromium": {}, "tesseract": {}, "gaps": [], "upgraded": False}

    missing = [s for s in PINNED_DEPS if not report["packages"][_dist_name(s)]["present"]]
    do_upgrade = install and _should_upgrade(update)
    if install and (missing or do_upgrade):
        specs = list(PINNED_DEPS) if do_upgrade else missing
        # install best-effort packages on their own so their wider dep tree can't fail the rest
        core = [s for s in specs if _dist_name(s) not in BEST_EFFORT]
        extra = [s for s in specs if _dist_name(s) in BEST_EFFORT]
        if core:
            _pip_install(py, core, upgrade=do_upgrade)
        for s in extra:
            _pip_install(py, [s], upgrade=do_upgrade)
        if do_upgrade:
            _write_stamp()
            report["upgraded"] = True
        present = _probe(py)
        report["packages"] = _snapshot(present)

    if report["packages"]["playwright"]["present"]:
        report["chromium"] = _ensure_chromium(py, install)
    else:
        report["chromium"] = {"ok": False, "path": None, "note": "playwright not installed"}

    report["tesseract"] = _detect_tesseract()

    for dist, info in report["packages"].items():
        if not info["present"]:
            tag = " (best-effort)" if info["best_effort"] else ""
            report["gaps"].append(f"{dist}{tag}: import '{info['import']}' unavailable")
    if not report["chromium"].get("ok"):
        report["gaps"].append("chromium: headless render/screenshot disabled")
    if not report["tesseract"]["present"]:
        report["gaps"].append("tesseract system binary missing: OCR disabled -> " +
                              report["tesseract"]["install"])
    return report


def _print_capabilities(report: dict, stream=None) -> None:
    stream = stream or sys.stderr
    w = lambda m="": print(m, file=stream)  # noqa: E731
    w("[deps] dependency preflight" + ("" if report["install"] else " (probe-only — no installs)"))
    for dist, info in report["packages"].items():
        mark = "OK " if info["present"] else "-- "
        ver = f" {info['version']}" if info.get("version") else ""
        w(f"  {mark}{dist}{ver}")
    cr = report["chromium"]
    w(f"  {'OK ' if cr.get('ok') else '-- '}chromium" + (f"  {cr.get('note')}" if cr.get("note") else ""))
    ts = report["tesseract"]
    w(f"  {'OK ' if ts['present'] else '-- '}tesseract" + (f"  {ts.get('version','')}" if ts["present"] else ""))
    if not ts["present"]:
        w(f"      install: {ts['install']}")
    if report["gaps"]:
        w(f"  {len(report['gaps'])} capability gap(s) — the run continues; affected steps are skipped honestly.")


def preflight(update: bool | None = None, quiet: bool = False) -> dict:
    """One call for pipeline entry points: build/enter the isolated venv, ensure every covered dep is
    present (and up to date), provision Chromium, detect tesseract. Idempotent within a process.
    Returns the capability report; prints an honest summary to stderr unless quiet."""
    global _LAST_REPORT
    if "--no-deps" in sys.argv[1:]:
        return {"skipped": True, "packages": {}, "gaps": [], "tesseract": {"present": False}}
    _bootstrap_into_venv()  # may re-exec + sys.exit; returns here only when already inside (or degraded)
    if os.environ.get("HARVEST_DEPS_READY") == "1" and _LAST_REPORT is not None:
        return _LAST_REPORT
    report = ensure_dependencies(update=update)
    os.environ["HARVEST_DEPS_READY"] = "1"
    _LAST_REPORT = report
    if not quiet:
        _print_capabilities(report)
    return report


# --------------------------------------------------------------------------- Option 1: install ANY
# capability's requirements into the SAME managed venv (never system/Homebrew Python -> no PEP
# 668) — EXCEPT a capability marked `"isolated": true` in dependencies.json, which gets its own
# `.harvest-venv-<id>` so one capability's pins cannot demote another's (audit H-5: semgrep pins
# mcp<2 and silently downgraded the hosted leg's SDK).
def _load_capabilities() -> list[dict]:
    try:
        return json.loads((ROOT / "tools" / "dependencies.json").read_text(encoding="utf-8")).get("capabilities", [])
    except Exception:  # noqa: BLE001
        return []


def _resolve_requirements(cap_or_path: str):
    """(requirements_path|None, capability_dict|None, note). A `*.txt` arg is used directly; anything
    else is treated as a capability `id` and looked up in tools/dependencies.json."""
    for cand in (Path(cap_or_path), ROOT / cap_or_path):
        if str(cand).endswith(".txt") and cand.exists():
            return cand, None, ""
    for c in _load_capabilities():
        if c.get("id") == cap_or_path:
            req = c.get("requirements")
            if not req:  # e.g. render_convert -> LibreOffice system binary, nothing to pip-install
                return None, c, f"'{cap_or_path}' is a system-binary capability (no pip packages)"
            rp = ROOT / req
            return (rp if rp.exists() else None), c, ("" if rp.exists() else f"requirements file {req} not found")
    return None, None, f"unknown capability or requirements path: '{cap_or_path}'"


def _specs_from_requirements(path: Path) -> list[str]:
    """Real package specs only — skip blanks, comments (full-line and inline), and pip option lines
    (`--only-binary`, `-r …`). Feeding these to the per-package best-effort _pip_install() means a
    no-wheel package is an honest gap, not an all-or-nothing `-r` failure."""
    specs = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].split("\t#", 1)[0].strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        specs.append(line)
    return specs


def _pip_present(py: str, dists: list[str]) -> dict:
    src = ("import json, importlib.metadata as M\n"
           "out = {}\n"
           "for d in %r:\n"
           "    try: M.version(d); out[d] = True\n"
           "    except Exception: out[d] = False\n"
           "print(json.dumps(out))\n")
    try:
        r = subprocess.run([py, "-c", src % list(dists)], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {d: False for d in dists}


def install_requirements(cap_or_path: str, upgrade: bool = False) -> dict:
    """Install one capability's (or a requirements file's) packages into the managed venv, wheels-only
    + per-package best-effort. Call ONLY after _bootstrap_into_venv() has re-exec'd us inside
    .harvest-venv, so sys.executable is the venv python and system/Homebrew Python is never touched."""
    path, cap, note = _resolve_requirements(cap_or_path)
    if cap and cap.get("tier") == "cloud_optional":
        return {"target": cap_or_path, "installed": False,
                "note": f"'{cap_or_path}' is cloud_optional (OFF by default; needs district opt-in + an "
                        "API key from the environment) — not auto-installed."}
    if path is None:
        return {"target": cap_or_path, "installed": False, "note": note or "nothing to install"}
    specs = _specs_from_requirements(path)
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    if not specs:
        return {"target": cap_or_path, "requirements": rel, "installed": True,
                "note": "no active (uncommented) packages", "packages": {}}
    venv = _capability_venv(cap)
    if venv == VENV_DIR:
        py = sys.executable                       # already re-exec'd inside the shared venv
    else:
        vpy = _ensure_venv(venv)                  # isolated: its own env, built on demand
        if vpy is None:
            return {"target": cap_or_path, "requirements": rel, "installed": False,
                    "note": f"could not build the isolated venv {venv.name}"}
        py = str(vpy)
    _pip_install(py, specs, upgrade=upgrade)
    present = _pip_present(py, [_dist_name(s) for s in specs])
    return {"target": cap_or_path, "requirements": rel, "venv_python": str(_venv_python(venv)),
            "isolated": venv != VENV_DIR,
            "packages": present, "gaps": sorted(d for d, ok in present.items() if not ok),
            "installed": True}


def _print_install(rep: dict) -> None:
    w = lambda m="": print(m, file=sys.stderr)  # noqa: E731
    if not rep.get("installed"):
        w(f"[deps] {rep['target']}: {rep.get('note', 'not installed')}")
        return
    into = Path(rep.get("venv_python", VENV_DIR)).parent.parent.name or VENV_DIR.name
    w(f"[deps] {rep['target']} -> {rep.get('requirements', '')} (into {into}"
      f"{' — ISOLATED, its pins cannot be downgraded by another capability' if rep.get('isolated') else ''})")
    for d, ok in (rep.get("packages") or {}).items():
        w(f"  {'OK ' if ok else '-- '}{d}")
    if rep.get("gaps"):
        w(f"  {len(rep['gaps'])} gap(s) — no matching wheel; honest capability gap, run continues.")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # --python-path [capability]: print the managed-venv interpreter (built or not) — the "exact
    # spot" a GUI launch or a Claude Desktop MCP `command` can point at. An isolated capability
    # (e.g. mcp_server) lives in its OWN venv, so name it to get the right interpreter. Print-only.
    if "--python-path" in args:
        rest = [a for a in args[args.index("--python-path") + 1:] if not a.startswith("-")]
        cap = None
        if rest:
            cap = next((c for c in _load_capabilities() if c["id"] == rest[0]), None)
            if cap is None:
                print(f"unknown capability: {rest[0]}", file=sys.stderr)
                return 2
        print(str(_venv_python(_capability_venv(cap))))
        return 0

    # --install <cap|path> / --install-all: install into .harvest-venv, never global (Option 1).
    if "--install" in args or "--install-all" in args:
        _bootstrap_into_venv()  # builds + re-execs INTO the venv; returns here only inside it (or degraded)
        if os.environ.get("HARVEST_VENV") != "1":
            print("[deps] could not enter an isolated venv; refusing to install into the current "
                  "interpreter (that would hit PEP 668 / risk system Python). Fix the venv "
                  "(--reset-venv) or create one manually: python3 -m venv .venv && . .venv/bin/activate",
                  file=sys.stderr)
            return 1
        upgrade = "--update-deps" in args
        if "--install-all" in args:
            targets = [c["id"] for c in _load_capabilities()
                       if c.get("tier") == "local_optional" and c.get("requirements")]
        else:
            i = args.index("--install")
            targets = [args[i + 1]] if i + 1 < len(args) else []
        if not targets:
            print("usage: deps_preflight.py --install <capability|requirements.txt> | --install-all",
                  file=sys.stderr)
            return 2
        installs = []
        done: dict = {}  # resolved requirements path -> first capability that installed it (dedupe)
        for t in targets:
            path, _cap, _note = _resolve_requirements(t)
            key = str(path) if path else None
            if key and key in done:
                rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
                rep = {"target": t, "requirements": rel, "installed": True,
                       "note": f"covered by '{done[key]}' (same requirements file, already installed this run)"}
            else:
                rep = install_requirements(t, upgrade=upgrade)
                if key and rep.get("installed"):
                    done[key] = t
            installs.append(rep)
            _print_install(rep)
        print(json.dumps({"venv_python": str(_venv_python(VENV_DIR)), "installs": installs}, indent=2))
        # Exit contract: a requested install that did NOT land is a failure (scripts must not read a
        # failed install as success). The one benign no-op is a system-binary capability (nothing to
        # pip-install) — that stays 0.
        failed = [r for r in installs
                  if not r.get("installed") and "system-binary capability" not in r.get("note", "")]
        return 1 if failed else 0

    # default: existing harvest preflight (unchanged)
    report = preflight(quiet=True)
    _print_capabilities(report, stream=sys.stdout)
    print()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
