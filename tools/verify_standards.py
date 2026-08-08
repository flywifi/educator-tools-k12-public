#!/usr/bin/env python3
"""Offline standards-code resolver (standards-verification.md §2/§5). Stdlib-only; no network.

Resolves cited standard codes against the committed Florida corpus
(shared/standards/resources/florida/data/ — 6,500+ enumerated codes with statement text),
validates CCSS/NGSS coding schemes (adapters are scheme-only: structure is checkable offline,
existence is not), and classifies everything else honestly. States distinguish "looked it up and
it is absent" (not_found — BLOCKING only where the corpus is authoritative) from "cannot look
this up offline" (advisory). A best-effort corpus (social studies .doc parse; partial ELD) never
produces a blocking verdict — a parser gap must not manufacture a "fabricated standard" finding.

Usage:
  python3 tools/verify_standards.py MA.3.NSO.1.1 ELA.K.F.1.1     # ad-hoc codes
  python3 tools/verify_standards.py --input artifact.json        # standards_cited/_set/grade_band/context
  python3 tools/verify_standards.py --input artifact.json --strict   # exit 1 on any blocking state
  python3 tools/verify_standards.py --self-test                  # embedded probe table (CI gate)

Importable: verify(codes, standards_set=None, grade_band=None, context=None) -> report dict.
The per-code `statement` field carries the registry origin form for the citation-mutation check
(standards-verification.md §6).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"

# FL prefix -> subject corpus file(s). SC. is shared by NGSSS science and Computer Science.
PREFIX_SUBJECTS = {"MA": ["math"], "ELA": ["ela"], "SC": ["science", "computer_science"],
                   "SS": ["social_studies"], "ELD": ["eld"]}
# Corpora where absence is NOT proof of fabrication (data/index.json's own caveats).
LOW_CONFIDENCE = {
    "social_studies": "social_studies corpus is a best-effort .doc parse (data/index.json) — verify on CPALMS",
    "eld": "only the 5 umbrella ELD.K12.ELL.* practices are enumerated — verify deeper ELD codes on CPALMS",
}

# Coding schemes. FL per florida-best.md §Coding schemes; validated against all corpus codes
# (--self-test). AP suffixes: AP.<n>[a-z] (MA/ELA/SS), In/Su/Pa.<n> (science access-point levels).
FL_CORE = re.compile(r"^(MA|ELA|SC|SS)\.(K|K12|\d{1,3})\.[A-Z]{1,4}\.\d{1,2}\.((AP|In|Su|Pa)\.)?\d{1,3}[a-z]?$")
FL_ELD = re.compile(r"^ELD\.K12\.ELL\.(LA|MA|SC|SS|SI)\.\d{1,2}$")
CCSS_MATH = re.compile(r"^CCSS\.MATH\.CONTENT\.(K|[1-8]|HS[A-Z])\.[A-Z]{1,4}\.[A-Z]\.\d{1,2}[a-z]?$")
CCSS_MP = re.compile(r"^CCSS\.MATH\.PRACTICE\.MP[1-8]$")
CCSS_ELA = re.compile(r"^CCSS\.ELA-LITERACY\.[A-Z]{1,4}\.(K|[1-9]|1[0-2]|9-10|11-12)\.\d{1,2}[a-z]?$")
NGSS_PE = re.compile(r"^(K|[1-5]|MS|HS)-(PS|LS|ESS|ETS)\d{1,2}-\d{1,2}$")

BLOCKING_STATES = {"not_found", "malformed"}
BANDS = {"K-2": {"K", "1", "2"}, "3-5": {"3", "4", "5"}, "6-8": {"6", "7", "8"},
         "9-12": {"9", "10", "11", "12"}}
SPAN_GRADES = {"K12": {"K"} | {str(n) for n in range(1, 13)},
               "912": {"9", "10", "11", "12"}, "68": {"6", "7", "8"},
               "612": {str(n) for n in range(6, 13)}}

_cache: dict[str, dict[str, dict]] = {}
_caveats: list[str] = []


def _load_subject(name: str) -> dict[str, dict] | None:
    """code -> entry for one FL subject corpus; cached; None (with caveat) if unavailable."""
    if name in _cache:
        return _cache[name]
    try:
        doc = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
        table: dict[str, dict] = {}
        for e in doc.get("standards", []):
            if e["code"] in table:
                _caveats.append(f"duplicate code {e['code']} in {name} corpus (first entry wins)")
                continue
            table[e["code"]] = e
    except Exception as exc:
        _caveats.append(f"corpus_unavailable:{name}:{exc.__class__.__name__}")
        table = None  # type: ignore[assignment]
    _cache[name] = table
    return table


def _grade_set(token: str) -> set[str]:
    return SPAN_GRADES.get(token, {token})


def _band_match(code_grade: str, grade_band: str | None):
    if not grade_band or grade_band not in BANDS:
        return None
    return bool(_grade_set(str(code_grade)) & BANDS[grade_band])


def _suggest(code: str, tables: list[dict[str, dict]]) -> str:
    """Up to 3 real codes sharing the grade+strand prefix (first 3 dotted segments)."""
    prefix = ".".join(code.split(".")[:3]) + "."
    hits = [c for t in tables if t for c in t if c.startswith(prefix)][:3]
    return f" nearby codes: {', '.join(hits)}" if hits else ""


def _set_mismatch(family: str, standards_set: str | None) -> str:
    if not standards_set:
        return ""
    s = standards_set.lower()
    fl_set = any(k in s for k in ("b.e.s.t", "best", "ngsss", "florida"))
    ccss_set = "ccss" in s or "common core" in s
    if family.startswith("fl-") and ccss_set:
        return f" set_mismatch: FL code under standards_set '{standards_set}'"
    if family in ("ccss", "ngss") and fl_set and not ccss_set:
        return f" set_mismatch: {family.upper()} code under standards_set '{standards_set}'"
    return ""


def _resolve_one(code: str, standards_set, grade_band, applicability) -> dict:
    r = {"code": code, "framework": "", "state": "", "type": None, "grade": None,
         "grade_band_match": None, "statement": None, "detail": ""}
    c = code.strip()
    prefix = c.split(".", 1)[0] if "." in c else c

    # Case-only mismatch against an FL family: canonical form is uppercase.
    if prefix.upper() in PREFIX_SUBJECTS and prefix != prefix.upper():
        r.update(framework="fl", state="malformed",
                 detail=f"FL codes are uppercase-canonical — did you mean {c.upper()}?")
        return r

    if prefix in PREFIX_SUBJECTS:  # Florida enumerated families
        subjects = PREFIX_SUBJECTS[prefix]
        r["framework"] = f"fl-{'/'.join(subjects)}"
        scheme = FL_ELD if prefix == "ELD" else FL_CORE
        tables = [_load_subject(s) for s in subjects]
        for name, table in zip(subjects, tables):
            if table and c in table:
                e = table[c]
                r.update(state="resolved", type=e.get("type"), grade=str(e.get("grade")),
                         statement=e.get("statement"),
                         grade_band_match=_band_match(str(e.get("grade")), grade_band),
                         detail=_set_mismatch("fl-" + name, standards_set).strip())
                if r["grade_band_match"] is False:
                    r["detail"] = (r["detail"] + f" grade '{e.get('grade')}' is outside band '{grade_band}'").strip()
                return r
        if not scheme.match(c):
            r.update(state="malformed",
                     detail=f"violates the {prefix} coding scheme (florida-best.md §Coding schemes)")
            return r
        if all(t is None for t in tables):
            r.update(state="scheme_valid_unenumerated",
                     detail="corpus unavailable this run — structure valid, existence unchecked")
            return r
        low = [LOW_CONFIDENCE[s] for s in subjects if s in LOW_CONFIDENCE]
        if low:
            r.update(state="not_found_low_confidence", detail=low[0] + _suggest(c, tables))
        else:
            r.update(state="not_found",
                     detail=f"absent from the enumerated FL corpus ({'/'.join(subjects)}); "
                            f"a fabricated standard is a QG §11.4 critical failure." + _suggest(c, tables))
        return r

    if c.startswith("CCSS."):
        r["framework"] = "ccss"
        if CCSS_MATH.match(c) or CCSS_MP.match(c) or CCSS_ELA.match(c):
            r.update(state="scheme_valid_unenumerated",
                     detail="structure valid; existence not verifiable offline — CCSS is a "
                            "scheme-only adapter (shared/standards/ccss.md), not an enumerated corpus"
                            + _set_mismatch("ccss", standards_set))
        else:
            r.update(state="malformed", detail="violates the CCSS coding scheme (shared/standards/ccss.md §1)")
        return r

    if NGSS_PE.match(c) or re.match(r"^(K|[1-5]|MS|HS)-[A-Z]", c):
        r["framework"] = "ngss"
        if NGSS_PE.match(c):
            r.update(state="scheme_valid_unenumerated",
                     detail="structure valid; existence not verifiable offline — NGSS is a "
                            "scheme-only adapter (shared/standards/ngss.md)" + _set_mismatch("ngss", standards_set))
        else:
            r.update(state="malformed", detail="violates the NGSS PE coding scheme (shared/standards/ngss.md §1)")
        return r

    # No known scheme. Private frameworks (shared/standards/frameworks/) publish prose
    # code_pattern descriptions with codes_verified:false, so no pattern match is possible yet.
    r["framework"] = "unknown"
    if applicability in ("school_defined", "parent_selected"):
        r.update(state="unknown_framework",
                 detail="matches no known scheme; if this is a school framework, register it in "
                        "shared/standards/frameworks/ (context permits non-state frameworks)")
    else:
        r.update(state="unknown_framework",
                 detail="matches no known scheme under a state-standards context "
                        "(standards_applicability=" + str(applicability) + ") — verify the code or the context")
    return r


def verify(codes, standards_set=None, grade_band=None, context=None) -> dict:
    del _caveats[:]
    applicability = (context or {}).get("standards_applicability") if isinstance(context, dict) else None
    results = [_resolve_one(str(c), standards_set, grade_band, applicability)
               for c in codes if str(c).strip()]
    summary: dict[str, int] = {}
    for r in results:
        summary[r["state"]] = summary.get(r["state"], 0) + 1
    loaded = [s for s, t in _cache.items() if t]
    return {"tool": "verify-standards", "codes_checked": len(results), "results": results,
            "summary": summary,
            "blocking": [r["code"] for r in results if r["state"] in BLOCKING_STATES],
            "advisory": [r["code"] for r in results
                         if r["state"] not in BLOCKING_STATES
                         and (r["state"] != "resolved" or r["grade_band_match"] is False or r["detail"])],
            "corpus": {"fl_subjects_loaded": sorted(loaded),
                       "fl_total_codes": sum(len(_cache[s]) for s in loaded),
                       "caveats": sorted({LOW_CONFIDENCE[s] for s in loaded if s in LOW_CONFIDENCE}
                                         | set(_caveats))}}


# --- self-test -------------------------------------------------------------------------------
# (code, kwargs, expected_state, expected_blocking, expected_band_match_or_None)
PROBES = [
    ("MA.3.NSO.1.1", {}, "resolved", False, None),
    ("  MA.3.NSO.1.1  ", {}, "resolved", False, None),                       # whitespace
    ("ma.3.nso.1.1", {}, "malformed", True, None),                           # case-canonical
    ("MA.K.NSO.1.AP.1", {}, "resolved", False, None),                        # math access point
    ("ELA.K.F.1.AP.1a", {}, "resolved", False, None),                        # lettered AP
    ("SC.K.L.14.In.1", {}, "resolved", False, None),                         # science AP level
    ("MA.K12.MTR.1.1", {"grade_band": "3-5"}, "resolved", False, True),      # practice spans all
    ("ELA.K12.EE.1.1", {}, "resolved", False, None),
    ("SC.K12.CTR.1.1", {}, "resolved", False, None),                         # CS practice via SC.
    ("SC.K.CC.1.1", {}, "resolved", False, None),                            # CS content via SC.
    ("SC.K.L.14.1", {}, "resolved", False, None),                            # NGSSS science via SC.
    ("MA.912.AR.1.1", {"grade_band": "9-12"}, "resolved", False, True),
    ("MA.912.AR.1.1", {"grade_band": "3-5"}, "resolved", False, False),      # band mismatch advisory
    ("MA.3.NSO.9.99", {}, "not_found", True, None),                          # the fabricated-code case
    ("SS.7.C.1.99", {}, "not_found_low_confidence", False, None),            # best-effort corpus
    ("ELD.K12.ELL.LA.2", {}, "not_found_low_confidence", False, None),       # partial corpus
    ("MA.3.NSO", {}, "malformed", True, None),                               # truncated
    ("CCSS.MATH.CONTENT.3.NF.A.1", {}, "scheme_valid_unenumerated", False, None),
    ("CCSS.MATH.CONTENT.HSA.REI.B.3", {}, "scheme_valid_unenumerated", False, None),
    ("CCSS.MATH.PRACTICE.MP1", {}, "scheme_valid_unenumerated", False, None),
    ("CCSS.ELA-LITERACY.RI.11-12.7", {}, "scheme_valid_unenumerated", False, None),
    ("CCSS.MATH.3.NF.A.1", {}, "malformed", True, None),                     # missing CONTENT
    ("3-LS1-1", {}, "scheme_valid_unenumerated", False, None),
    ("HS-ESS1-6", {}, "scheme_valid_unenumerated", False, None),
    ("MS-XX1-1", {}, "malformed", True, None),                               # bad NGSS DCI
    ("XYZ.1.2.3", {"context": {"standards_applicability": "best_ngsss_apply"}},
     "unknown_framework", False, None),
    ("XYZ.1.2.3", {"context": {"standards_applicability": "school_defined"}},
     "unknown_framework", False, None),
    ("MA.3.NSO.1.1", {"standards_set": "CCSS-Math 2010"}, "resolved", False, None),  # set_mismatch detail
]


def self_test(invert: bool = False) -> int:
    """Run the probe table; every FL corpus code must also match its scheme regex (shape audit).
    --self-test-invert deliberately corrupts one expectation to prove this test can fail."""
    failures = 0
    for i, (code, kwargs, want_state, want_blocking, want_band) in enumerate(PROBES):
        want = "not_found" if (invert and i == 0) else want_state
        rep = verify([code], **kwargs)
        r = rep["results"][0]
        ok = (r["state"] == want
              and ((r["code"].strip() in rep["blocking"]) == want_blocking)
              and (want_band is None or r["grade_band_match"] is want_band))
        print(f"{'PASS' if ok else 'FAIL'} {code!r:38} -> {r['state']}"
              + (f" band_match={r['grade_band_match']}" if want_band is not None else ""))
        failures += 0 if ok else 1
    # set_mismatch detail must actually appear on the cross-family probe
    rep = verify(["MA.3.NSO.1.1"], standards_set="CCSS-Math 2010")
    if "set_mismatch" not in rep["results"][0]["detail"]:
        print("FAIL set_mismatch detail missing"); failures += 1
    # Shape audit: every corpus code matches its family scheme (proves the malformed check
    # can never brand a real committed code as malformed).
    bad = 0
    for subj in ("math", "ela", "science", "social_studies", "computer_science", "eld"):
        table = _load_subject(subj) or {}
        scheme = FL_ELD if subj == "eld" else FL_CORE
        for c in table:
            if not scheme.match(c):
                bad += 1
                if bad <= 5:
                    print(f"FAIL shape-audit {subj}: {c} does not match scheme")
    print(f"shape-audit: {bad} corpus code(s) outside scheme across "
          f"{sum(len(_cache[s]) for s in _cache if _cache[s])} codes")
    failures += bad
    print(f"self-test: {failures} failure(s) across {len(PROBES)} probes + shape audit")
    return 1 if failures else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Offline standards-code resolver (report-only by default).")
    ap.add_argument("codes", nargs="*", help="standard codes to resolve")
    ap.add_argument("--input", metavar="ARTIFACT_JSON",
                    help="read standards_cited/standards_set/grade_band/context from an artifact")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any code is in a blocking state")
    ap.add_argument("--self-test", action="store_true", help="run the embedded probe table + shape audit")
    ap.add_argument("--self-test-invert", action="store_true", help=argparse.SUPPRESS)  # dev-only
    a = ap.parse_args(argv)

    if a.self_test or a.self_test_invert:
        return self_test(invert=a.self_test_invert)
    kwargs: dict = {}
    codes = list(a.codes)
    if a.input:
        art = json.loads(Path(a.input).read_text(encoding="utf-8"))
        codes += [c for c in (art.get("standards_cited") or []) if str(c).strip()]
        kwargs = {"standards_set": art.get("standards_set"),
                  "grade_band": art.get("grade_band"), "context": art.get("context")}
    if not codes:
        ap.error("no codes given (positional or --input)")
    report = verify(codes, **kwargs)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if (a.strict and report["blocking"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
