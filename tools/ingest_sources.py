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
INGESTED = ROOT / "canonical-sources" / "registries" / "ingested-sources.json"


def set_out_root(root: Path) -> None:
    """Redirect ALL data writes under `root` instead of the repo — test isolation: a run against a
    throwaway inbox can't touch the committed registries. Mirrors the canonical-sources/ layout."""
    global PRIV_DIR, COURSES, INGESTED
    PRIV_DIR = root / "canonical-sources" / "schools" / "private"
    COURSES = root / "canonical-sources" / "references" / "fl-course-codes.json"
    INGESTED = root / "canonical-sources" / "registries" / "ingested-sources.json"


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", v))).strip()


def _norm_name(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()


def _read_text(path: Path) -> str:
    """i18n-aware decode so foreign school names / accents survive (NOT utf-8/replace, which mangles
    Windows-1252 / Shift-JIS / etc.). Prefers the shared docintel decoder; stdlib-safe fallback."""
    data = path.read_bytes()
    try:
        sys.path.insert(0, str(ROOT / "shared"))
        from docintel.html_util import decode_bytes
        return decode_bytes(data)
    except Exception:
        try:
            from charset_normalizer import from_bytes
            best = from_bytes(data).best()
            if best is not None:
                return str(best)
        except Exception:
            pass
        return data.decode("utf-8", "replace")


def _saved_url(text: str) -> str | None:
    m = re.search(r"saved from url=\(\d+\)(\S+)", text)
    return m.group(1).strip() if m else None


def _title(text: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return _clean(m.group(1))[:120] if m else None


def catalog_base(entries: list[dict]) -> int:
    """Record EVERY ingested file at a base level in ingested-sources.json — URL, type, status, rows
    — so even unparsed sources are cataloged for later enrichment (no per-type parser needed up front).
    Deduped by source_url (else filename). Merges/refreshes existing entries."""
    reg = {"_comment": "Base-level manifest of every file fed to tools/ingest_sources.py. Captures the "
           "saved-from URL, a type guess, parse status, and row count for each — so an UNPARSED source "
           "is still logged (with its URL) and a parser/registry can be added later. Nothing fabricated.",
           "domain": "ingested-sources", "version": "1.0.0", "sources": []}
    if INGESTED.exists():
        try:
            reg = json.loads(INGESTED.read_text(encoding="utf-8"))
        except Exception:
            pass
    by_key = {(s.get("source_url") or s.get("file")): s for s in reg.get("sources", [])}
    n_new = 0
    for e in entries:
        k = e.get("source_url") or e.get("file")
        if k in by_key:
            by_key[k].update({kk: vv for kk, vv in e.items() if vv})
        else:
            by_key[k] = e; n_new += 1
    reg["sources"] = sorted(by_key.values(), key=lambda s: (s.get("status", ""), s.get("file", "")))
    reg["updated"] = "2026-06-29"
    INGESTED.parent.mkdir(parents=True, exist_ok=True)
    INGESTED.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return n_new


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
    ap.add_argument("--out-root", help="write all data under this dir instead of the repo "
                                       "(test isolation; the offline index rebuild is skipped)")
    a = ap.parse_args(argv)
    if a.out_root:
        set_out_root(Path(a.out_root).resolve())
        print(f"[out-root] writing data under {a.out_root} (repo registries untouched)")
    inbox = Path(a.inbox)
    if not inbox.exists():
        print(f"inbox not found: {inbox}", file=sys.stderr); return 1

    priv_incoming, course_incoming, report, base_entries = [], [], [], []
    for f in sorted(inbox.iterdir()):
        if not f.is_file() or f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
            continue
        is_xlsx = f.suffix.lower() == ".xlsx"
        is_binary = f.suffix.lower() in (".zip", ".pdf", ".xls") and not is_xlsx
        text = "" if is_xlsx else _read_text(f)
        # .xls files are usually Office-HTML (readable); .zip/.pdf are opaque here
        if f.suffix.lower() == ".xls":
            is_binary = "<html" not in text[:200].lower()
        kind = detect(f, text)
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
        # base-level catalog entry for EVERY file (parsed or not)
        status = "parsed" if recs else ("opaque_binary" if is_binary else "captured_unparsed")
        base_entries.append({
            "file": f.name, "source_url": _saved_url(text) if text else None,
            "title": _title(text) if text else None, "detected_type": kind,
            "status": status, "rows": len(recs), "captured": "2026-06-29",
            "note": None if recs else "no parser yet — URL/title captured at base level for later enrichment",
        })

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
        print(f"\n[dry-run] would catalog {len(base_entries)} source files at base level; no files written.")
        return 0

    n_cat = catalog_base(base_entries)
    print(f"base catalog: {len(base_entries)} files recorded in {INGESTED.relative_to(ROOT)} ({n_cat} new)")

    PRIV_DIR.mkdir(parents=True, exist_ok=True)
    consolidated.write_text(json.dumps({
        "_comment": "Consolidated + DEDUPED private/independent schools, merged across all ingested "
                    "sources (AISF, NCES PSS, ...) by ingest_sources.py. Keyed by NCES PSS id, else "
                    "normalized name; 'sources' lists every directory an entry was seen in. Public, no PII.",
        "domain": "private-schools-consolidated", "captured": "2026-06-29",
        "count": len(merged_list), "human_review_required": True, "members": merged_list,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {consolidated.relative_to(ROOT)}")

    # rebuild the offline index (skipped under --out-root: the index reads/writes real repo paths)
    if not a.out_root:
        print("\nrebuilding offline index ...")
        subprocess.run([sys.executable, str(ROOT / "tools" / "offline_index.py"), "--build"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
