#!/usr/bin/env python3
"""Parse Florida's stored standards documents into structured, queryable JSON.

Reads the B.E.S.T./NGSSS standards documents under
shared/standards/resources/florida/ and emits one JSON per subject in
.../florida/data/, plus an index. Each entry: {code, grade, strand, type, statement}
with type ∈ {benchmark, access_point, practice}.

.docx sources parse cleanly (line-structured). The Social Studies source is a legacy
binary .doc, so it is parsed best-effort (codes + nearby text); verify SS on CPALMS.

Reproducible; stdlib only. Usage: python3 tools/parse_fl_standards.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rebuild_index() -> None:
    """Rebuild the offline index after regenerating a source corpus, so the gitignored
    offline.db + its committed manifest never drift from the JSON we just wrote. Non-fatal:
    a build hiccup warns but never fails the producer (skip entirely with --no-index)."""
    try:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "offline_index.py"), "--build"],
                           capture_output=True, text=True, timeout=300)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            print("  [warn] offline index rebuild returned non-zero — run "
                  "`python3 tools/offline_index.py --build` manually", file=sys.stderr)
    except Exception as e:
        print(f"  [warn] offline index not rebuilt ({e.__class__.__name__}); run "
              "`python3 tools/offline_index.py --build` and commit the manifest", file=sys.stderr)
FL = ROOT / "shared" / "standards" / "resources" / "florida"
OUT = FL / "data"

# Read documents through the governed docintel engine when available (structure + tables +
# provenance, fully offline). Falls back to the stdlib docx reader if docintel can't load.
sys.path.insert(0, str(ROOT / "shared"))
try:
    import docintel
    _PIPE = docintel.Pipeline()
except Exception:
    docintel, _PIPE = None, None

# subject -> (path under florida/, code regex, format)
SUBJECTS = {
    "math":             ("standards/Mathematics(B.E.S.T.)_StandardsandAccessPoints.doc.docx", r"MA\.[A-Z0-9]{1,4}\.[A-Z]{1,4}\.[\w.]+", "docx"),
    "ela":              ("standards/EnglishLanguageArts(B.E.S.T.)_StandardsandAccessPoints.doc.docx", r"ELA\.[A-Z0-9]{1,4}\.[A-Z]{1,3}\.[\w.]+", "docx"),
    "science":          ("standards/Science_StandardsandAccessPoints.doc.docx", r"SC\.[A-Z0-9]{1,4}\.[A-Z]{1,3}\.[\w.]+", "docx"),
    "computer_science": ("standards/ComputerScience_StandardsReportWithoutAccessPoints.doc.docx", r"SC\.[A-Z0-9]{1,4}\.[A-Z][\w.\-]+", "docx"),
    "eld":              ("english-learners/EnglishLanguageDevelopment_StandardsReportWithoutAccessPoints.doc.docx", r"ELD\.[A-Z0-9]{1,4}\.[\w.]+", "docx"),
    "social_studies":   ("standards/SocialStudies_StandardsandAccessPoints_WR.doc", r"SS\.[A-Z0-9]{1,4}\.[A-Z]{1,3}\.[\w.]+", "doc"),
}
STOP = re.compile(r"(?i)^(clarification|example|benchmark clarification|connecting|purpose|in grade)")


def docx_text(p: Path) -> str:
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    return html.unescape(re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n")))


def doc_text(p: Path) -> str:
    """FL's Social Studies .doc is an HTML-exported Word file — decode, strip tags, keep characters.

    It is UTF-8 (`file` reports "HTML document, UTF-8 text"). Decoding it as latin-1 — the previous
    behaviour — mojibaked every multi-byte character, and the [^\\x20-\\x7e] -> " " rule that used to
    follow in parse_doc() then erased them. In this one document that destroyed 324 apostrophes,
    73 + 74 smart quotes and 6 dashes, with zero survivors: `Identify Florida's role` became
    `Identify Florida s role`. That is defect D-J, and it was a parser bug, not a source defect —
    the correct characters have been in the committed document all along.

    Characters are PRESERVED here rather than folded to ASCII. The corpus should be faithful to its
    source; folding for comparison is cpalms_verify._norm's job, and the CPALMS overlay likewise
    stores the curly form.
    """
    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8")          # sniff, never assume
    except UnicodeDecodeError:
        text = raw.decode("latin-1", "replace")
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", _strip_control(text))


def _strip_control(s: str) -> str:
    """Drop control characters; keep every printable character including non-ASCII typography."""
    return "".join(ch for ch in s if ch in "\n\t" or ch.isprintable())


# --- structured field extraction --------------------------------------------------------------
# The FL documents are tables with labelled columns. Emitting all of it as one `statement` put
# document furniture into 3,320 of 6,583 statements (50.4%) — Clarifications 1,414, Date Adopted
# 1,281, Complexity 498, "Standard N:" section headers 209, "BENCHMARK CODE" table headers 208,
# Remarks 109 — which forced every downstream comparator to tolerate a PREFIX rather than test
# equality. That tolerance became a 0.97 similarity band, and with it a 100% pass rate for changed
# numeric bounds and 93.9% for deleted negations. Extracting the fields removes the reason the
# tolerance existed.
FIELD_PATTERNS = [
    ("clarifications", r"\bClarifications?\s*:"),
    ("remarks", r"\bRemarks(?:\s*/\s*Examples)?\s*:"),
    ("complexity", r"\b(?:Content|Cognitive)\s+Complexity\s*:"),
    ("date_adopted", r"\bDate Adopted(?:\s+or\s+(?:Last\s+)?Revised)?\s*:"),
    ("related_access_points", r"\bRelated Access Point\(?s?\)?\s*:?"),
    # "Examples :" is a table column in the docx documents. CASE-SENSITIVE, and never after "for":
    # capitalised "Example(s):" is the label (552 occurrences) while the lowercase form is ordinary
    # prose (6 occurrences, every one of them "for example:"). Matching case-insensitively truncated
    # SC.912.N.1.1 at "Define a problem based on a specific body of knowledge, for" — 1,729
    # characters of a real benchmark discarded. The separation is exact and was measured across all
    # six documents; `(?-i:…)` is required because _FIELD_RE as a whole is compiled with re.I.
    ("examples", r"(?-i:\b(?<![Ff]or )Examples?\s*:)"),
]
_FIELD_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in FIELD_PATTERNS), re.I)
# Section and table furniture ENDS a record: it belongs to the document, never to a standard.
# The vocabulary here is the documents' own, enumerated by scanning every label-shaped token in all
# six sources rather than guessed: Strand 222, Grade 58, Body of Knowledge 39, Big Idea 92 (science),
# Expectation 6 (ELA). Each was checked for prose use and has none — the only "mid-sentence" hits are
# the "This report was generated by CPALMS" title line, itself furniture. Deliberately NOT listed:
# "The Practice of Science A:", "Law of Conservation of Energy:" and similar, which are real NGSSS
# body text that happens to be label-shaped.
#
# Case matters here. The table headers "BENCHMARK CODE BENCHMARK" are upper-case, but "benchmark" is
# also an ordinary English word used 204 times inside real statements and clarifications ("Use
# benchmark quantities to determine if a solution is reasonable", "Within this benchmark, the
# expectation is not to…"). Matched case-insensitively, those become truncation points. So the
# header alternatives are wrapped in `(?-i:…)`. "Body of Knowledge" is the opposite case — science
# writes it with a lower-case "of" (40 of 41) — so it stays case-insensitive, and its trailing colon
# keeps it off the prose phrase "a specific body of knowledge, for example".
_SECTION = re.compile(r"\b(?:Standard\s+\d+\s*:|(?-i:BENCHMARK CODE\b)|(?-i:ACCESS POINT CODE\b)"
                      r"|(?-i:\bBENCHMARK\b(?=\s|$))|Grade\s*:|Grade\s+\d+\s*:|Cluster\s+\d+\s*:"
                      r"|Strand\s*:|Body\s+Of\s+Knowledge\s*:|Big\s+Idea\s+\d+\s*:"
                      r"|Expectation\s+\d+\s*:|This report was generated)", re.I)


def _trim_edges(s: str) -> str:
    """Trim label and separator debris from a field's edges while KEEPING terminal sentence
    punctuation. A blanket .strip(" :.-") also ate the full stop that ends nearly every benchmark,
    which the source document does have — the docx path preserved it and only the Social Studies
    path did not, so the corpus disagreed with itself. Comparison is unaffected either way
    (cpalms_verify._norm ends in .rstrip(".")), so fidelity to the document decides it."""
    return s.strip().lstrip(":.-").rstrip(" :-").strip()


def split_fields(seg: str) -> dict:
    """One raw segment -> the benchmark sentence plus each labelled field beside it.

    Verified against the committed Social Studies document before being wired in: 2,713 rows
    (exactly the corpus count), furniture inside statements 1,813 -> 0, and the captured field
    counts (409 clarifications, 1,281 date_adopted) match the label counts in the document itself —
    an independent check that the split follows the document's real structure rather than a guess.
    """
    seg = re.sub(r"\s+", " ", seg or "").strip()
    cut = _SECTION.search(seg)
    if cut:
        seg = seg[:cut.start()].strip()
    marks = list(_FIELD_RE.finditer(seg))
    out = {"statement": _trim_edges(seg[:marks[0].start()] if marks else seg)}
    # A label repeated inside its own value belongs to that value, not to a new field. "Examples :
    # Example: One less than 40 is 39. Example: Ten more than 23 is 33." is one field with three
    # sentences; splitting on each inner "Example:" would keep only the last and silently drop the
    # rest. Consecutive marks of the same name are therefore absorbed. (A repeat that follows a
    # DIFFERENT label still starts a new field — and no document nests one label inside another:
    # "Example:" inside a Clarifications value occurs 0 times across all six sources.)
    for i, m in enumerate(marks):
        if i and m.lastgroup == marks[i - 1].lastgroup:
            continue
        j = i + 1
        while j < len(marks) and marks[j].lastgroup == m.lastgroup:
            j += 1
        end = marks[j].start() if j < len(marks) else len(seg)
        val = _trim_edges(seg[m.end():end])
        if val:
            # A label that reappears AFTER a different one is joined rather than overwritten, so no
            # document text is ever silently dropped by the splitter.
            out[m.lastgroup] = f"{out[m.lastgroup]} {val}" if out.get(m.lastgroup) else val
    return out


def docintel_text(p: Path):
    """Read a doc via the governed docintel engine: paragraphs (in reading order) + table cells
    as lines, so table-bound access points are captured. Returns (text, retrieval_state)."""
    doc = _PIPE.run(p.read_bytes(), str(p))
    lines: list[str] = []
    for page in doc.pages:
        by_id = {b.block_id: b for b in page.blocks}
        for bid in (page.reading_order or [b.block_id for b in page.blocks]):
            b = by_id.get(bid)
            if b is None:
                continue
            if b.type == "table" and b.table:
                for cell in sorted(b.table.cells, key=lambda c: (c.row, c.col)):
                    if cell.text:
                        lines.append(cell.text)
            elif b.text:
                lines.append(b.text)
    return "\n".join(lines), doc.diagnostics.get("retrieval_state")


def classify(code: str) -> str:
    if ".AP." in code or re.search(r"\.(In|Su|Pa)\.", code):
        return "access_point"
    if ".K12." in code:
        return "practice"
    return "benchmark"


def info(code: str):
    parts = code.split(".")
    return (parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else "")


def parse_docx(text: str, code_re: str):
    # Two layouts: the code alone on a line (statement follows), OR the code leading a line with its
    # statement inline (common in access-point table cells). Handle both so tables aren't lost.
    line_code = re.compile(rf"^\s*({code_re})\s*[​\s]*$")
    lead_code = re.compile(rf"^\s*({code_re})[​\s]+(\S.*)$")
    lines = text.split("\n")
    out, seen = [], set()

    def emit(code, stmt):
        if code in seen:
            return
        seen.add(code)
        g, strand = info(code)
        # Was: split on "Related Access Point" only — one field of six, so Clarifications,
        # Complexity and Date Adopted stayed inside the statement.
        row = {"code": code, "grade": g, "strand": strand, "type": classify(code)}
        row.update(split_fields(stmt))
        out.append(row)

    for i, ln in enumerate(lines):
        m = line_code.match(ln)
        if m:
            stmt = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                s = lines[j].strip()
                if not s:
                    continue
                if line_code.match(lines[j]) or lead_code.match(lines[j]) or STOP.match(s):
                    break
                stmt = s
                break
            emit(m.group(1).strip(), stmt)
            continue
        m2 = lead_code.match(ln)
        if m2 and not STOP.match(m2.group(2).strip()):
            emit(m2.group(1).strip(), m2.group(2))
    return out


def _sentence_trim(s: str, soft: int = 600) -> str:
    """Trim overlong best-effort segments at a sentence boundary, never mid-word."""
    if len(s) <= soft:
        return s
    cut = s.rfind(". ", 0, soft)
    return s[: cut + 1].strip() if cut > 40 else s[:soft].rsplit(" ", 1)[0].strip()


def parse_doc(text: str, code_re: str):
    """Best-effort for legacy binary .doc: codes + cleaned trailing text."""
    hits = list(re.finditer(rf"({code_re})", text))
    out, seen = [], set()
    for k, mm in enumerate(hits):
        code = mm.group(1)
        if code in seen:
            continue
        seg = text[mm.end(): hits[k + 1].start() if k + 1 < len(hits) else mm.end() + 700]
        # The [^\x20-\x7e] -> " " purge that used to run here is GONE: combined with the latin-1
        # decode it destroyed every apostrophe, smart quote and dash in the document (D-J).
        # Field splitting replaces the single "Related Access Point" split that used to follow.
        seen.add(code)
        g, strand = info(code)
        row = {"code": code, "grade": g, "strand": strand, "type": classify(code)}
        fields = split_fields(seg)
        fields["statement"] = _sentence_trim(fields["statement"])
        row.update(fields)
        out.append(row)
    return out


# Regression probes for split_fields. Every case here is a real string from the FL documents that
# an earlier draft of these patterns got wrong — the label/prose collisions are the whole risk of
# this splitter, and a truncation is invisible downstream because a truncated statement is still a
# valid PREFIX of the original, so tools/parse_diff.py cannot catch it.
SPLIT_PROBES = [
    # (segment, expected statement, expected field name or None)
    ("Define a problem based on a specific body of knowledge, for example: biology, chemistry",
     "Define a problem based on a specific body of knowledge, for example: biology, chemistry", None),
    ("Compare structures of plants and animals, for example: some animals have skeletons",
     "Compare structures of plants and animals, for example: some animals have skeletons", None),
    ("Justify thinking. For example: I think ___ because ___.",
     "Justify thinking. For example: I think ___ because ___.", None),
    ("Use benchmark quantities to determine if a solution is reasonable",
     "Use benchmark quantities to determine if a solution is reasonable", None),
    ("Within this benchmark, the expectation is not to write the numeral",
     "Within this benchmark, the expectation is not to write the numeral", None),
    ("Represent whole numbers from 10 to 20. Examples : The number 13 can be represented",
     "Represent whole numbers from 10 to 20.", "examples"),
    ("Identify Florida's role in World War II. BENCHMARK CODE BENCHMARK SS.4.A.8.1",
     "Identify Florida's role in World War II.", None),
    ("Discuss factors influencing attraction. Strand: SOCIOLOGY",
     "Discuss factors influencing attraction.", None),
    ("Recognize a calendar. Date Adopted or Revised : 05/23",
     "Recognize a calendar.", "date_adopted"),
    ("One less than 40. Examples : Example: One less is 39. Example: Ten more is 33",
     "One less than 40.", "examples"),          # inner repeats absorbed, not split
]


def self_test() -> int:
    """python3 tools/parse_fl_standards.py --self-test — offline, no documents needed."""
    bad = 0
    for seg, want_stmt, want_field in SPLIT_PROBES:
        got = split_fields(seg)
        if got["statement"] != want_stmt:
            bad += 1
            print(f"  FAIL statement\n    in   {seg!r}\n    want {want_stmt!r}\n    got  {got['statement']!r}")
        if want_field and want_field not in got:
            bad += 1
            print(f"  FAIL field {want_field!r} not captured from {seg!r} -> {got}")
        if not want_field and len(got) > 1:
            bad += 1
            print(f"  FAIL prose split into fields: {seg!r} -> {got}")
    # the inner-repeat probe must keep BOTH example sentences, not only the last
    ex = split_fields(SPLIT_PROBES[-1][0]).get("examples", "")
    if "One less is 39" not in ex or "Ten more is 33" not in ex:
        bad += 1
        print(f"  FAIL repeated label dropped text: {ex!r}")
    print(f"split_fields self-test: {len(SPLIT_PROBES)} probes, {bad} failure(s)")
    return 1 if bad else 0


def main(out_dir: Path | None = None) -> int:
    # A regeneration must be provable BEFORE it lands: write to a scratch dir, run
    # tools/parse_diff.py against the committed corpus, and only then write into the repo.
    OUT_ = out_dir or OUT
    OUT_.mkdir(parents=True, exist_ok=True)
    index = {"state": "Florida", "note": "Full enumerated FL standards extracted from the stored documents. "
             "Verify on CPALMS (https://www.cpalms.org/search/Standard). SS is best-effort from a binary .doc.",
             "subjects": {}}
    for subj, (rel, code_re, fmt) in SUBJECTS.items():
        src = FL / rel
        if not src.exists():
            print(f"  [skip] {subj}: missing {rel}")
            continue
        if fmt == "doc":
            text, reader, rstate = doc_text(src), "legacy-doc", None
        elif _PIPE is not None:
            text, rstate = docintel_text(src)
            reader = "docintel"
        else:
            text, reader, rstate = docx_text(src), "stdlib-fallback", None
        entries = parse_doc(text, code_re) if fmt == "doc" else parse_docx(text, code_re)
        # drop empty-statement noise from the best-effort .doc path
        if fmt == "doc":
            entries = [e for e in entries if len(e["statement"]) > 8]
        json.dump({"subject": subj, "source_file": Path(rel).name, "format": fmt,
                   "reader": reader, "retrieval_state": rstate,
                   "count": len(entries), "standards": entries},
                  open(OUT_ / f"{subj}.json", "w", encoding="utf-8"), indent=2)
        t = Counter(e["type"] for e in entries)
        index["subjects"][subj] = {"file": f"data/{subj}.json", "format": fmt, "reader": reader,
                                   "count": len(entries), "benchmarks": t["benchmark"],
                                   "access_points": t["access_point"], "practices": t["practice"]}
        print(f"  {subj:16} {len(entries):5} codes  (benchmark {t['benchmark']}, AP {t['access_point']}, "
              f"practice {t['practice']}, {fmt} via {reader})")
    index["total"] = sum(s["count"] for s in index["subjects"].values())
    json.dump(index, open(OUT_ / "index.json", "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {len(index['subjects'])} subjects + index.json ({index['total']} codes) to {OUT_}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse FL standards docs into data/*.json.")
    ap.add_argument("--no-index", action="store_true",
                    help="do not rebuild the offline index after writing (parse only)")
    ap.add_argument("--out", help="write corpora HERE instead of the repo — use this to stage a "
                                  "regeneration for tools/parse_diff.py before it lands")
    ap.add_argument("--self-test", action="store_true",
                    help="run the split_fields regression probes and exit (offline, no documents)")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    rc = main(Path(args.out) if args.out else None)
    if rc == 0 and not args.no_index and not args.out:
        rebuild_index()
    raise SystemExit(rc)
