#!/usr/bin/env python3
"""One resolver for every external binary TOS shells out to (macOS finding E2).

WHY THIS EXISTS, in the words of the one place that already did it right
(`office/office_authoring.py::_find_soffice`): "on Windows and macOS soffice is NOT on PATH by
default, so PATH-only discovery would report a false capability gap on the very desktops that run
the offline tools."

That rule was written and then broken inside the same repo, because nothing factored it out:

  - `docintel/parsers/libreoffice_parser.py` carried an INLINED COPY of the per-OS logic in an
    `except` branch — the second resolver `office/README.md` explicitly forbids.
  - `health/capabilities.py` probed every declared `bins` entry with PATH-only `shutil.which`, so
    on a Mac it reported `soffice` MISSING while `office_authoring` found and used it. The health
    report and the feature contradicted each other.
  - `docintel/parsers/tesseract_ocr.py` reported `available() == True` from the Python wrapper
    alone and then failed at call time when the `tesseract` engine was absent.
  - `docintel/parsers/whisper_transcriber.py` documented an `ffmpeg` requirement and never looked
    for it.

TESTABILITY. `platform`, `which`, `exists` and `env` are PARAMETERS, not globals, because that is
the only way this repo tests a branch it cannot run — the `build_mcpb.launch_command(cfg, platform)`
precedent. There is no monkeypatch, no pytest and no fake-PATH fixture anywhere in the tree, so a
resolver whose OS branch is reachable only on that OS is a resolver with no coverage.

Resolution order: `TOS_BIN_<NAME>` env override -> `which()` (incl. aliases) -> per-OS candidate
paths -> None. Every resolution reports HOW it was found, so `doctor_env` and `mcp_smoke` can show
a path and a reason instead of a boolean.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

#: Alternate names to try on PATH. `libreoffice` is the distro name for the same program.
ALIASES = {
    "soffice": ("soffice", "libreoffice"),
    "libreoffice": ("libreoffice", "soffice"),
}

#: Where each binary lives when it is NOT on PATH, per platform. Keys are sys.platform values.
#: darwin lists BOTH Homebrew prefixes — /opt/homebrew (Apple Silicon) and /usr/local (Intel) —
#: which `_find_soffice` omitted entirely, so a Homebrew LibreOffice on a Mac was invisible unless
#: it also happened to be in /Applications.
CANDIDATES = {
    "soffice": {
        "win32": (r"C:\Program Files\LibreOffice\program\soffice.exe",
                  r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        "darwin": ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                   "/opt/homebrew/bin/soffice", "/usr/local/bin/soffice"),
        "linux": ("/usr/bin/soffice", "/usr/bin/libreoffice",
                  "/snap/bin/libreoffice", "/opt/libreoffice/program/soffice"),
    },
    "tesseract": {
        "win32": (r"C:\Program Files\Tesseract-OCR\tesseract.exe",),
        "darwin": ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"),
        "linux": ("/usr/bin/tesseract", "/usr/local/bin/tesseract"),
    },
    "ffmpeg": {
        "win32": (r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",),
        "darwin": ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"),
        "linux": ("/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/snap/bin/ffmpeg"),
    },
    "ffprobe": {
        "win32": (r"C:\Program Files\ffmpeg\bin\ffprobe.exe",),
        "darwin": ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"),
        "linux": ("/usr/bin/ffprobe", "/usr/local/bin/ffprobe"),
    },
    "pdftoppm": {
        "win32": (r"C:\Program Files\poppler\bin\pdftoppm.exe",),
        "darwin": ("/opt/homebrew/bin/pdftoppm", "/usr/local/bin/pdftoppm"),
        "linux": ("/usr/bin/pdftoppm",),
    },
    "pdftotext": {
        "win32": (r"C:\Program Files\poppler\bin\pdftotext.exe",),
        "darwin": ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext"),
        "linux": ("/usr/bin/pdftotext",),
    },
    "node": {
        "win32": (r"C:\Program Files\nodejs\node.exe",),
        "darwin": ("/opt/homebrew/bin/node", "/usr/local/bin/node"),
        "linux": ("/usr/bin/node", "/usr/local/bin/node", "/snap/bin/node"),
    },
    "fc-list": {
        "win32": (),
        "darwin": ("/opt/homebrew/bin/fc-list", "/usr/local/bin/fc-list"),
        "linux": ("/usr/bin/fc-list",),
    },
}

_CACHE: dict = {}


def env_var(name: str) -> str:
    """The override variable for a binary: fc-list -> TOS_BIN_FC_LIST."""
    return "TOS_BIN_" + name.upper().replace("-", "_").replace(".", "_")


def resolve(name, *, platform=None, which=None, exists=None, env=None) -> dict:
    """Locate `name`, reporting the path AND how it was found.

    Returns {"name", "path": str|None, "how": "env"|"path"|"candidate"|None, "platform"}.
    `how` matters: a capability report that says only True/False cannot tell a user whether their
    Homebrew install was seen, which is the exact confusion E2 is about.

    Injected `platform`/`which`/`exists`/`env` are how the darwin and win32 branches are exercised
    from a Linux CI runner; results are cached only when nothing is injected, so a probe can never
    poison the real lookup.
    """
    plat = platform or sys.platform
    cacheable = which is None and exists is None and env is None and platform is None
    if cacheable and name in _CACHE:
        return _CACHE[name]

    which = which or shutil.which
    exists = exists or (lambda p: Path(p).exists())
    env = os.environ if env is None else env

    override = (env.get(env_var(name)) or "").strip()
    if override:
        # An explicit override is honoured even if it does not exist — reporting "you pointed me at
        # a path that isn't there" beats silently falling back and claiming the capability is absent.
        out = {"name": name, "path": override, "how": "env", "platform": plat,
               "exists": bool(exists(override))}
        if cacheable:
            _CACHE[name] = out
        return out

    for candidate_name in ALIASES.get(name, (name,)):
        found = which(candidate_name)
        if found:
            out = {"name": name, "path": found, "how": "path", "platform": plat, "exists": True}
            if cacheable:
                _CACHE[name] = out
            return out

    # Not on PATH. This is the normal state on Windows and macOS desktops, not an error.
    key = plat if plat in ("win32", "darwin") else "linux"
    for cand in CANDIDATES.get(name, {}).get(key, ()):
        if exists(cand):
            out = {"name": name, "path": cand, "how": "candidate", "platform": plat, "exists": True}
            if cacheable:
                _CACHE[name] = out
            return out

    out = {"name": name, "path": None, "how": None, "platform": plat, "exists": False}
    if cacheable:
        _CACHE[name] = out
    return out


def find_binary(name, **kw):
    """The path to `name`, or None. Thin wrapper over resolve() for call sites that want a path."""
    return resolve(name, **kw)["path"]


def present(name, **kw) -> bool:
    """True when the binary was located AND is actually there (an env override may point nowhere)."""
    r = resolve(name, **kw)
    return bool(r["path"]) and r["exists"]


def clear_cache() -> None:
    _CACHE.clear()


def _self_test() -> int:
    fails = 0

    def ck(label, cond):
        nonlocal fails
        print(f"{'PASS' if cond else 'FAIL'} {label}")
        if not cond:
            fails += 1

    # --- real branches on THIS machine (both outcomes exist here, which is the point) ---
    so = resolve("soffice")
    ck(f"soffice resolves on this container (how={so['how']}, path={so['path']})", bool(so["path"]))
    for absent in ("tesseract", "ffmpeg", "pdftoppm"):
        r = resolve(absent)
        ck(f"{absent} absent here -> honest gap, not a crash", r["path"] is None and r["how"] is None)

    # --- the branches this OS cannot run: injected lookup, the build_mcpb.launch_command precedent
    no_path = lambda _n: None                                    # noqa: E731 — nothing on PATH
    ck("darwin: Homebrew (Apple Silicon) tesseract is found off-PATH",
       resolve("tesseract", platform="darwin", which=no_path, env={},
               exists=lambda p: p == "/opt/homebrew/bin/tesseract")["path"]
       == "/opt/homebrew/bin/tesseract")
    ck("darwin: Intel Homebrew prefix is ALSO a candidate (_find_soffice listed neither)",
       resolve("soffice", platform="darwin", which=no_path, env={},
               exists=lambda p: p == "/usr/local/bin/soffice")["path"] == "/usr/local/bin/soffice")
    ck("darwin: /Applications LibreOffice still resolves",
       resolve("soffice", platform="darwin", which=no_path, env={},
               exists=lambda p: p.startswith("/Applications"))["how"] == "candidate")
    ck("win32: LibreOffice under Program Files resolves",
       resolve("soffice", platform="win32", which=no_path, env={},
               exists=lambda p: p.endswith("soffice.exe"))["path"].endswith("soffice.exe"))
    ck("win32: a binary with no win32 candidate is an honest gap, not a linux path",
       resolve("fc-list", platform="win32", which=no_path, env={}, exists=lambda p: True)["path"]
       is None)

    # --- aliases ---
    ck("alias: `libreoffice` on PATH satisfies a `soffice` lookup",
       resolve("soffice", platform="linux", env={},
               which=lambda n: "/usr/bin/libreoffice" if n == "libreoffice" else None)["path"]
       == "/usr/bin/libreoffice")

    # --- env override ---
    ck("TOS_BIN_TESSERACT overrides PATH",
       resolve("tesseract", env={"TOS_BIN_TESSERACT": "/custom/tess"},
               which=lambda _n: "/usr/bin/tesseract", exists=lambda _p: True)["path"]
       == "/custom/tess")
    bad = resolve("ffmpeg", env={"TOS_BIN_FFMPEG": "/nope/ffmpeg"}, which=no_path,
                  exists=lambda _p: False)
    ck("an override pointing nowhere is reported as such, not silently ignored",
       bad["how"] == "env" and bad["exists"] is False and present(
           "ffmpeg", env={"TOS_BIN_FFMPEG": "/nope/ffmpeg"}, which=no_path,
           exists=lambda _p: False) is False)
    ck("env_var name mangling: fc-list -> TOS_BIN_FC_LIST", env_var("fc-list") == "TOS_BIN_FC_LIST")

    # --- the cache must not be poisoned by an injected probe ---
    clear_cache()
    resolve("soffice", platform="darwin", which=no_path, env={}, exists=lambda _p: False)
    ck("an injected probe does NOT enter the cache (real lookup still works)",
       resolve("soffice")["path"] is not None)

    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    for _n in sorted(CANDIDATES):
        _r = resolve(_n)
        _how = f"  (via {_r['how']})" if _r["path"] else ""
        _state = "FOUND " if _r["path"] else "absent"
        print(f"{_n:12s} {_state} {_r['path'] or ''}{_how}")
