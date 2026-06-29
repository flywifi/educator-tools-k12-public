#!/usr/bin/env python3
"""ingest_sources.py — offline, token-free bulk ingester for saved source files.

Drop a pile of saved pages/exports into an inbox folder; this auto-detects each file's TYPE by
content signature, parses it into the canonical TOS datasets, DEDUPLICATES (so re-saving the same
directory or overlapping searches doesn't create duplicates), and rebuilds the offline index. Pure
stdlib (+ openpyxl only if an .xlsx is present). No model tokens — this is the scalable replacement
for parsing each file by hand in chat.

DETECTED TYPES (by signature, not filename):
  NCES PSS table        Office-HTML table containing 'PSS_SCHOOL_ID'      -> private schools (federal IDs)
  AISF directory        HTML with 'School_Name__c' sforc fields           -> private schools (AISF)
  CPALMS course export  .xlsx whose row-3 header has 'Course #'           -> courses

DEDUP: private schools keyed by nces_pss_id when present, else normalized name. Merges fields across
sources and records every `sources` an entry was seen in. Nothing is fabricated; only parsed rows.

USAGE
  python3 tools/ingest_sources.py --inbox ./harvest_inbox            # parse + merge + rebuild index
  python3 tools/ingest_sources.py --inbox ./harvest_inbox --dry-run  # report what it WOULD do
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV_DIR = ROOT / "canonical-sources" / "schools" / "private"
COURSES = ROOT / "canonical-sources" / "references" / "fl-course-codes.json"


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", v))).strip()


def _norm_name(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()


# ---- type detection + parsers -------------------------------------------------
def detect(path: Path, head: str) -> str:
    if path.suffix.lower() in (".xlsx", ".xls") and "PSS_SCHOOL_ID" not in head and "<html" not in head.lower():
        return "xlsx_course_export"
    if "PSS_SCHOOL_ID" in head:
        return "nces_pss"
    if "School_Name__c" in head:
        return "aisf_directory"
    if path.suffix.lower() in (".xlsx",):
        return "xlsx_course_export"
    return "unknown"


def parse_nces_pss(text: str, src: str) -> list[dict]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I)
    def cells(r): return [_clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
    hdr = None; hi = 0
    for i, r in enumerate(rows):
        c = cells(r)
        if "PSS_SCHOOL_ID" in c:
            hdr, hi = c, i; break
    if not hdr:
        return []
    want = {"PSS_SCHOOL_ID": "nces_pss_id", "PSS_INST": "school_name", "LoGrade": "low_grade",
            "HiGrade": "high_grade", "PSS_ADDRESS": "address", "PSS_CITY": "city", "PSS_STABB": "state",
            "PSS_ENROLL_T": "enrollment", "PSS_RELIG": "religious", "PSS_LEVEL": "level"}
    im = {hdr.index(k): v for k, v in want.items() if k in hdr}
    out = []
    for r in rows[hi + 1:]:
        c = cells(r)
        if not c or not c[0] or c[0] == "PSS_SCHOOL_ID" or len(c) < len(hdr) - 5:
            continue
        rec = {v: (c[i] if i < len(c) else "") for i, v in im.items()}
        if rec.get("school_name"):
            rec["association"] = "NCES-PSS"; rec["source"] = src
            out.append(rec)
    return out


def parse_aisf(text: str, src: str) -> list[dict]:
    occ = re.findall(r'class="sforc-(?:header|description)\s+([A-Za-z0-9_]+__c)"[^>]*>(.*?)</', text, re.S)
    recs = []; cur = None
    for fld, val in occ:
        v = _clean(val)
        if fld == "School_Name__c":
            if cur:
                recs.append(cur)
            cur = {"school_name": v, "association": "AISF", "source": src}
        elif cur is not None and v:
            key = fld.replace("__c", "").replace("School_", "").lower()
            cur[{"head_name": "head", "accreditation_status": "accreditation"}.get(key, key)] = v
    if cur:
        recs.append(cur)
    return [r for r in recs if "test school" not in r["school_name"].lower()]


def parse_course_xlsx(path: Path, src: str) -> list[dict]:
    try:
        import openpyxl
    except ImportError:
        print("  (openpyxl needed for course xlsx; skipping)", file=sys.stderr)
        return []
    wb = openpyxl.load_workbook(path, read_only=True); rows = list(wb.active.iter_rows(values_only=True)); wb.close()
    hdr_i = next((i for i, r in enumerate(rows[:6]) if r and any(str(c).strip() == "Course #" for c in r if c)), None)
    if hdr_i is None:
        return []
    out = []
    for r in rows[hdr_i + 1:]:
        if not r or not r[0]:
            continue
        out.append({"course_number": str(r[0]).strip(),
                    "title": str(r[1]).strip() if len(r) > 1 and r[1] else None,
                    "path": str(r[2]).strip() if len(r) > 2 and r[2] else None,
                    "link": str(r[3]).strip() if len(r) > 3 and r[3] else None})
    return out


# ---- dedup merge --------------------------------------------------------------
def merge_private(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int, int]:
    """Dedup across sources by NCES id AND normalized name, so the same school from a federal
    (id-keyed) source and a name-only source (AISF) collapses into one record."""
    records: list[dict] = []
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}

    def index(r):
        records.append(r)
        if r.get("nces_pss_id"):
            by_id[r["nces_pss_id"]] = r
        by_name[_norm_name(r["school_name"])] = r

    def find(r):
        if r.get("nces_pss_id") and r["nces_pss_id"] in by_id:
            return by_id[r["nces_pss_id"]]
        return by_name.get(_norm_name(r["school_name"]))

    for r in existing:
        index(r)
    added = merged = 0
    for r in incoming:
        tgt = find(r)
        if tgt:
            for f, v in r.items():
                if v and not tgt.get(f):
                    tgt[f] = v
            srcs = set(filter(None, ([tgt.get("source")] if tgt.get("source") else []) +
                              tgt.get("sources", []) + ([r.get("source")] if r.get("source") else [])))
            if len(srcs) > 1:
                tgt["sources"] = sorted(srcs)
            if r.get("nces_pss_id") and r["nces_pss_id"] not in by_id:  # gained an id via the merge
                by_id[r["nces_pss_id"]] = tgt
            merged += 1
        else:
            index(r); added += 1
    return records, added, merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inbox", required=True, help="folder of saved source files to ingest")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    inbox = Path(a.inbox)
    if not inbox.exists():
        print(f"inbox not found: {inbox}", file=sys.stderr); return 1

    priv_incoming, course_incoming, report = [], [], []
    for f in sorted(inbox.iterdir()):
        if not f.is_file() or f.suffix.lower() in (".zip", ".png", ".jpg", ".jpeg", ".gif"):
            continue
        is_xlsx = f.suffix.lower() == ".xlsx"
        text = "" if is_xlsx else f.read_text(encoding="utf-8", errors="replace")
        kind = detect(f, text)  # signature scan over the FULL text, not just a head slice
        src = f.name
        if kind == "nces_pss":
            recs = parse_nces_pss(text, src); priv_incoming += recs
        elif kind == "aisf_directory":
            recs = parse_aisf(text, src); priv_incoming += recs
        elif kind == "xlsx_course_export":
            recs = parse_course_xlsx(f, src); course_incoming += recs
        else:
            recs = []
        report.append((f.name, kind, len(recs)))

    print("INGEST PLAN:")
    for name, kind, n in report:
        print(f"  {kind:20} {n:5} rows  <- {name[:50]}")

    # merge private schools into a consolidated, deduped file
    consolidated = PRIV_DIR / "private-schools-consolidated.json"
    existing = []
    if consolidated.exists():
        existing = json.loads(consolidated.read_text(encoding="utf-8")).get("members", [])
    merged_list, added, merged = merge_private(existing, priv_incoming)
    print(f"\nprivate schools: +{added} new, {merged} merged/deduped -> {len(merged_list)} total")

    if a.dry_run:
        print("\n[dry-run] no files written.")
        return 0

    PRIV_DIR.mkdir(parents=True, exist_ok=True)
    consolidated.write_text(json.dumps({
        "_comment": "Consolidated + DEDUPED private/independent schools, merged across all ingested "
                    "sources (AISF, NCES PSS, ...) by ingest_sources.py. Keyed by NCES PSS id, else "
                    "normalized name; 'sources' lists every directory an entry was seen in. Public, no PII.",
        "domain": "private-schools-consolidated", "captured": "2026-06-29",
        "count": len(merged_list), "human_review_required": True, "members": merged_list,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {consolidated.relative_to(ROOT)}")

    # rebuild the offline index
    print("\nrebuilding offline index ...")
    subprocess.run([sys.executable, str(ROOT / "tools" / "offline_index.py"), "--build"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
