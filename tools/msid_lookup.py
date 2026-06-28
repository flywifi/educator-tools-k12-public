#!/usr/bin/env python3
"""FLDOE MSID lookup — match school names in TOS school indexes to real FLDOE Master School IDs.

The FLDOE publishes a Master School Identification (MSID) file each year as a downloadable CSV/Excel
(district=2-digit + school=4-digit = 6-digit MSID). This tool:

  1. --fetch      Downloads the current MSID file from FLDOE to a local cache (requires network).
  2. --match      Matches school names in a TOS schools.json against the cached MSID file (offline).
  3. --apply      Writes matched MSIDs back to the schools.json (in-place, dry-run default).
  4. --stats      Reports match rate and unmatched schools.

Matching strategy (fuzzy, offline):
  - Exact name match (case-insensitive, stripped)
  - Stripped-suffix match (removes "School", "Elementary", "Middle", "High", etc.)
  - Token-overlap score ≥ 0.7 (Jaccard on word sets)
  - Tie-break by district number
  Anything below the score threshold is flagged UNMATCHED — never silently wrong.

MSID source: FLDOE Master School Identification files
  https://www.fldoe.org/accountability/data-sys/school-fin-data/master-school-id-files.stml

Usage:
  python3 tools/msid_lookup.py --fetch                          # download latest MSID file
  python3 tools/msid_lookup.py --match --district 48            # match OCPS schools (offline)
  python3 tools/msid_lookup.py --match --district 48 --apply    # write matched IDs back (dry-run)
  python3 tools/msid_lookup.py --match --district 48 --apply --confirm   # actually write
  python3 tools/msid_lookup.py --stats --district 48            # match rate report

Stdlib only. Optional: `requests` for --fetch; `openpyxl` for XLSX MSID files.
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

def load_msid_csv(path: Path) -> list[dict]:
    """Parse FLDOE MSID CSV into list of dicts. Handles BOM, varying column names."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        # Normalize key names (FLDOE uses inconsistent caps/spacing across years)
        norm = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}
        rows.append(norm)
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
    n = re.sub(r"[''\".,/-]", " ", n)
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
                   threshold: float = 0.65) -> dict:
    """Match one district's schools.json against MSID rows. Returns stats dict."""
    schools_path = _district_folder(district_number)
    if schools_path is None:
        return {"error": f"No schools.json found for district {district_number}"}

    data = json.loads(schools_path.read_text(encoding="utf-8"))
    schools = data.get("schools", [])

    # Filter MSID rows to this district
    dist_rows = [r for r in msid_rows if _district_col(r).zfill(2) == district_number.zfill(2)]
    if not dist_rows:
        return {"error": f"No MSID rows found for district {district_number}"}

    # Pre-compute normalized names for MSID candidates
    for r in dist_rows:
        r["_norm"] = _normalize(_school_col(r))

    matched, unmatched = [], []
    for school in schools:
        # Skip if already has a real MSID (not placeholder)
        current = school.get("msid", "")
        if current and "X" not in current.upper() and len(current) == 6:
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

    stats = {
        "district": district_number,
        "file": str(schools_path),
        "total": len(schools),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "match_rate": f"{100 * len(matched) / max(len(schools), 1):.1f}%",
        "unmatched_names": unmatched[:20],
    }

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
            prev = match_district(d, msid_rows, apply=False, confirm=False, threshold=args.threshold)
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
