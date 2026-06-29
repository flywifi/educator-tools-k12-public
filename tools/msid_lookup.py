#!/usr/bin/env python3
"""FLDOE MSID lookup — match school names in TOS school indexes to real FLDOE Master School IDs.

The FLDOE Master School ID (MSID = 2-digit district + 4-digit school = 6 digits) is NOT a downloadable
file. The authoritative source is an interactive web app — the Education Data System (EDS) at
eds.fldoe.org/EDS/MasterSchoolID/Selection.cfm — which renders every Florida school as an HTML list
with DIST/SCHL numbers in the links. The reliable, offline-friendly workflow is therefore:

    SAVE the EDS page from a browser (Ctrl+S → "Webpage, HTML only"), then parse it OFFLINE here.

This tool reads that saved .html (and also .xlsx/.csv if a future year ships a file), matches school
names against a TOS schools.json, and stamps the real MSIDs — all offline, no tokens, no live network.

  --inspect   Show detected columns/links + a match preview (no writes). RUN THIS FIRST.
  --match     Match school names in a TOS schools.json against the MSID source (offline).
  --apply     Write matched MSIDs back to the schools.json (dry-run unless --confirm).
  --stats     Report match rate + unmatched schools.

Matching (fuzzy, offline, safe): exact normalized-name match first; else Jaccard token overlap above
--threshold (default 0.65). Apostrophes/suffixes ("School/Elementary/...") are normalized away.
Anything below threshold is left as a placeholder and reported UNMATCHED — never silently wrong,
never fabricated.

Usage:
  python3 tools/msid_lookup.py --inspect --district 48 --msid-file SavedEDSPage.html
  python3 tools/msid_lookup.py --match   --district 48 --msid-file SavedEDSPage.html            # preview
  python3 tools/msid_lookup.py --match   --district 48 --apply --confirm --msid-file SavedEDSPage.html

Accepts --msid-file as .html (saved EDS page, preferred), .xlsx/.xls (openpyxl), or .csv (stdlib).
--fetch is best-effort only (FLDOE blocks bots + relocates URLs); the saved-page path is the reliable one.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "canonical-sources" / "registries" / "msid-cache"
SCHOOLS_DIR = ROOT / "canonical-sources" / "schools"

# NOTE: FLDOE relocates this file every year and blocks non-browser requests, so the
# auto-fetch URL is UNVERIFIED and may 403. The reliable path is to download the current
# "Master School Identification File" by hand from the FLDOE page below (one click in a
# browser) and point the tool at it with --msid-file. Auto-fetch is best-effort only.
MSID_PAGE = "https://www.fldoe.org/accountability/data-sys/school-fin-data/master-school-id-files.stml"
MSID_URL = (
    "https://www.fldoe.org/core/fileparse.php/7584/urlt/MasterSchoolID.csv"
)
DISTRICT_NAMES = {
    "48": ["ocps", "orange"],
    "59": ["seminole", "scps"],
    "49": ["osceola"],
    "35": ["lake"],
    "05": ["brevard"],
    "64": ["volusia"],
    "53": ["polk"],
}


# ---------------------------------------------------------------------------
# MSID file fetching
# ---------------------------------------------------------------------------

def fetch_msid(url: str = MSID_URL, cache_dir: Path = CACHE_DIR) -> Path:
    """Download the FLDOE MSID file to cache_dir/MasterSchoolID.csv. Polite 1-req/sec."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / "MasterSchoolID.csv"

    try:
        import requests  # prefer requests (follows redirects, better UA)
        headers = {"User-Agent": "TOS-MSID-Lookup/1.0 (edu-tools; public FLDOE data)"}
        time.sleep(1.0)
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
    except ImportError:
        req = urllib.request.Request(url, headers={"User-Agent": "TOS-MSID-Lookup/1.0"})
        time.sleep(1.0)
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())

    print(f"Downloaded {len(dest.read_bytes())} bytes → {dest}", file=sys.stderr)
    return dest


# ---------------------------------------------------------------------------
# MSID file parsing
# ---------------------------------------------------------------------------

def _normalize_row(raw: dict) -> dict:
    """Lower-case + underscore the keys; strip values. FLDOE varies caps/spacing across years."""
    return {str(k).strip().lower().replace(" ", "_"): ("" if v is None else str(v).strip())
            for k, v in raw.items()}


def load_msid_csv(path: Path) -> list[dict]:
    """Parse a FLDOE MSID file (CSV or XLSX) into normalized dict rows.

    FLDOE publishes the Master School ID file as Excel (.xlsx) most years and CSV some years,
    so this reads either. XLSX needs `openpyxl` (pip install openpyxl); CSV is stdlib.
    """
    suffix = path.suffix.lower()
    rows: list[dict] = []

    if suffix in (".html", ".htm"):
        # FLDOE EDS Master School ID page (eds.fldoe.org/EDS/MasterSchoolID/Selection.cfm)
        # saved from a browser: every school is a link Schooldisplay.cfm?DIST=##&SCHL=####>NAME</a>.
        # This is the authoritative list and the ONLY reliable way to get it (no file download exists).
        import html as _html
        text = path.read_text(encoding="utf-8", errors="replace")
        pat = re.compile(r'Schooldisplay\.cfm\?DIST=(\d+)&(?:amp;)?SCHL=(\d+)">([^<]+)</a>', re.I)
        for dist, schl, name in pat.findall(text):
            rows.append(_normalize_row({
                "district_number": dist,
                "school_number": schl,
                "school_name": _html.unescape(name).strip(),
            }))
        return rows

    if suffix in (".xlsx", ".xlsm", ".xls"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit(
                f"\n{path.name} is an Excel file. Install the reader once:\n"
                f"    pip install openpyxl\n"
                f"...then re-run. (Or open it in Excel and Save As CSV and point --msid-file at that.)"
            )
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        header: list[str] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                header = [str(c).strip() if c is not None else f"col{j}" for j, c in enumerate(row)]
                continue
            if row is None or all(c is None for c in row):
                continue
            raw = {header[j]: row[j] for j in range(min(len(header), len(row)))}
            rows.append(_normalize_row(raw))
        wb.close()
        return rows

    # default: CSV (handles BOM)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        rows.append(_normalize_row(row))
    return rows


def _district_col(row: dict) -> str:
    """Extract 2-digit district number from an MSID row."""
    for key in ("district_number", "district_no", "dist_no", "district"):
        if key in row:
            return str(row[key]).zfill(2)
    # Try extracting from MSID if present
    for key in ("msid", "school_id", "master_school_id"):
        if key in row and len(row[key]) >= 2:
            return str(row[key])[:2].zfill(2)
    return ""


def _school_col(row: dict) -> str:
    """Extract school name from an MSID row."""
    for key in ("school_name", "school_nm", "name", "school"):
        if key in row:
            return row[key]
    return ""


def _msid_col(row: dict) -> str:
    """Extract full 6-digit MSID from a row (district+school concatenated)."""
    for key in ("msid", "master_school_id", "school_id"):
        if key in row:
            return str(row[key]).zfill(6)
    # build from district + school number
    dist = _district_col(row)
    for key in ("school_number", "school_no", "sch_no"):
        if key in row:
            return dist + str(row[key]).zfill(4)
    return ""


def _status_col(row: dict) -> str:
    for key in ("status", "school_status", "active"):
        if key in row:
            return str(row[key]).strip().lower()
    return "unknown"


# ---------------------------------------------------------------------------
# Name normalization + matching
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(
    r"\b(school|elementary|middle|high|center|academy|charter|magnet|virtual|"
    r"technical|college|institute|community|learning|education|preparatory|prep|"
    r"pk|k-8|junior|senior|jr|sr)\b",
    re.IGNORECASE,
)


def _normalize(name: str) -> str:
    """Lower-case, strip punctuation and common school suffixes for fuzzy matching."""
    n = name.lower()
    # Apostrophes are DELETED (not spaced) so FLDOE's "HUNTERS CREEK" == our "Hunter's Creek".
    n = re.sub(r"['’‘]", "", n)
    n = re.sub(r"[\".,/()&-]", " ", n)
    n = _SUFFIX_RE.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _match_name(name: str, candidates: list[dict], threshold: float = 0.65) -> dict | None:
    """Find best MSID row matching `name`. Returns None if best score < threshold."""
    norm_name = _normalize(name)
    best_score, best = 0.0, None
    for cand in candidates:
        cand_norm = cand.get("_norm", "")
        # Exact match wins immediately
        if norm_name == cand_norm:
            return cand
        score = _jaccard(norm_name, cand_norm)
        if score > best_score:
            best_score, best = score, cand
    if best_score >= threshold:
        return best
    return None


# ---------------------------------------------------------------------------
# District folder detection
# ---------------------------------------------------------------------------

def _district_folder(district_number: str) -> Path | None:
    """Find the schools directory for a given district number."""
    aliases = DISTRICT_NAMES.get(district_number.zfill(2), [])
    for alias in aliases:
        p = SCHOOLS_DIR / alias / "schools.json"
        if p.exists():
            return p
    # Fallback: any folder whose schools.json has matching district_number
    for p in SCHOOLS_DIR.rglob("schools.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if str(d.get("district_number", "")).zfill(2) == district_number.zfill(2):
                return p
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Main match logic
# ---------------------------------------------------------------------------

def match_district(district_number: str, msid_rows: list[dict],
                   apply: bool = False, confirm: bool = False,
                   threshold: float = 0.65, force: bool = False) -> dict:
    """Match one district's schools.json against MSID rows. Returns stats dict.

    force=True re-matches EVERY school against the authoritative FLDOE list and OVERWRITES any
    existing MSID, resetting non-matches to a 'DDXXXX' placeholder. Use this when existing MSIDs
    can't be trusted (e.g. seeded by a generator) so no unverified number survives. Without force,
    a school that already carries a 6-digit non-placeholder MSID is left untouched ('kept')."""
    schools_path = _district_folder(district_number)
    if schools_path is None:
        return {"error": f"No schools.json found for district {district_number}"}

    data = json.loads(schools_path.read_text(encoding="utf-8"))
    schools = data.get("schools", [])
    placeholder = f"{district_number.zfill(2)}XXXX"

    # Filter MSID rows to this district
    dist_rows = [r for r in msid_rows if _district_col(r).zfill(2) == district_number.zfill(2)]
    if not dist_rows:
        return {"error": f"No MSID rows found for district {district_number}"}

    # Pre-compute normalized names for MSID candidates
    for r in dist_rows:
        r["_norm"] = _normalize(_school_col(r))

    matched, unmatched, reset = [], [], 0
    for school in schools:
        current = school.get("msid", "")
        is_placeholder = (not current) or ("X" in current.upper()) or (len(current) != 6)

        # Without --force, trust an existing real-looking MSID and leave it alone.
        if not force and not is_placeholder:
            matched.append({"name": school["school_name"], "msid": current, "action": "kept"})
            continue

        hit = _match_name(school["school_name"], dist_rows, threshold)
        if hit:
            new_msid = _msid_col(hit)
            matched.append({
                "name": school["school_name"],
                "msid": new_msid,
                "matched_to": _school_col(hit),
                "action": "matched",
            })
            if apply:
                school["msid"] = new_msid
                if _status_col(hit) in ("closed", "inactive", "0"):
                    school["status"] = "closed"
        else:
            unmatched.append(school["school_name"])
            # In force mode, clear any untrusted/fabricated MSID back to an honest placeholder.
            if apply and force and not is_placeholder:
                school["msid"] = placeholder
                reset += 1

    stats = {
        "district": district_number,
        "file": str(schools_path),
        "total": len(schools),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "match_rate": f"{100 * len(matched) / max(len(schools), 1):.1f}%",
        "unmatched_names": unmatched[:20],
    }
    if force:
        stats["reset_to_placeholder"] = reset

    if apply and confirm:
        schools_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        stats["written"] = True
    elif apply:
        stats["dry_run"] = True
        stats["note"] = "Pass --confirm to write changes"

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fetch", action="store_true", help="Download latest MSID CSV from FLDOE")
    p.add_argument("--match", action="store_true", help="Match school names to MSID rows")
    p.add_argument("--inspect", action="store_true",
                   help="Show detected columns + column mapping + a match preview (no writes). "
                        "Run this FIRST to confirm the parser understands your MSID file.")
    p.add_argument("--stats", action="store_true", help="Print match-rate statistics")
    p.add_argument("--apply", action="store_true", help="Write matched MSIDs back (dry-run unless --confirm)")
    p.add_argument("--confirm", action="store_true", help="Actually write changes (requires --apply)")
    p.add_argument("--district", help="District number(s), comma-separated (e.g. 48,59)")
    p.add_argument("--threshold", type=float, default=0.65, help="Jaccard match threshold 0-1 (default 0.65)")
    p.add_argument("--force", action="store_true",
                   help="Re-match EVERY school against FLDOE, overwriting existing MSIDs and resetting "
                        "non-matches to a DDXXXX placeholder. Use when existing MSIDs can't be trusted.")
    p.add_argument("--msid-file", help="Path to cached MSID CSV (default: auto)")
    args = p.parse_args(argv)

    if args.fetch:
        dest = fetch_msid()
        print(f"Cached: {dest}")
        return 0

    # Find MSID cache
    cache_file = Path(args.msid_file) if args.msid_file else CACHE_DIR / "MasterSchoolID.csv"
    if not cache_file.exists():
        print(f"MSID cache not found at {cache_file}. Run --fetch first, or pass --msid-file.", file=sys.stderr)
        return 1

    msid_rows = load_msid_csv(cache_file)
    print(f"Loaded {len(msid_rows)} MSID rows from {cache_file}", file=sys.stderr)

    # --inspect: show what the parser DETECTED so we can confirm the column mapping is right
    # before changing any data. This is the anti-"guessed and shipped" check.
    if args.inspect:
        cols = list(msid_rows[0].keys()) if msid_rows else []
        print("\n=== DETECTED COLUMNS (normalized) ===")
        print(cols)
        print("\n=== COLUMN MAPPING the tool will use ===")
        sample = msid_rows[0] if msid_rows else {}
        print(f"  district -> _district_col() = {_district_col(sample)!r}")
        print(f"  school   -> _school_col()   = {_school_col(sample)!r}")
        print(f"  msid     -> _msid_col()     = {_msid_col(sample)!r}")
        print(f"  status   -> _status_col()   = {_status_col(sample)!r}")
        print("\n=== FIRST 3 RAW ROWS ===")
        for r in msid_rows[:3]:
            print("  " + json.dumps({k: v for k, v in r.items() if k != "_norm"}, ensure_ascii=False))
        # Per-district match preview (dry-run, no writes)
        districts_p = [d.strip().zfill(2) for d in (args.district or "").split(",") if d.strip()] \
            or list(DISTRICT_NAMES.keys())
        for d in districts_p:
            dist_rows = [r for r in msid_rows if _district_col(r).zfill(2) == d.zfill(2)]
            print(f"\n=== DISTRICT {d}: {len(dist_rows)} MSID rows found ===")
            for r in dist_rows[:5]:
                print(f"  {_msid_col(r)}  {_school_col(r)}")
            prev = match_district(d, msid_rows, apply=False, confirm=False,
                                  threshold=args.threshold, force=args.force)
            print(f"  preview: {prev.get('matched')}/{prev.get('total')} would match "
                  f"({prev.get('match_rate')}); unmatched sample: {prev.get('unmatched_names', [])[:5]}")
        return 0

    districts = [d.strip() for d in (args.district or "").split(",") if d.strip()]
    if not districts:
        # Default to all known districts
        districts = list(DISTRICT_NAMES.keys())

    all_stats = []
    for district in districts:
        stats = match_district(
            district, msid_rows,
            apply=args.apply,
            confirm=args.confirm,
            threshold=args.threshold,
            force=args.force,
        )
        all_stats.append(stats)
        if args.stats or not args.apply:
            print(json.dumps(stats, indent=2))
        elif args.apply:
            print(f"District {district}: {stats.get('matched')}/{stats.get('total')} matched "
                  f"({stats.get('match_rate')}) {'[WRITTEN]' if stats.get('written') else '[dry-run]'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
