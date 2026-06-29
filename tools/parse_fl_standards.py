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

import html
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
    # FL's Social Studies .doc is an HTML-exported Word file — decode then strip tags.
    raw = p.read_bytes().decode("latin-1", "ignore")
    raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[ \t]+", " ", raw)


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
        out.append({"code": code, "grade": g, "strand": strand, "type": classify(code),
                    "statement": (stmt or "").strip()[:300]})

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


def parse_doc(text: str, code_re: str):
    """Best-effort for legacy binary .doc: codes + cleaned trailing text."""
    hits = list(re.finditer(rf"({code_re})", text))
    out, seen = [], set()
    for k, mm in enumerate(hits):
        code = mm.group(1)
        if code in seen:
            continue
        seg = text[mm.end(): hits[k + 1].start() if k + 1 < len(hits) else mm.end() + 240]
        seg = re.sub(r"\s+", " ", re.sub(r"[^\x20-\x7e]", " ", seg)).strip(" :.-")
        seg = re.split(r"Related Access Point", seg)[0].strip(" :.-")
        seen.add(code)
        g, strand = info(code)
        out.append({"code": code, "grade": g, "strand": strand, "type": classify(code), "statement": seg[:200]})
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
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
                  open(OUT / f"{subj}.json", "w"), indent=2)
        t = Counter(e["type"] for e in entries)
        index["subjects"][subj] = {"file": f"data/{subj}.json", "format": fmt, "reader": reader,
                                   "count": len(entries), "benchmarks": t["benchmark"],
                                   "access_points": t["access_point"], "practices": t["practice"]}
        print(f"  {subj:16} {len(entries):5} codes  (benchmark {t['benchmark']}, AP {t['access_point']}, "
              f"practice {t['practice']}, {fmt} via {reader})")
    index["total"] = sum(s["count"] for s in index["subjects"].values())
    json.dump(index, open(OUT / "index.json", "w"), indent=2)
    print(f"\nwrote {len(index['subjects'])} subjects + index.json ({index['total']} codes) to {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
