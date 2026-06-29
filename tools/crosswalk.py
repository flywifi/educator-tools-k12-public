#!/usr/bin/env python3
"""Cross-map requirements AND grades across frameworks/scales (offline).

Reads the independent-framework registry (shared/standards/frameworks/), the grade-scale registry
(shared/standards/grade-scales/), and the crosswalks (shared/standards/crosswalks/) and answers:
  - "what does <code> in framework A map to in B?"   (--map)
  - "what does grade <X> on scale A mean on scale B?" (--grade)  e.g. translate an 'A'.

Mappings are domain-level + illustrative until verified, and MOST grade conversions are
institution-dependent — always confirm on the source (see crosswalks.md, grade-scales.md). Mirrors
tools/fl_lookup.py. Stdlib only.

Usage:
  python3 tools/crosswalk.py --frameworks
  python3 tools/crosswalk.py --framework ib
  python3 tools/crosswalk.py --map "AP Calculus AB"            # search framework crosswalks
  python3 tools/crosswalk.py --map "MYP" --from IB --to FL-BEST-Math
  python3 tools/crosswalk.py --grade-scales
  python3 tools/crosswalk.py --grade A --from traditional-10pt --to gpa-4pt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "shared" / "standards" / "frameworks"
GS = ROOT / "shared" / "standards" / "grade-scales"
XW = ROOT / "shared" / "standards" / "crosswalks"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_frameworks():
    return _load(FW / "index.json")


def load_grade_scales():
    return _load(GS / "index.json")


def load_crosswalks():
    """All crosswalk files split into framework crosswalks and grade-scale crosswalks."""
    fw_xw, gs_xw = [], []
    for p in sorted(XW.glob("*.json")):
        d = _load(p)
        (gs_xw if d.get("kind") == "grade_scale_crosswalk" else fw_xw).append(d)
    return fw_xw, gs_xw


def list_all() -> None:
    idx = load_frameworks()
    print(f"registered frameworks ({len(idx['frameworks'])}):")
    for f in idx["frameworks"]:
        print(f"  - {f['id']:11} {f['label']}  [{f['type']}, status={f['status']}, "
              f"codes_verified={f['codes_verified']}]")
    fw_xw, gs_xw = load_crosswalks()
    print("\nframework crosswalks:", ", ".join(
        f"{x['from_framework']}->{x['to_framework']}" for x in fw_xw) or "none")
    print("grade-scale crosswalks:", "yes" if gs_xw else "none",
          "(use --grade-scales to list scales, --grade to translate)")


def show_framework(fid: str) -> int:
    p = FW / f"{fid}.json"
    if not p.exists():
        print(f"[!] no such framework: {fid}")
        return 1
    d = _load(p)
    print(f"\n{d['label']} ({d['framework']}) - {d['type']}")
    print(f"  levels: {', '.join(d.get('programmes_or_levels', []))}")
    print(f"  subjects: {', '.join(d.get('subjects', []))}")
    print(f"  code pattern: {d.get('code_pattern')}")
    print(f"  enumerated standards: {len(d.get('standards', []))}  (codes_verified={d.get('codes_verified')})")
    print(f"  source: {d.get('source')}")
    return 0


def show_grade_scales() -> None:
    idx = load_grade_scales()
    print(f"registered grade scales ({len(idx['scales'])}):")
    for s in idx["scales"]:
        print(f"  - {s['id']:18} {s['label']}  [{s['type']}, status={s['status']}]")
    print("\ntranslate with: --grade <value> --from <scale-id> --to <scale-id>")


def map_codes(needle: str, frm: str | None, to: str | None) -> None:
    fw_xw, _ = load_crosswalks()
    n, hits = needle.lower(), 0
    for xw in fw_xw:
        if frm and xw["from_framework"].lower() != frm.lower():
            continue
        if to and xw["to_framework"].lower() != to.lower():
            continue
        for e in xw.get("entries", []):
            if n in str(e.get("from_code", "")).lower() or n in str(e.get("subject", "")).lower():
                hits += 1
                print(f"\n  {xw['from_framework']}  {e.get('from_code')}  ({e.get('subject')})")
                print(f"   -> {xw['to_framework']}  {', '.join(e.get('to_code', []))}")
                print(f"      relationship={e.get('relationship')} coverage={e.get('coverage','?')} "
                      f"confidence={e.get('confidence')}")
                print(f"      {e.get('note','')}")
    if not hits:
        print(f"\n  no framework crosswalk entries match '{needle}' (entries are being populated; verify on source).")


def translate_grade(value: str, frm: str | None, to: str | None) -> None:
    _, gs_xw = load_crosswalks()
    v, hits = value.strip().lower(), 0
    for xw in gs_xw:
        for e in xw.get("entries", []):
            if str(e.get("from_grade", "")).strip().lower() != v:
                continue
            if frm and e.get("from_scale", "").lower() != frm.lower():
                continue
            if to and e.get("to_scale", "").lower() != to.lower():
                continue
            hits += 1
            to_vals = ", ".join(e.get("to", [])) or "(does not translate)"
            print(f"\n  {e.get('from_scale')}  '{e.get('from_grade')}'  ->  {e.get('to_scale')}  {to_vals}")
            print(f"      relationship={e.get('relationship')} coverage={e.get('coverage')} "
                  f"confidence={e.get('confidence')} institution_dependent={e.get('institution_dependent')}")
            print(f"      {e.get('note','')}")
    if not hits:
        print(f"\n  no grade-scale mapping for '{value}'"
              + (f" from {frm}" if frm else "") + (f" to {to}" if to else "")
              + ". Conversions are institution-dependent — confirm on the school/district policy.")
    else:
        print("\n  NOTE: grade translations are institution-dependent — confirm on the school/district policy "
              "before relying on them.")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Cross-map requirements and grades across frameworks/scales (offline).")
    ap.add_argument("--frameworks", action="store_true", help="list registered frameworks")
    ap.add_argument("--framework", metavar="ID", help="show one framework's metadata")
    ap.add_argument("--map", metavar="CODE", help="find framework crosswalk mappings for a code/label")
    ap.add_argument("--grade-scales", action="store_true", dest="grade_scales", help="list registered grade scales")
    ap.add_argument("--grade", metavar="VALUE", help="translate a grade/score across scales (e.g., A)")
    ap.add_argument("--from", dest="frm", help="filter by source framework/scale")
    ap.add_argument("--to", help="filter by target framework/scale")
    a = ap.parse_args(argv)

    did = False
    if a.grade_scales:
        show_grade_scales(); did = True
    if a.grade is not None:
        translate_grade(a.grade, a.frm, a.to); did = True
    if a.framework:
        show_framework(a.framework); did = True
    if a.map is not None:
        map_codes(a.map, a.frm, a.to); did = True
    if not did:
        list_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
