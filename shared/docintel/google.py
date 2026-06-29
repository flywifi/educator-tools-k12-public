"""Google Workspace support: the native Google Docs API JSON parser + the Drive export map.

A Google Doc has no "file" of its own - you either export it (→ docx/odt/pdf/html/txt, handled by the
file-format parsers) or read it via the Docs API `documents.get`, which returns a JSON document
resource. `GoogleDocsParser` reads that JSON natively (stdlib) into UDOM with headings, paragraphs,
and tables. Fetching from Drive (OAuth/network) is intentionally out of scope - bring the exported
file or the API JSON; this skill reads documents, it is not a Drive connector.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .governance import Confidence, Provenance, new_id
from .orchestration import Parser, RecoveryResult
from .tables import table_from_cells, table_text
from .udom import Block, Cell, Source

# Google Drive export targets, for reference/documentation (Drive `files.export` mimeType values).
DRIVE_EXPORT_MIME: Dict[str, List[str]] = {
    "application/vnd.google-apps.document": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.oasis.opendocument.text",                                  # .odt
        "application/pdf", "text/html", "text/plain",
    ],
    "application/vnd.google-apps.spreadsheet": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
        "text/csv", "application/vnd.oasis.opendocument.spreadsheet",               # .ods
    ],
    "application/vnd.google-apps.presentation": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
        "application/pdf", "application/vnd.oasis.opendocument.presentation",        # .odp
    ],
}


def is_google_doc_json(data: bytes) -> bool:
    """True if the bytes look like a Google Docs API `documents.get` resource."""
    try:
        doc = json.loads(data)
    except Exception:
        return False
    return (isinstance(doc, dict) and isinstance(doc.get("body"), dict)
            and isinstance(doc["body"].get("content"), list))


def _para_text(paragraph: Dict[str, Any]) -> str:
    return "".join(e.get("textRun", {}).get("content", "")
                   for e in paragraph.get("elements", [])).strip()


def _content_text(content: List[Dict[str, Any]]) -> str:
    """Flatten a structural-element list (e.g., a table cell's content) to text."""
    parts = [_para_text(el["paragraph"]) for el in content if "paragraph" in el]
    return " ".join(p for p in parts if p)


def _heading(named_style: str) -> Optional[int]:
    if named_style.startswith("HEADING_"):
        return int(named_style.split("_")[1])
    if named_style == "TITLE":
        return 1
    if named_style == "SUBTITLE":
        return 2
    return None


class GoogleDocsParser(Parser):
    name = "google-docs-json"
    version = "0.1.0"
    capabilities = {"text", "reading_order", "tables"}

    def available(self) -> bool:
        return True

    def supports(self, media_type: str) -> bool:
        return media_type in ("application/json", "application/vnd.google-apps.document")

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        if not is_google_doc_json(data):
            return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                                  diagnostics={"status": "not_google_docs_json"})
        doc = json.loads(data)
        blocks: List[Block] = []

        def prov() -> Provenance:
            return Provenance(source_id=source.filename, parser=self.name,
                              parser_version=self.version, extraction_method="native",
                              page_number=1)

        title = doc.get("title")
        if title:
            blocks.append(Block(block_id=new_id("b"), type="heading", page_number=1,
                                provenance=prov(),
                                confidence=Confidence(value=0.99, level="text", method="gdocs:title"),
                                text=title, level=1))
        for el in doc["body"]["content"]:
            if "paragraph" in el:
                text = _para_text(el["paragraph"])
                if not text:
                    continue
                nst = el["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
                level = _heading(nst)
                blocks.append(Block(block_id=new_id("b"),
                                    type="heading" if level else "paragraph", page_number=1,
                                    provenance=prov(),
                                    confidence=Confidence(value=0.98, level="text",
                                                          method="gdocs:paragraph"),
                                    text=text, level=level))
            elif "table" in el:
                cells: List[Cell] = []
                for r, row in enumerate(el["table"].get("tableRows", [])):
                    for c, cell in enumerate(row.get("tableCells", [])):
                        cells.append(Cell(row=r, col=c, text=_content_text(cell.get("content", [])),
                                          confidence=Confidence(value=0.95, level="cell",
                                                                method="gdocs:cell")))
                if cells:
                    blocks.append(Block(block_id=new_id("tbl"), type="table", page_number=1,
                                        provenance=prov(),
                                        confidence=Confidence(value=0.95, level="table",
                                                              method="gdocs:table"),
                                        table=table_from_cells(cells), text=table_text(cells)))
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.97,
                              diagnostics={"format": "google_docs_json", "title": title,
                                           "blocks": len(blocks)})
