#!/usr/bin/env python3
"""Schools + programs index (offline, stdlib) — RFC-F001 V2 workstream C.

Loads district school/program indexes from canonical-sources/schools/<district>/schools.json and answers questions
about them: list/filter schools (by level, type, status), find magnet/choice programs, look up a school
by MSID or name, and surface what's stale. Public NON-PII data only — the authoritative school list is
the FLDOE MSID file; magnet/choice programs come from the district site. Open/close + program changes are
monitored by the source-currency engine (canonical-sources/registries/<district>-schools.json); this engine just reads
the committed snapshot and is honest about `completeness` (seed / partial / complete).

Usage:
  python3 canonical-sources/schools/schools.py --list                          # all schools (all districts)
  python3 canonical-sources/schools/schools.py --district ocps --level MS      # filter
  python3 canonical-sources/schools/schools.py --magnet                        # schools with magnet/choice programs
  python3 canonical-sources/schools/schools.py --status closed                 # e.g. recently closed/consolidated
  python3 canonical-sources/schools/schools.py --find "high school"            # name/MSID lookup
  python3 canonical-sources/schools/schools.py --stats                         # coverage + counts (+ completeness)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _districts() -> list[Path]:
    return sorted(p for p in HERE.glob("*/schools.json"))


def load(district: str | None = None) -> list[dict]:
    """Return the loaded district index dicts (optionally one district by folder name)."""
    out = []
    for path in _districts():
        if district and path.parent.name != district:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_district_key"] = path.parent.name
        data["_path"] = str(path.relative_to(HERE.parent.parent))
        out.append(data)
    return out


def schools(district: str | None = None) -> list[dict]:
    rows = []
    for idx in load(district):
        for s in idx.get("schools", []):
            s = dict(s)
            s["_district"] = idx.get("district_name")
            s["_district_key"] = idx["_district_key"]
            s["_completeness"] = idx.get("completeness", "seed")
            rows.append(s)
    return rows


def _has_program(s: dict, ptypes: set[str]) -> bool:
    return any((p.get("program_type") in ptypes) for p in s.get("programs", []))


def query(district=None, level=None, type=None, status=None, magnet=False, find=None) -> list[dict]:
    rows = schools(district)
    if level:
        rows = [s for s in rows if level in (s.get("levels") or [])]
    if type:
        rows = [s for s in rows if s.get("type") == type]
    if status:
        rows = [s for s in rows if s.get("status") == status]
    if magnet:
        rows = [s for s in rows if _has_program(s, {"magnet", "choice"})]
    if find:
        q = find.lower()
        rows = [s for s in rows if q in (s.get("school_name", "").lower()) or q == s.get("msid", "")]
    return rows


def stats() -> dict:
    out = {"districts": [], "human_review_required": True}
    for idx in load():
        ss = idx.get("schools", [])
        by_status, by_level, programs = {}, {}, 0
        for s in ss:
            by_status[s.get("status", "?")] = by_status.get(s.get("status", "?"), 0) + 1
            for lv in (s.get("levels") or ["?"]):
                by_level[lv] = by_level.get(lv, 0) + 1
            programs += len(s.get("programs", []))
        out["districts"].append({
            "district": idx.get("district_name"), "key": idx["_district_key"],
            "snapshot": idx.get("snapshot"), "completeness": idx.get("completeness", "seed"),
            "schools": len(ss), "programs": programs, "by_status": by_status, "by_level": by_level,
            "note": "SEED — populate the full index from FLDOE MSID" if idx.get("completeness") == "seed" else ""})
    return out


def _fmt(s: dict) -> str:
    progs = ", ".join(p.get("program_name", "?") for p in s.get("programs", [])) or "-"
    return f"{s.get('msid','?'):8} [{s.get('status','?'):10}] {s.get('school_name','?')}  ({'/'.join(s.get('levels') or [])})  programs: {progs}"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Query the schools + programs index (offline, public non-PII).")
    ap.add_argument("--district", help="district folder key, e.g. 'ocps'")
    ap.add_argument("--level", choices=["PK", "ES", "MS", "HS", "combo"])
    ap.add_argument("--type")
    ap.add_argument("--status", choices=["open", "closed", "planned", "consolidated", "renamed"])
    ap.add_argument("--magnet", action="store_true", help="only schools with a magnet/choice program")
    ap.add_argument("--find", help="name substring or exact MSID")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    a = ap.parse_args(argv)

    if not _districts():
        print(json.dumps({"status": "error", "detail": "no district indexes under canonical-sources/schools/*/schools.json"}))
        return 1
    if a.stats:
        print(json.dumps(stats(), indent=2, ensure_ascii=False))
        return 0
    rows = query(a.district, a.level, a.type, a.status, a.magnet, a.find)
    if a.json:
        print(json.dumps({"count": len(rows), "schools": rows, "human_review_required": True}, indent=2, ensure_ascii=False))
    else:
        for s in rows:
            print(_fmt(s))
        print(f"\n{len(rows)} school(s).  (completeness is per-district; see --stats)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
