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
    ap.add_argument("--withdrawn", action="store_true",
                    help="also show guidance a NEWER source document removed (data/withdrawn/). "
                         "Clearly labelled: it was official once and is not current.")
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
    if a.withdrawn:
        # Kept out of the corpus on purpose (see data/withdrawn/*.json "_why_not_in_the_corpus"):
        # the corpus must stay the parse of exactly one document. Joined on demand, and never
        # presented as current — the label is not decoration, it is the whole point.
        shown = 0
        for wf in sorted((DATA / "withdrawn").glob("*.withdrawn.json")):
            doc = json.loads(wf.read_text(encoding="utf-8"))
            for code, e in doc.get("entries", {}).items():
                if a.code and not code.startswith(a.code):
                    continue
                if a.subject and doc.get("subject") != a.subject:
                    continue
                if q and not any(q in str(v).lower() for v in e["withdrawn_fields"].values()):
                    continue
                if shown == 0:
                    print(f"\n--- WITHDRAWN guidance (NOT current; removed by a newer official "
                          f"document) ---")
                for field, val in e["withdrawn_fields"].items():
                    print(f"  {code:24} [withdrawn {field}] {str(val)[:90]}")
                shown += 1
                if shown >= a.limit:
                    break
        if shown:
            print(f"  ({shown} withdrawn entr(ies). Source: {doc['withdrawn_from']['file']} "
                  f"sha256 {doc['withdrawn_from']['sha256'][:12]}. Do not cite as current.)")
    if rows:
        print("\nVerify on CPALMS: https://www.cpalms.org/search/Standard")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
