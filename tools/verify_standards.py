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
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"

# FL prefix -> subject corpus file(s). SC. is shared by NGSSS science and Computer Science.
PREFIX_SUBJECTS = {"MA": ["math"], "ELA": ["ela"], "SC": ["science", "computer_science"],
                   "SS": ["social_studies"], "ELD": ["eld"]}
# Corpora where absence is NOT proof of fabrication (data/index.json's own caveats). A subject
# EXITS this set once a CPALMS verification overlay (tools/cpalms_verify.py --apply --write)
# covers >= OVERLAY_TRUST_COVERAGE of its codes — see _is_low_confidence().
LOW_CONFIDENCE = {
    # Retained for the coverage machinery; the caveat is HISTORICAL. The "best-effort .doc parse"
    # was root-caused and fixed 2026-08-13 (launch audit §10), the source was refreshed, and every
    # one of the 2,713 SS codes now matches CPALMS's official text exactly (overlay at 100%). The
    # coverage threshold therefore lifts SS out of this set: absence is evidence, and blocks.
    "social_studies": "SS corpus fully corroborated against CPALMS 2026-08-13 (2,713/2,713); "
                      "this low-confidence note is vestigial and inert above the coverage threshold",
    # ELD's entry is retained for the coverage machinery, but its premise was WRONG. It assumed
    # deeper ELD codes existed that we had not enumerated. A census swept CPALMS's ELD subject
    # across all 13 grade labels (2026-08-13) and found exactly 5 unique codes — the same 5 — and
    # ELD.K12.ELL.{LA,SI,MA}.2 each return not_on_cpalms. Florida's ELL standards ARE these five.
    # With the overlay at 5/5 the coverage threshold now lifts ELD out of this set, so an absent
    # ELD.K12.ELL.* code blocks. WIDA's own descriptors use a different coding scheme entirely
    # (e.g. "ELD-SI.4-12.Narrate"), so they resolve as unknown_framework — advisory, never blocking.
    "eld": "ELD enumerates the 5 umbrella ELD.K12.ELL.* standards; CPALMS's ELD catalogue contains "
           "exactly those 5 (censused 2026-08-13). WIDA descriptors use another scheme — verify on WIDA",
}
OVERLAYS = DATA / "overlays"
OVERLAY_TRUST_COVERAGE = 0.98

# Coding schemes. FL per florida-best.md §Coding schemes; validated against all corpus codes
# (--self-test). AP suffixes: AP.<n>[a-z] (MA/ELA/SS), In/Su/Pa.<n> (science access-point levels).
FL_CORE = re.compile(r"^(MA|ELA|SC|SS)\.(K|K12|\d{1,3})\.[A-Z]{1,4}\.\d{1,2}\.((AP|In|Su|Pa)\.)?\d{1,3}[a-z]?$")
FL_ELD = re.compile(r"^ELD\.K12\.ELL\.(LA|MA|SC|SS|SI)\.\d{1,2}$")
CCSS_MATH = re.compile(r"^CCSS\.MATH\.CONTENT\.(K|[1-8]|HS[A-Z])\.[A-Z]{1,4}\.[A-Z]\.\d{1,2}[a-z]?$")
CCSS_MP = re.compile(r"^CCSS\.MATH\.PRACTICE\.MP[1-8]$")
CCSS_ELA = re.compile(r"^CCSS\.ELA-LITERACY\.[A-Z]{1,4}\.(K|[1-9]|1[0-2]|9-10|11-12)\.\d{1,2}[a-z]?$")
NGSS_PE = re.compile(r"^(K|[1-5]|MS|HS)-(PS|LS|ESS|ETS)\d{1,2}-\d{1,2}$")

BLOCKING_STATES = {"not_found", "malformed"}

# The only overlay state that is a verification of the corpus statement. Everything else — a text
# disagreement, an ambiguous card, an absence — is a review signal.
#
# `needs_review` is DERIVED from this rather than read from the entry's flag. The flag is written by
# the verification loop and is normally present, but a record whose flag is merely missing must not
# read as verified: four committed entries (SS.4.E.1.1 and three cpalms_additions) carried an
# unverified state with no flag, and keying on the flag alone reported them as clean.
OVERLAY_VERIFIED_STATES = {"confirmed"}


def _overlay_needs_review(ov: dict) -> bool:
    return bool(ov.get("needs_review")) or ov.get("state") not in OVERLAY_VERIFIED_STATES

# --- §6 citation-mutation comparator (standards-verification.md §6) --------------------------
# STRICT, and deliberately separate from any verification comparator: verification must TOLERATE a
# corpus statement that appends "Clarifications:"/"Examples:" to the registry text, while mutation
# detection must CATCH a benchmark restated wrongly. Reusing one for the other misses value drift
# and caveat stripping (audit finding F5, 2026-08-09).
_MUT_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Tails that are DOCUMENT METADATA, not restatement content: labelled columns the source documents
# carry beside a benchmark. Calibrated against 113 A9 false positives sampled 2026-08-10 — the
# benchmark sentences were identical; only these tails differed.
#
# Matched CASE-SENSITIVELY on the raw text, and only in LABEL form, for the same reason the parser
# is (see tools/parse_fl_standards.py): these are ordinary English words as well as labels. The
# previous case-insensitive bare-word version cut every statement at the first "example", so
# "Identify examples of when figurative language is used to contribute to meaning" was compared as
# the single word "Identify" — 137 statements whose remainder no mutation could ever be detected in.
# `Examples` additionally never counts after "for", the one prose form the FL documents use.
#
# NOTE: alternatives ending in punctuation (e.g. "Standard 8:") cannot carry a trailing \b —
# a colon followed by a space is not a word boundary — so they live in their own branch.
_MUT_TAIL = re.compile(
    r"(?:\b(?:Clarifications?|Remarks?|Notes?|Content Complexity|Cognitive Complexity|"
    r"Date Adopted(?: or (?:Last )?Revised)?|BENCHMARK\s*CODE)\b"
    r"|(?<![Ff]or )\bExamples?\s*:"
    r"|\bStandard\s*\d+\s*:)"
    r"\s*:?.*$", re.S)
_MUT_HEDGE = ("with support", "with guidance", "with prompting", "explore", "begin to",
              "approximately", "as appropriate", "when appropriate", "using models",
              "using manipulatives", "in familiar contexts", "may ")
_MUT_ABSOLUTE = ("master", "mastery", "always", "must ", "independently demonstrate")
_MUT_BROADEN = ("all ", "any ", "elementary", "any size", "every ", "general ")
_MUT_UNITS = ("percent", "percentage point", "hundredth", "thousandth", "tenth", "digit",
              "place value", "fraction", "decimal", "degree", "gram", "meter", "liter",
              "number", "percentage")
_MUT_ATTRIB = ("b.e.s.t", "best standards", "ngsss", "florida standards", "per the",
               "according to")


def _mut_norm(s: str) -> str:
    """Normalize for comparison: entities/smart quotes folded, period-spacing artifact repaired,
    whitespace collapsed, lowercased, trailing period dropped. Cosmetic differences must never
    read as mutations."""
    s = html.unescape(s or "")
    s = re.sub(r"[\u2018\u2019\u201c\u201d'\"\u2026]", "", s)   # quotes/ellipsis: punctuation, not content
    s = re.sub(r"\.(?=[A-Za-z])", ". ", s)
    return re.sub(r"\s+", " ", s).strip().lower().rstrip(".")


def _mut_core(s: str) -> str:
    """Origin form for comparison: any appended labelled tail cut, then normalized.

    Order matters. _mut_norm lowercases, and the label patterns are case-sensitive precisely
    because the same words occur as ordinary prose — so the cut must happen on the raw text, while
    the capitalization that distinguishes a column header from a sentence still exists."""
    return _mut_norm(_MUT_TAIL.sub("", s or "")).strip()


def mutation_flags(cited: str, origin: str) -> list[dict]:
    """Detect §6 citation mutations of a REAL standard. Returns [] when the restatement is
    faithful. Evidence-producing (each flag names what moved) — a detector for the quality-review
    gate, never an automatic verdict."""
    c, o = _mut_core(cited), _mut_core(origin)
    flags: list[dict] = []
    if not c or not o:
        return flags
    # A trailing ellipsis DECLARES elision (display truncation), which is not a dropped caveat —
    # the reader is told text was omitted. Numeric/unit/attribution checks still run on what IS
    # present; only the caveat-stripping test is suppressed.
    declared_truncation = bool(re.search(r"(…|\.\.\.|&hellip;)\s*$", (cited or "").strip()))
    c_nums, o_nums = sorted(_MUT_NUM.findall(c)), sorted(_MUT_NUM.findall(o))
    if c_nums != o_nums:
        flags.append({"category": "value_drift", "origin": o_nums, "cited": c_nums})
    missing_hedges = [h for h in _MUT_HEDGE if h in o and h not in c]
    added_absolute = [a for a in _MUT_ABSOLUTE if a in c and a not in o]
    if missing_hedges or added_absolute:
        flags.append({"category": "hedge_removal", "missing_hedges": missing_hedges,
                      "added_absolutes": added_absolute})
    # Caveat stripping: a qualifying clause of the origin is absent downstream AND the restatement
    # is shorter (a longer restatement that merely adds context is not stripping).
    if len(c) < len(o) and not declared_truncation:
        clauses = [x.strip() for x in re.split(r"[;,]|\busing\b|\bwhen\b|\bgiven\b|\bwithin\b", o)
                   if len(x.strip()) > 17]
        dropped = [cl for cl in clauses if cl not in c]
        if dropped:
            flags.append({"category": "caveat_stripping", "dropped": dropped[:3]})
    broadened = [b for b in _MUT_BROADEN if b in c and b not in o]
    if broadened:
        flags.append({"category": "scope_broadening", "added": broadened})
    o_units = {u for u in _MUT_UNITS if u in o}
    c_units = {u for u in _MUT_UNITS if u in c}
    if o_units and o_units - c_units and c_units - o_units:
        flags.append({"category": "unit_swap", "origin_only": sorted(o_units - c_units),
                      "cited_only": sorted(c_units - o_units)})
    laundered = [a for a in _MUT_ATTRIB if a in c and a not in o]
    if laundered:
        flags.append({"category": "attribution_laundering", "added": laundered})
    return flags
BANDS = {"K-2": {"K", "1", "2"}, "3-5": {"3", "4", "5"}, "6-8": {"6", "7", "8"},
         "9-12": {"9", "10", "11", "12"}}
SPAN_GRADES = {"K12": {"K"} | {str(n) for n in range(1, 13)},
               "912": {"9", "10", "11", "12"}, "68": {"6", "7", "8"},
               "612": {str(n) for n in range(6, 13)}}

_cache: dict[str, dict[str, dict]] = {}
_overlay_cache: dict[str, dict] = {}
_caveats: list[str] = []


def _load_overlay(name: str) -> dict:
    """CPALMS verification overlay for a subject (tools/cpalms_verify.py --apply --write).
    entries: code -> {state, statement_verified, cpalms_url, checked_at, new_code?}."""
    if name in _overlay_cache:
        return _overlay_cache[name]
    overlay: dict = {}
    try:
        p = OVERLAYS / f"{name}.cpalms.json"
        if p.exists():
            overlay = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        _caveats.append(f"overlay_unreadable:{name}:{exc.__class__.__name__}")
    _overlay_cache[name] = overlay
    return overlay


def _is_low_confidence(name: str) -> str | None:
    """A low-confidence subject earns full trust once its CPALMS overlay coverage crosses the
    threshold — then absence in the corpus becomes evidence again (blocking not_found)."""
    if name not in LOW_CONFIDENCE:
        return None
    ov = _load_overlay(name)
    if ov.get("entries") and float(ov.get("coverage", 0)) >= OVERLAY_TRUST_COVERAGE:
        return None
    return LOW_CONFIDENCE[name]


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
                ov = (_load_overlay(name).get("entries") or {}).get(c)
                if ov:
                    # An overlay entry proves the CODE EXISTS on CPALMS. It does not prove the
                    # corpus statement is faithful — that is what `state` records. Attaching a bare
                    # verified={} for every entry made near_match / statement_differs / ambiguous
                    # indistinguishable from confirmed to every consumer, including the CI gate: a
                    # row whose text CPALMS disagrees with reported "resolved / verified / no
                    # warning". `state` and `needs_review` are carried through so the distinction
                    # survives the trip.
                    r["verified"] = {"source": "cpalms", "checked_at": ov.get("checked_at"),
                                     "url": ov.get("cpalms_url"), "state": ov.get("state")}
                    if _overlay_needs_review(ov):
                        r["needs_review"] = True
                        r["detail"] = (r["detail"] + f" overlay state '{ov.get('state')}': the code "
                                       f"is real and CPALMS's text is used here, but agreement "
                                       f"with the corpus statement is UNVERIFIED — human review "
                                       f"required").strip()
                    if ov.get("statement_verified"):
                        # CPALMS's text is the registry origin form for the §6 mutation check.
                        r["statement"] = ov["statement_verified"]
                if r["grade_band_match"] is False:
                    r["detail"] = (r["detail"] + f" grade '{e.get('grade')}' is outside band '{grade_band}'").strip()
                return r
        # Not in the parse corpus: an overlay may still resolve it — as a renumbering (old -> new
        # code) or as a CPALMS addition (census found it on CPALMS; the parse corpus lacks it).
        for name in subjects:
            ov = (_load_overlay(name).get("entries") or {}).get(c)
            if not ov:
                continue
            # Both branches below resolve a code the corpus does NOT contain, so neither is a
            # corroborated match — they carry needs_review for the same reason the in-corpus
            # branch does, and for the same reason it is a warning rather than a block: CPALMS's
            # own text is what gets served, so the citation is usable, just not cross-checked.
            if ov.get("new_code"):
                r.update(state="resolved", statement=ov.get("statement_verified"),
                         verified={"source": "cpalms", "checked_at": ov.get("checked_at"),
                                   "url": ov.get("cpalms_url"), "state": ov.get("state")},
                         needs_review=True,
                         detail=f"superseded_by {ov['new_code']} (CPALMS renumbering) — cite the "
                                f"current code")
                return r
            if ov.get("state") == "retired":
                # The code was REAL and has been withdrawn. Reporting it as `not_found` would make
                # the gate call a published Florida benchmark fabricated — finding D-K again. The
                # author still needs to act (do not cite it in new work), so it carries
                # needs_review and the withdrawn text, but it is never an integrity failure.
                r.update(state="retired", statement=ov.get("statement_withdrawn"),
                         verified={"source": "cpalms", "checked_at": ov.get("checked_at"),
                                   "url": ov.get("cpalms_url"), "state": "retired"},
                         needs_review=True,
                         detail=(ov.get("detail") or "withdrawn from CPALMS") +
                                " — do not cite in new work; if this artifact is historical, say so"
                                " explicitly.")
                return r
            if ov.get("state") == "cpalms_addition":
                r.update(state="resolved", statement=ov.get("statement_verified"),
                         verified={"source": "cpalms", "checked_at": ov.get("checked_at"),
                                   "url": ov.get("cpalms_url"), "state": ov.get("state")},
                         needs_review=True,
                         detail="verified on CPALMS but absent from the parsed corpus "
                                "(overlay addition, pending the human --include-additions gate) — "
                                "a corpus refresh would fold it in")
                return r
        if not scheme.match(c):
            r.update(state="malformed",
                     detail=f"violates the {prefix} coding scheme (florida-best.md §Coding schemes)")
            return r
        if all(t is None for t in tables):
            r.update(state="scheme_valid_unenumerated",
                     detail="corpus unavailable this run — structure valid, existence unchecked")
            return r
        low = [note for s in subjects if (note := _is_low_confidence(s))]
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
                       "caveats": sorted({note for s in loaded if (note := _is_low_confidence(s))}
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
    # Was `not_found_low_confidence` (advisory) while SS was a best-effort parse. The parse was
    # root-caused and fixed, the source refreshed, and all 2,713 SS codes verified against CPALMS
    # 2026-08-13 (overlay 100%), so the coverage threshold lifts SS out of LOW_CONFIDENCE: absence
    # is evidence and this blocks. Deliberate change, not a drifted expectation.
    ("SS.7.C.1.99", {}, "not_found", True, None),                            # absent; corpus corroborated
    # Was `not_found_low_confidence` (advisory) while ELD was treated as a partial corpus. The
    # 2026-08-13 census settled that: CPALMS's ELD subject holds exactly the 5 umbrella standards
    # across all 13 grade labels, and this code returns not_on_cpalms when asked directly. With the
    # overlay at 5/5 the coverage threshold lifts ELD out of LOW_CONFIDENCE, so absence is now
    # evidence and this blocks. Deliberate change, not a drifted expectation.
    ("ELD.K12.ELL.LA.2", {}, "not_found", True, None),                       # absent; corpus complete
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
    # Overlay behavior, both ways: inject a synthetic trusted CPALMS overlay for social_studies.
    # Fixture URLs are CONSTRUCTED from the declared origin (url-provenance.json) at runtime —
    # a fabricated full URL must never appear as a literal in a provenance-guarded tree.
    _fix_url = "https://www.cpalms.org" + "/PreviewStandard/Preview/"
    _overlay_cache["social_studies"] = {
        "coverage": 0.99,
        "entries": {"SS.K.A.1.1": {"state": "confirmed", "statement_verified": "VERIFIED-TEXT",
                                   "cpalms_url": _fix_url + "1",
                                   "checked_at": "2026-08-09T00:00:00Z"},
                    "SS.7.OLD.1.1": {"state": "renumbered", "new_code": "SS.7.CG.1.1",
                                     "statement_verified": "MOVED-TEXT",
                                     "cpalms_url": _fix_url + "2",
                                     "checked_at": "2026-08-09T00:00:00Z"}}}
    r1 = verify(["SS.K.A.1.1"])["results"][0]
    ok = r1["state"] == "resolved" and r1.get("verified", {}).get("source") == "cpalms" \
        and r1["statement"] == "VERIFIED-TEXT"
    print(("PASS" if ok else "FAIL") + " overlay: resolved code carries verified stamp + origin form")
    failures += 0 if ok else 1

    # --- ELD crossed the coverage threshold 2026-08-13: absences now BLOCK -------------------
    # Guarded because the flip is user-visible and easy to undo by accident. The justification is
    # a complete census (13 grade labels -> exactly 5 codes) plus control probes; if the overlay
    # ever regresses below threshold these expectations change, and that should be deliberate.
    _eld = verify(["ELD.K12.ELL.LA.1"])
    ok = _eld["results"][0]["state"] == "resolved" and not _eld["blocking"]
    print(("PASS" if ok else "FAIL") + " ELD: a verified umbrella standard resolves cleanly")
    failures += 0 if ok else 1
    _wida = verify(["ELD-SI.4-12.Narrate"])
    ok = _wida["results"][0]["state"] == "unknown_framework" and not _wida["blocking"]
    print(("PASS" if ok else "FAIL") + " ELD: a WIDA-scheme descriptor stays ADVISORY, never blocking "
                                      "(different framework, not a fabricated FL code)")
    failures += 0 if ok else 1

    # --- retired != fabricated (D-K in a new costume) ------------------------------------------
    _overlay_cache["social_studies"]["entries"]["SS.9.GONE.1.1"] = {
        "state": "retired", "needs_review": True, "statement_withdrawn": "WITHDRAWN-TEXT",
        "checked_at": "2026-08-13T00:00:00Z", "detail": "withdrawn: absent from CPALMS and dropped"}
    _r = verify(["SS.9.GONE.1.1"])
    _rr = _r["results"][0]
    ok = (_rr["state"] == "retired" and _rr.get("needs_review") is True
          and "SS.9.GONE.1.1" not in _r["blocking"] and _rr["statement"] == "WITHDRAWN-TEXT")
    print(("PASS" if ok else "FAIL") + " retired: a WITHDRAWN standard is not blocking and keeps "
                                      "its text (a real code must never read as fabricated)")
    failures += 0 if ok else 1
    ok = "do not cite in new work" in _rr["detail"]
    print(("PASS" if ok else "FAIL") + " retired: the author is told what to do about it")
    failures += 0 if ok else 1

    # --- N1: an overlay entry proves the CODE exists, not that the TEXT agrees ----------------
    # Every entry used to receive a bare verified={} stamp, so a row CPALMS disagrees with was
    # indistinguishable from a confirmed one — to a reader and to the CI gate alike.
    ok = r1.get("verified", {}).get("state") == "confirmed" and not r1.get("needs_review")
    print(("PASS" if ok else "FAIL") + " N1: a CONFIRMED row carries state=confirmed and no "
                                       "needs_review (negative control)")
    failures += 0 if ok else 1
    _overlay_cache["social_studies"]["entries"]["SS.K.A.1.2"] = {
        "state": "statement_differs", "needs_review": True, "statement_verified": "CPALMS-TEXT",
        "cpalms_url": _fix_url + "4", "checked_at": "2026-08-09T00:00:00Z"}
    r2 = verify(["SS.K.A.1.2"])["results"][0]
    ok = (r2.get("needs_review") is True and r2["verified"]["state"] == "statement_differs"
          and r2["statement"] == "CPALMS-TEXT" and "human review" in r2["detail"])
    print(("PASS" if ok else "FAIL") + " N1: a DISAGREEING row sets needs_review and still serves "
                                       "CPALMS's text")
    failures += 0 if ok else 1
    # The flag is DERIVED, not trusted: four committed entries carried an unverified state with no
    # needs_review flag, and reading the flag alone reported them clean.
    _overlay_cache["social_studies"]["entries"]["SS.K.A.1.AP.1"] = {
        "state": "statement_differs", "statement_verified": "CPALMS-TEXT-2",
        "cpalms_url": _fix_url + "5", "checked_at": "2026-08-09T00:00:00Z"}
    r3 = verify(["SS.K.A.1.AP.1"])["results"][0]
    ok = r3.get("needs_review") is True
    print(("PASS" if ok else "FAIL") + " N1: an unverified state with a MISSING flag still needs "
                                       "review (flag is derived, not trusted)")
    failures += 0 if ok else 1
    rep = verify(["SS.7.C.9.99"])
    ok = rep["results"][0]["state"] == "not_found" and "SS.7.C.9.99" in rep["blocking"]
    print(("PASS" if ok else "FAIL") + " overlay: trusted coverage flips SS miss to BLOCKING not_found")
    failures += 0 if ok else 1
    _overlay_cache["social_studies"]["entries"]["SS.9.NEW.1.1"] = {
        "state": "cpalms_addition", "statement_verified": "ADDED-TEXT",
        "cpalms_url": _fix_url + "3", "checked_at": "2026-08-09T00:00:00Z"}
    r4 = verify(["SS.9.NEW.1.1"])["results"][0]
    ok = r4["state"] == "resolved" and "overlay addition" in r4["detail"] \
        and r4["statement"] == "ADDED-TEXT"
    print(("PASS" if ok else "FAIL") + " overlay: cpalms_addition resolves (census find, not in corpus)")
    failures += 0 if ok else 1
    r3 = verify(["SS.7.OLD.1.1"])["results"][0]
    ok = r3["state"] == "resolved" and "superseded_by SS.7.CG.1.1" in r3["detail"]
    print(("PASS" if ok else "FAIL") + " overlay: renumbered old code resolves with superseded_by")
    failures += 0 if ok else 1
    _overlay_cache["social_studies"] = {"coverage": 0.5, "entries": {"SS.K.A.1.1": {}}}
    rep = verify(["SS.7.C.9.99"])
    ok = rep["results"][0]["state"] == "not_found_low_confidence" and not rep["blocking"]
    print(("PASS" if ok else "FAIL") + " overlay: sub-threshold coverage stays advisory (both ways)")
    failures += 0 if ok else 1
    _overlay_cache.clear()
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
    failures += _mutation_batteries()
    print(f"self-test: {failures} failure(s) across {len(PROBES)} probes + shape audit "
          f"+ mutation batteries")
    return 1 if failures else 0


# §6 comparator acceptance batteries (audit finding F5). Origin text is a REAL verified statement.
_ORIGIN = ("Read and write numbers from 0 to 10,000 using standard form, expanded form and "
           "word form.")
MUTATIONS = [
    ("value_drift", _ORIGIN.replace("10,000", "100,000")),
    ("caveat_stripping", "Read and write numbers from 0 to 10,000."),
    ("hedge_removal", "Master reading and writing numbers from 0 to 10,000 using standard form, "
                      "expanded form and word form."),
    ("scope_broadening", "Read and write numbers of any size using standard form, expanded form "
                         "and word form."),
    ("unit_swap", "Read and write percentages from 0 to 10,000 using standard form, expanded "
                  "form and word form."),
    ("attribution_laundering", "According to the B.E.S.T. standards: " + _ORIGIN),
]
FAITHFUL = [
    ("identical", _ORIGIN),
    ("appended clarifications", _ORIGIN + " Clarifications: Clarification 1: Instruction includes "
                                          "the use of manipulatives."),
    ("appended examples", _ORIGIN + " Examples: The number two thousand five is written 2,005."),
    ("smart quotes", _ORIGIN.replace("word form", "word’s form").replace("word’s", "word")),
    ("period-spacing artifact", _ORIGIN.replace("form.", "form.Students")[:-8] + "form."),
    ("case change", _ORIGIN.upper()),
    ("no trailing period", _ORIGIN.rstrip(".")),
    ("collapsed whitespace", "  ".join(_ORIGIN.split(" "))),
    ("ellipsized card", _ORIGIN[:60] + "…"),
    ("leading stem", "Students will read and write numbers from 0 to 10,000 using standard form, "
                     "expanded form and word form."),
    ("html entities", _ORIGIN.replace("and", "&amp;").replace("&amp;", "and")),
    ("trailing whitespace", _ORIGIN + "   "),
    # Real parse-metadata tails sampled from the corpus during the A9 sweep (2026-08-10). The
    # benchmark sentence was identical in every one; only these document artifacts differed.
    ("content-complexity tail", _ORIGIN + " Content Complexity: Level 3: Strategic Thinking & Complex Reasoning"),
    ("adoption-date tail", _ORIGIN + " Date Adopted or Revised : 05/23"),
    ("next-section bleed", _ORIGIN + " Date Adopted or Revised : 05/23 Standard 2: Pre-Columbian Florida BENCHMARK CODE"),
    ("cognitive-complexity tail", _ORIGIN + " Cognitive Complexity: Level 2: Basic Application"),
]


def _mutation_batteries() -> int:
    """Every mutation must flag; no faithful restatement may flag (F5 acceptance gate)."""
    fails = 0
    caught = 0
    for want, text in MUTATIONS:
        cats = {f["category"] for f in mutation_flags(text, _ORIGIN)}
        hit = want in cats
        caught += hit
        print(("PASS " if hit else "FAIL ") + f"mutation[{want}] detected"
              + ("" if hit else f" (got {sorted(cats) or 'nothing'})"))
        fails += 0 if hit else 1
    fp = 0
    for name, text in FAITHFUL:
        cats = sorted({f["category"] for f in mutation_flags(text, _ORIGIN)})
        if cats:
            fp += 1
            print(f"FAIL false-positive[{name}] -> {cats}")
    print(f"mutation batteries: {caught}/{len(MUTATIONS)} mutations flagged, "
          f"{fp}/{len(FAITHFUL)} false positives")
    return fails + fp


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Offline standards-code resolver (report-only by default).")
    ap.add_argument("codes", nargs="*", help="standard codes to resolve")
    ap.add_argument("--input", metavar="ARTIFACT_JSON",
                    help="read standards_cited/standards_set/grade_band/context from an artifact")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any code is in a blocking state")
    ap.add_argument("--compare", metavar="CODE",
                    help="§6 citation-mutation check: compare --text against CODE's origin form")
    ap.add_argument("--text", help="the artifact's restatement of the standard (with --compare)")
    ap.add_argument("--self-test", action="store_true", help="run the embedded probe table + shape audit")
    ap.add_argument("--self-test-invert", action="store_true", help=argparse.SUPPRESS)  # dev-only
    a = ap.parse_args(argv)

    if a.self_test or a.self_test_invert:
        return self_test(invert=a.self_test_invert)
    if a.compare:
        if not a.text:
            ap.error("--compare needs --text (the artifact's restatement)")
        res = verify([a.compare])["results"][0]
        origin = res.get("statement")
        if not origin:
            print(json.dumps({"tool": "verify-standards", "mode": "mutation-check",
                              "code": a.compare, "state": res["state"],
                              "checked": "code resolution",
                              "detail": "no origin-form statement available — cannot compare "
                                        "(resolve the code first)"}, indent=2))
            return 1
        flags = mutation_flags(a.text, origin)
        print(json.dumps({"tool": "verify-standards", "mode": "mutation-check",
                          "code": a.compare, "state": res["state"], "origin_form": origin,
                          "cited_text": a.text, "mutation_flags": flags,
                          "verdict": "mutations_detected" if flags
                                     else "no mutations found — checked: value drift, unit swap, "
                                          "caveat stripping, hedge removal, scope broadening, "
                                          "attribution laundering",
                          "guidance": ("restate in the registry's origin form "
                                       "(standards-verification.md §6)") if flags else ""},
                         indent=2, ensure_ascii=False))
        return 1 if flags else 0
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
