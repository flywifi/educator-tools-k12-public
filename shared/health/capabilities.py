#!/usr/bin/env python3
"""Capabilities preflight (offline, stdlib) — what optional powers are active, and what each unlocks.

Reads tools/dependencies.json and probes, for every capability: Python libs (importable?), system
binaries (on PATH?), API-key secrets (present in the ENVIRONMENT? — value never read/printed), and font
coverage (via fc-list). Reports each as ready / partial / missing, and for the cloud tier whether it is
installed + credentialed (still off until a deployment opts in). Honest gaps only — nothing is faked.

Usage:
  python3 shared/health/capabilities.py              # human summary
  python3 shared/health/capabilities.py --json       # machine report
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools" / "dependencies.json"


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _font_families() -> list[str]:
    if not shutil.which("fc-list"):
        return []
    try:
        out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return []
    return out.splitlines()


def _fonts_present(groups: dict, fc_lines: list[str]) -> dict:
    blob = "\n".join(fc_lines).lower()
    cov = {}
    for group, families in groups.items():
        cov[group] = {fam: (fam.lower() in blob) for fam in families}
    return cov


def report() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"capabilities": []}
    fc_lines = _font_families()
    caps = []
    for c in manifest.get("capabilities", []):
        pys = {m: _has_module(m) for m in c.get("python", [])}
        bins = {b: bool(shutil.which(b)) for b in c.get("bins", [])}
        secrets = {s: (os.environ.get(s) not in (None, "")) for s in c.get("secrets", [])}
        entry = {"id": c["id"], "tier": c["tier"], "beats_baseline": c.get("beats_baseline"),
                 "python": pys, "bins": bins}
        if c.get("secrets"):
            entry["secrets_configured"] = secrets   # booleans only — never the values
        if c.get("fonts"):
            entry["fonts"] = _fonts_present(c["fonts"], fc_lines)

        py_ok = all(pys.values()) if pys else True
        bin_ok = all(bins.values()) if bins else True
        installed = py_ok and bin_ok and (c.get("rest_api") or pys or bins or True)
        if c["tier"] == "cloud_optional":
            cred_ok = all(secrets.values()) if secrets else True
            lib_ok = py_ok or bool(c.get("rest_api"))
            entry["status"] = ("available_when_enabled" if (lib_ok and cred_ok)
                               else "needs_credentials" if lib_ok else "needs_install")
            entry["note"] = "OFF by default; deployment must opt in (privacy: " + str(c.get("privacy", "")) + ")"
        elif c.get("fonts"):
            flat = [v for grp in entry["fonts"].values() for v in grp.values()]
            entry["status"] = "ready" if all(flat) else "partial" if any(flat) else "missing"
        else:
            some = (any(pys.values()) if pys else False) or (any(bins.values()) if bins else False)
            entry["status"] = "ready" if (py_ok and bin_ok) else "partial" if some else "missing"
        caps.append(entry)
    return {"tool": "capabilities-preflight", "capabilities": caps,
            "summary": {s: sum(1 for c in caps if c["status"] == s)
                        for s in ("ready", "partial", "missing", "available_when_enabled",
                                  "needs_credentials", "needs_install")},
            "human_review_required": True}


def to_summary(rep: dict) -> str:
    mark = {"ready": "ok  ", "partial": "PART", "missing": "MISS",
            "available_when_enabled": "rdy*", "needs_credentials": "key?", "needs_install": "----"}
    lines = ["# Capabilities preflight", "",
             "  (local: ready/partial/missing · cloud: rdy*=installed+keyed but off until opt-in)", ""]
    for tier in ("local_optional", "cloud_optional"):
        lines.append(f"## {tier}")
        for c in [c for c in rep["capabilities"] if c["tier"] == tier]:
            lines.append(f"- [{mark.get(c['status'], '?')}] {c['id']:20} — {c['beats_baseline']}")
        lines.append("")
    lines.append("_Cloud capabilities may send data off-site — district opt-in + student-data-policy. "
                 "Secrets come from the environment only; never the repo._")
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Capabilities preflight (offline).")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    a = ap.parse_args(argv)
    rep = report()
    print(json.dumps(rep, indent=2) if a.json else to_summary(rep), end="" if not a.json else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
