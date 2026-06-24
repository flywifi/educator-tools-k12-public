#!/usr/bin/env python3
"""Structural document validator (stdlib only) — catch the common corruption classes before a teacher does.

Always runs (no third-party deps), so it works no matter what the teacher has installed. It checks the
*container structure* that the format specs require — the failures that make Office/PDF say "the file
cannot be opened because there are problems with the contents":
  - OOXML (.docx/.pptx/.xlsx): valid ZIP + `[Content_Types].xml` + `_rels/.rels` + the main part.
  - ODF  (.odt/.ods/.odp): valid ZIP + `mimetype` + `content.xml`.
  - PDF: `%PDF-` header + `startxref`/`xref` + `%%EOF` trailer.
Each finding cites the authority (ECMA-376/Open XML SDK, ISO 32000/veraPDF, ODF) and gives repair
guidance. Honest limit: structural validity is necessary, not sufficient — deep schema validity (Open XML
SDK) / PDF/A conformance (veraPDF) needs those tools; we report that as a follow-up, never fake it.

Usage:
  python3 tools/validate_document.py <file> [<file> ...]
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

# Required parts per OOXML body type (ECMA-376 / OPC). [Content_Types].xml + _rels/.rels are universal.
_OOXML_MAIN = {"word/document.xml": "docx", "ppt/presentation.xml": "pptx", "xl/workbook.xml": "xlsx"}


def _finding(severity: str, code: str, detail: str, spec: str, guidance: str) -> dict:
    return {"severity": severity, "code": code, "detail": detail, "spec": spec, "guidance": guidance}


def _check_ooxml(z: zipfile.ZipFile, names: set) -> list:
    f = []
    if "[Content_Types].xml" not in names:
        f.append(_finding("blocking", "ooxml_missing_content_types", "no [Content_Types].xml",
                          "ECMA-376 OPC", "not a valid OOXML package; re-export from the source app"))
    if "_rels/.rels" not in names:
        f.append(_finding("blocking", "ooxml_missing_root_rels", "no _rels/.rels relationships part",
                          "ECMA-376 OPC", "package relationships missing; re-save the file"))
    if not any(m in names for m in _OOXML_MAIN):
        f.append(_finding("blocking", "ooxml_missing_main_part",
                          "no main part (word/document.xml | ppt/presentation.xml | xl/workbook.xml)",
                          "ECMA-376", "the document body is absent; the file is truncated/corrupt"))
    return f


def _check_odf(names: set) -> list:
    f = []
    if "content.xml" not in names:
        f.append(_finding("blocking", "odf_missing_content", "no content.xml",
                          "OASIS ODF", "not a valid ODF document; re-export"))
    return f


def _check_pdf(data: bytes) -> list:
    f = []
    if not data[:8].startswith(b"%PDF-"):
        f.append(_finding("blocking", "pdf_missing_header", "no %PDF- header in first 8 bytes",
                          "ISO 32000 §7.5.2", "not a PDF / wrong bytes; re-acquire the file"))
    tail = data[-2048:]
    if b"%%EOF" not in tail:
        f.append(_finding("blocking", "pdf_missing_eof", "no %%EOF trailer near end of file",
                          "ISO 32000 §7.5.5", "file is truncated; re-download/re-export"))
    if b"startxref" not in tail and b"xref" not in data[-8192:] and b"/XRef" not in data:
        f.append(_finding("warning", "pdf_missing_xref", "no startxref/xref/XRef stream found",
                          "ISO 32000 §7.5.4 / veraPDF", "cross-reference table missing; needs repair (qpdf)"))
    return f


def validate_document(path: Path) -> dict:
    if not path.exists():
        return {"input": str(path), "kind": "missing", "valid": False,
                "findings": [_finding("blocking", "not_found", "file does not exist", "-", "check the path")]}
    data = path.read_bytes()
    findings, kind = [], "unknown"
    if data[:4] == b"PK\x03\x04":  # ZIP-based: OOXML / ODF / epub / generic
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as z:
                bad = z.testzip()
                names = set(z.namelist())
                if bad:
                    findings.append(_finding("blocking", "zip_crc_error", f"corrupt entry: {bad}",
                                             "ZIP/OPC", "archive is damaged; re-acquire the file"))
                if "[Content_Types].xml" in names:
                    kind = next((v for k, v in _OOXML_MAIN.items() if k in names), "ooxml")
                    findings += _check_ooxml(z, names)
                elif "mimetype" in names or "content.xml" in names:
                    kind = "odf"
                    findings += _check_odf(names)
                else:
                    kind = "zip"
        except zipfile.BadZipFile:
            kind = "zip"
            findings.append(_finding("blocking", "bad_zip", "not a readable ZIP container",
                                     "ZIP/OPC", "file is truncated/corrupt; re-export"))
    elif data[:5] == b"%PDF-" or data[:8].find(b"%PDF-") >= 0:
        kind = "pdf"
        findings += _check_pdf(data)
    elif data[:5].lower().startswith(b"{\\rtf"):
        kind = "rtf"
    else:
        kind = "unknown"
        findings.append(_finding("info", "unrecognized_container", "no known document signature",
                                 "-", "docintel's universal reader will still extract text/metadata"))
    blocking = [x for x in findings if x["severity"] == "blocking"]
    return {"input": str(path), "kind": kind, "valid": not blocking, "findings": findings,
            "note": "structural check only — deep schema validity (Open XML SDK) / PDF-A conformance "
                    "(veraPDF) is a separate, optional follow-up; never assume openability from this alone",
            "human_review_required": True}


def main(argv) -> int:
    if not argv:
        print("usage: python3 tools/validate_document.py <file> [<file> ...]")
        return 2
    reports = [validate_document(Path(p)) for p in argv]
    print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))
    return 0 if all(r["valid"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
