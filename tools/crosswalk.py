#!/usr/bin/env python3
"""Cross-map requirements across frameworks (offline).

Reads the independent-framework registry (shared/standards/frameworks/) and the crosswalks
(shared/standards/crosswalks/) and answers "what does <code> in framework A map to in B?". Mirrors
tools/fl_lookup.py. Mappings are domain-level + illustrative until verified - always confirm on both
sources (see crosswalks.md). Stdlib only.

Usage:
  python3 tools/crosswalk.py --frameworks
  python3 tools/crosswalk.py --framework ib
  python3 tools/crosswalk.py --map "AP Calculus AB"            # search all crosswalks
  python3 tools/crosswalk.py --map "MYP" --from IB --to FL-BEST-Math
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "shared" / "standards" / "frameworks"
XW = ROOT / "shared" / "standards" / "crosswalks"


def load_frameworks():
    return json.loads((FW / "index.json").read_text(encoding="utf-8"))


def load_crosswalks():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(XW.glob("*.json"))]


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Cross-map requirements across frameworks (offline).")
    ap.add_argument("--frameworks", action="store_true", help="list registered frameworks")
    ap.add_argument("--framework", metavar="ID", help="show one framework's metadata")
    ap.add_argument("--map", metavar="CODE", help="find crosswalk mappings for a code/label")
    ap.add_argument("--from", dest="frm", help="filter by source framework")
    ap.add_argument("--to", help="filter by target framework")
    a = ap.parse_args(argv)

    if a.frameworks or not (a.framework or a.map):
        idx = load_frameworks()
        print(f"registered frameworks ({len(idx['frameworks'])}):")
        for f in idx["frameworks"]:
            print(f"  - {f['id']:11} {f['label']}  [{f['type']}, status={f['status']}, "
                  f"codes_verified={f['codes_verified']}]")
        print("\ncrosswalks:", ", ".join(p.stem for p in sorted(XW.glob("*.json"))) or "none")
        if not a.framework and not a.map:
            return 0

    if a.framework:
        p = FW / f"{a.framework}.json"
        if not p.exists():
            print(f"[!] no such framework: {a.framework}")
            return 1
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"\n{d['label']} ({d['framework']}) - {d['type']}")
        print(f"  levels: {', '.join(d.get('programmes_or_levels', []))}")
        print(f"  subjects: {', '.join(d.get('subjects', []))}")
        print(f"  code pattern: {d.get('code_pattern')}")
        print(f"  enumerated standards: {len(d.get('standards', []))}  (codes_verified={d.get('codes_verified')})")
        print(f"  source: {d.get('source')}")

    if a.map:
        needle = a.map.lower()
        hits = 0
        for xw in load_crosswalks():
            if a.frm and xw["from_framework"].lower() != a.frm.lower():
                continue
            if a.to and xw["to_framework"].lower() != a.to.lower():
                continue
            for e in xw.get("entries", []):
                if needle in str(e.get("from_code", "")).lower() or needle in str(e.get("subject", "")).lower():
                    hits += 1
                    print(f"\n  {xw['from_framework']}  {e.get('from_code')}  ({e.get('subject')})")
                    print(f"   -> {xw['to_framework']}  {', '.join(e.get('to_code', []))}")
                    print(f"      relationship={e.get('relationship')} confidence={e.get('confidence')}")
                    print(f"      {e.get('note','')}")
        if not hits:
            print(f"\n  no crosswalk entries match '{a.map}' (entries are being populated; verify on source).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
