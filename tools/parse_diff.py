#!/usr/bin/env python3
"""Prove a corpus regeneration changed STRUCTURE, not CONTENT — stdlib-only, offline.

The FL corpora are parse output. Regenerating them from the committed source documents is the
sanctioned way to fix a parse defect (the corpus is never edited by hand, and verification never
writes into it). But a regeneration can silently do far more than intended: a changed segmentation
rule can drop or invent standards, and a changed extraction rule can put text into a statement that
was never in the document.

This tool exists so that cannot happen unnoticed. It enforces two ABORT conditions:

  1. The code set must be identical, per subject. A code appearing or disappearing means the
     segmentation moved — that is a corpus rewrite, not a repair, and needs its own review.
  2. Every new statement must be an ASCII-fold PREFIX of the old one. That is the mechanical proof
     that the regeneration only REMOVED trailing document furniture and RESTORED characters. If a
     new statement is not a prefix, text was invented rather than trimmed.

Condition 2 has one honest gap: the fold keeps letters, so restoring a destroyed *letter* reads as
added text. `SS.912.AA.2.16` is the corpus's only instance — the old parser turned `Adams-Onís` into
`Adams-On s`, so the restored `i` breaks prefix containment even though nothing was invented.
Rather than loosen the rule, a non-prefix code is ESCALATED to a stricter test: the new statement
must appear VERBATIM in the subject's committed source document. The document is the authority on
what the text is; passing that test is a stronger proof than prefix containment, not a weaker one.
A code that fails it, or whose source text cannot be read, still aborts — the escalation fails closed.

Everything else — furniture removed, characters restored, fields newly captured — is reported for
human review rather than asserted.

Usage:
  python3 tools/parse_diff.py --old shared/standards/resources/florida/data --new /tmp/new
  python3 tools/parse_diff.py --old <dir> --new <dir> --json report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

SUBJECTS = ("math", "ela", "science", "social_studies", "computer_science", "eld")

# Document furniture that must never appear inside a benchmark statement. Measured before the fix:
# 3,320 of 6,583 statements (50.4%) contained at least one of these.
#
# The vocabulary is the documents' own — every label-shaped token in all six sources was enumerated
# and each one checked for prose use — rather than a list of what the parser happens to remove. That
# distinction matters: a furniture count built from the parser's own patterns would report zero by
# construction. Real NGSSS body text that is merely label-shaped ("The Practice of Science A:",
# "Law of Conservation of Energy:") is deliberately excluded.
FURNITURE = re.compile(
    r"\bStandard\s+\d+\s*:|\bBENCHMARK CODE\b|\bACCESS POINT CODE\b|\bClarifications?\s*:"
    r"|\bRemarks\s*(?:/\s*Examples)?\s*:|\bDate Adopted|\b(?:Content|Cognitive)\s+Complexity"
    r"|\bRelated Access Point|(?-i:\b(?<![Ff]or )Examples?\s*:)|\bStrand\s*:|\bGrade\s*:"
    r"|\bBody\s+Of\s+Knowledge\s*:"
    r"|\bBig\s+Idea\s+\d+\s*:|\bExpectation\s+\d+\s*:|This report was generated|cpalms\.org", re.I)
# Case-sensitivity is load-bearing in the "Examples" alternative, exactly as in the parser: the
# capitalised form is a table label (552 occurrences), the lower-case form is prose (6, all "for
# example:"). Counting the prose form as furniture would report 4 phantom defects in science and
# push someone to "fix" statements that are already correct.


def ascii_fold(s: str) -> str:
    """Compare only the letters and digits. Strips punctuation, spacing and diacritics so that
    restoring an apostrophe or removing a trailing header does not read as a content change."""
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _load(path: Path) -> dict[str, dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {e["code"]: e for e in doc["standards"]}


_SRC_CACHE: dict[str, str | None] = {}


def source_text(subject: str) -> str | None:
    """The subject's committed source document, read exactly the way the parser reads it, flattened
    to one whitespace-normalized line so a statement can be searched for verbatim.

    Returns None if the document or the parser cannot be loaded — callers must treat that as a
    failure, never as a pass."""
    if subject in _SRC_CACHE:
        return _SRC_CACHE[subject]
    text = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import parse_fl_standards as P
        rel, _code_re, fmt = P.SUBJECTS[subject]
        path = P.FL / rel
        if fmt == "doc":
            raw = P.doc_text(path)
        elif P._PIPE is not None:
            raw = P.docintel_text(path)[0]
        else:
            raw = P.docx_text(path)
        text = re.sub(r"\s+", " ", raw)
    except Exception as e:                                   # noqa: BLE001 — reported, fails closed
        print(f"  [warn] {subject}: source document unreadable for escalation "
              f"({e.__class__.__name__}: {e})", file=sys.stderr)
    _SRC_CACHE[subject] = text
    return text


def in_source(subject: str, statement: str) -> bool:
    """Is this exact statement present in the source document? The escalation for a non-prefix
    code: proof the text was read out of the document rather than synthesized by the parser."""
    src = source_text(subject)
    stmt = re.sub(r"\s+", " ", statement or "").strip()
    return bool(src and stmt and stmt in src)


def compare(old_dir: Path, new_dir: Path, expect_added=None, expect_removed=None) -> tuple[int, dict]:
    report: dict = {"subjects": {}, "aborts": [], "totals": {}}
    t_old_furn = t_new_furn = t_changed = t_codes = t_restored = 0
    max_old = max_new = 0

    for subj in SUBJECTS:
        op, np_ = old_dir / f"{subj}.json", new_dir / f"{subj}.json"
        if not (op.exists() and np_.exists()):
            report["aborts"].append(f"{subj}: missing corpus file ({op.exists()=}, {np_.exists()=})")
            continue
        old, new = _load(op), _load(np_)
        s: dict = {"old_codes": len(old), "new_codes": len(new)}

        # ---- ABORT 1: the code set must not move -------------------------------------------
        added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
        s["added"], s["removed"] = added[:20], removed[:20]
        s["added_count"], s["removed_count"] = len(added), len(removed)
        if added or removed:
            # A SOURCE REFRESH legitimately moves the code set: the state retires or adds standards
            # and publishes a new document. That is not the defect this abort guards against (a
            # segmentation change silently dropping standards), but the two are indistinguishable
            # from the diff alone — so the operator must say IN ADVANCE exactly which codes may
            # move, and the sets must match exactly. An unexpected code moving still aborts, and so
            # does an expected one that did NOT move, which catches a stale expectation.
            exp_add = set(expect_added or []) if expect_added is not None else None
            exp_rem = set(expect_removed or []) if expect_removed is not None else None
            declared = exp_add is not None or exp_rem is not None
            if declared and set(added) == (exp_add or set()) and set(removed) == (exp_rem or set()):
                s["code_change_declared"] = True
                report.setdefault("declared_changes", []).append(
                    f"{subj}: {len(added)} added / {len(removed)} removed — matches the declared "
                    f"set exactly (source refresh).")
            else:
                extra = f" Declared but did not move: {sorted((exp_rem or set()) - set(removed))[:5]}" \
                    if declared else ""
                report["aborts"].append(
                    f"{subj}: CODE SET CHANGED — {len(added)} added, {len(removed)} removed"
                    + (". Segmentation moved; this is a corpus rewrite, not a repair."
                       if not declared else
                       f", which does NOT match the declared set "
                       f"(declared +{len(exp_add or [])}/-{len(exp_rem or [])}).{extra}")
                    + f" undeclared added={sorted(set(added) - (exp_add or set()))[:5]} "
                      f"undeclared removed={sorted(set(removed) - (exp_rem or set()))[:5]}")

        # ---- ABORT 2: new statement must be a prefix of old -------------------------------
        not_prefix, changed, of, nf = [], 0, 0, 0
        for code in sorted(set(old) & set(new)):
            o_stmt = old[code].get("statement") or ""
            n_stmt = new[code].get("statement") or ""
            of += bool(FURNITURE.search(o_stmt))
            nf += bool(FURNITURE.search(n_stmt))
            max_old_l, max_new_l = len(o_stmt), len(n_stmt)
            if max_old_l > max_old:
                max_old = max_old_l
            if max_new_l > max_new:
                max_new = max_new_l
            o, n = ascii_fold(o_stmt), ascii_fold(n_stmt)
            if o != n:
                changed += 1
                if not o.startswith(n):
                    not_prefix.append(code)
        # ---- ESCALATION: a non-prefix code must be provable from the source document ---------
        restored, invented = [], []
        for code in not_prefix:
            (restored if in_source(subj, new[code].get("statement") or "") else invented).append(code)

        s.update(statements_changed=changed, furniture_old=of, furniture_new=nf,
                 not_prefix_count=len(not_prefix), not_prefix=not_prefix[:20],
                 restored_not_prefix=restored[:20], restored_not_prefix_count=len(restored),
                 invented=invented[:20], invented_count=len(invented),
                 fields_captured={k: sum(1 for e in new.values() if e.get(k))
                                  for k in ("clarifications", "remarks", "complexity",
                                            "date_adopted", "related_access_points", "examples")})
        if invented:
            report["aborts"].append(
                f"{subj}: {len(invented)} statement(s) are NOT a prefix of the original AND do not "
                f"appear in the source document — text was invented, not trimmed. e.g. {invented[:5]}")
        t_restored += len(restored)
        report["subjects"][subj] = s
        t_old_furn += of
        t_new_furn += nf
        t_changed += changed
        t_codes += len(new)

    report["totals"] = {"codes": t_codes, "statements_changed": t_changed,
                        "furniture_old": t_old_furn, "furniture_new": t_new_furn,
                        "max_statement_old": max_old, "max_statement_new": max_new,
                        "restored_not_prefix": t_restored}
    return (1 if report["aborts"] else 0), report


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--json", help="also write the full report here")
    ap.add_argument("--expect-removed", nargs="*", metavar="CODE",
                    help="codes that a SOURCE REFRESH is expected to remove. The removed set must "
                         "match this EXACTLY — an undeclared removal still aborts, and a declared "
                         "code that did not move also aborts (a stale expectation).")
    ap.add_argument("--expect-added", nargs="*", metavar="CODE",
                    help="codes a source refresh is expected to add (same exact-match rule)")
    a = ap.parse_args(argv)

    rc, rep = compare(Path(a.old), Path(a.new), a.expect_added, a.expect_removed)
    t = rep["totals"]
    print(f"{'subject':18} {'codes':>7} {'+/-':>7} {'changed':>8} {'furn old→new':>14} "
          f"{'!prefix':>8} {'restored':>9} {'invented':>9}")
    for subj, s in rep["subjects"].items():
        print(f"{subj:18} {s['new_codes']:7} "
              f"{('+%d/-%d' % (s['added_count'], s['removed_count'])):>7} "
              f"{s['statements_changed']:8} "
              f"{(str(s['furniture_old']) + '→' + str(s['furniture_new'])):>14} "
              f"{s['not_prefix_count']:8} {s['restored_not_prefix_count']:9} {s['invented_count']:9}")
    print(f"\ntotals: {t['codes']} codes · {t['statements_changed']} statements changed · "
          f"furniture {t['furniture_old']} → {t['furniture_new']} · "
          f"longest statement {t['max_statement_old']} → {t['max_statement_new']}")
    for subj, s in rep["subjects"].items():
        for code in s["restored_not_prefix"]:
            # Deliberately does NOT say WHY the text changed. The escalation proves only that the
            # new statement is in the source document; whether that is a restored character or a
            # revision in a refreshed document is not something this tool can know, and asserting
            # one of them would be the tool inventing an explanation for a human to trust.
            print(f"  {subj}: {code} — not a prefix, but present VERBATIM in the source document")
    for subj, s in rep["subjects"].items():
        cap = {k: v for k, v in s["fields_captured"].items() if v}
        if cap:
            print(f"  {subj:18} fields captured: {cap}")
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    for m in rep.get("declared_changes", []):
        print(f"\n  [declared] {m}")
    if rep["aborts"]:
        print("\nABORT — regeneration must not be applied:")
        for m in rep["aborts"]:
            print("  •", m)
        return 1
    moved = sum(s["added_count"] + s["removed_count"] for s in rep["subjects"].values())
    print(f"\nOK — every statement is either a prefix of the original or ({t['restored_not_prefix']}) "
          f"proven verbatim in the source document"
          + (f"; {moved} code(s) moved, each one declared in advance." if moved else
             "; no code was added or removed.")
          + "\nWhat this does NOT establish: WHY a statement changed. A trimmed tail, a restored "
            "character and a revision in a refreshed source document all look alike here — read the "
            "per-code list above before treating any of them as equivalent.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
