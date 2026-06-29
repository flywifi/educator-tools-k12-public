#!/usr/bin/env python3
"""Query the enumerated Florida standards (shared/standards/resources/florida/data/).

Examples:
  python3 tools/fl_lookup.py --subject math --grade 3 --search fraction
  python3 tools/fl_lookup.py --code MA.3.FR            # prefix match
  python3 tools/fl_lookup.py --subject ela --search "main idea"
  python3 tools/fl_lookup.py --code ELA.K.F.1.1        # exact
Filters combine (AND). Always verify results on CPALMS (https://www.cpalms.org/search/Standard).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "shared" / "standards" / "resources" / "florida" / "data"


def load(subject: str | None):
    files = [DATA / f"{subject}.json"] if subject else sorted(DATA.glob("*.json"))
    for f in files:
        if f.name == "index.json" or not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for s in d.get("standards", []):
            s["subject"] = d["subject"]
            yield s


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", choices=["math", "ela", "science", "computer_science", "eld", "social_studies"])
    ap.add_argument("--grade")
    ap.add_argument("--type", choices=["benchmark", "access_point", "practice"])
    ap.add_argument("--code", help="exact or prefix match on the code")
    ap.add_argument("--search", help="case-insensitive keyword in the statement")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(argv)

    if not DATA.exists():
        print("No data yet — run: python3 tools/parse_fl_standards.py")
        return 1

    q = (a.search or "").lower()
    rows = []
    for s in load(a.subject):
        if a.grade and s.get("grade") != a.grade:
            continue
        if a.type and s.get("type") != a.type:
            continue
        if a.code and not s["code"].startswith(a.code):
            continue
        if q and q not in (s.get("statement") or "").lower():
            continue
        rows.append(s)

    print(f"{len(rows)} match(es)" + (f" (showing {a.limit})" if len(rows) > a.limit else ""))
    for s in rows[: a.limit]:
        print(f"  {s['code']:24} [{s['subject']}/{s['type']}] {s.get('statement','')[:90]}")
    if rows:
        print("\nVerify on CPALMS: https://www.cpalms.org/search/Standard")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
