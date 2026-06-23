#!/usr/bin/env python3
"""Registry-currency watcher (offline, stdlib) — Area 1 of the capability roadmap.

Generalizes the standards crawler's "hash a watched source, report drift, human-approve, update baseline"
discipline to EVERY stored authoritative registry/field-catalog in the ecosystem (connectors, grade
scales, frameworks, ontology, routing, the records field catalogs, and the Cowork plugin manifest). It
does NOT fetch the web (that is standards-updater/tools/standards_refresh.py for the standards corpus);
it detects when an internal registry has drifted from its recorded baseline and tells you which
authoritative source to re-verify on. Nothing auto-applies — a human approves, then re-baselines.

Usage:
  python3 tools/registry_currency.py --report            # JSON drift report (default)
  python3 tools/registry_currency.py --summary           # human-readable
  python3 tools/registry_currency.py --update-baselines   # record current hashes (after approving changes)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "tools" / "registry-sources.json"
BASELINES = ROOT / "tools" / "registry-baselines.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def check() -> dict:
    cfg = _load(CONFIG, {"registries": []})
    baselines = _load(BASELINES, {}).get("hashes", {})
    rows, drift = [], 0
    for r in cfg.get("registries", []):
        rid, rel = r["id"], r["path"]
        digest = _sha256(ROOT / rel)
        base = baselines.get(rid)
        if digest is None:
            status, action = "missing", f"file absent: {rel}"
        elif base is None:
            status, action = "new", "record a baseline (--update-baselines)"
        elif digest != base:
            status, action = "changed", f"re-verify on: {r.get('authority','?')}; human-approve, then --update-baselines"
        else:
            status, action = "unchanged", "none"
        if status in ("changed", "missing"):
            drift += 1
        rows.append({"id": rid, "path": rel, "class": r.get("class"), "status": status,
                     "authority": r.get("authority"), "note": r.get("note"), "action": action})
    return {"tool": "registry-currency", "generated_at": _now(), "checked": len(rows),
            "drift_count": drift, "registries": rows,
            "baselines_present": BASELINES.exists(), "human_review_required": True}


def update_baselines() -> dict:
    cfg = _load(CONFIG, {"registries": []})
    hashes = {}
    for r in cfg.get("registries", []):
        digest = _sha256(ROOT / r["path"])
        if digest is not None:
            hashes[r["id"]] = digest
    BASELINES.write_text(json.dumps({"updated": _now(), "hashes": hashes}, indent=2) + "\n", encoding="utf-8")
    return {"recorded": len(hashes), "path": str(BASELINES.relative_to(ROOT))}


def to_summary(report: dict) -> str:
    lines = ["# Registry-currency report", "",
             f"- checked: {report['checked']} registries · drift: {report['drift_count']}"
             f" · baselines: {'present' if report['baselines_present'] else 'NOT recorded yet'}", ""]
    for r in report["registries"]:
        mark = {"unchanged": "ok ", "changed": "DRIFT", "new": "new", "missing": "MISS"}.get(r["status"], "?")
        lines.append(f"- [{mark}] {r['id']:16} {r['path']}")
        if r["status"] in ("changed", "missing"):
            lines.append(f"        -> {r['action']}")
    lines += ["", "_Human approves every change before re-baselining. human_review_required: true._"]
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Watch internal registries for drift (offline).")
    ap.add_argument("--report", action="store_true", help="JSON drift report (default)")
    ap.add_argument("--summary", action="store_true", help="human-readable drift report")
    ap.add_argument("--update-baselines", action="store_true", help="record current hashes after approving changes")
    a = ap.parse_args(argv)
    if a.update_baselines:
        print(json.dumps(update_baselines(), indent=2))
    elif a.summary:
        print(to_summary(check()), end="")
    else:
        print(json.dumps(check(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
