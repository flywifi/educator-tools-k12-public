"""Parsers for Google Workspace export formats (and the office/ODF equivalents) - stdlib only.

Google Docs/Sheets/Slides export to these open/standard formats; reading them needs no Google APIs:
  - Docs  → .docx (PlainTextParser) · .odt (OdtParser)
  - Sheets → .csv (CsvParser) · .xlsx (XlsxParser)
  - Slides → .pptx (PptxParser)
The native Docs API JSON is handled by `google.GoogleDocsParser`. Tables are normalized into the same
UDOM `Table`/`Cell` used everywhere else; nothing is fabricated.
"""
from __future__ import annotations

import csv
import html as _html
import io
import re
import zipfile
from io import BytesIO
from typing import Dict, List, Tuple

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..tables import _place, table_from_cells, table_text
from ..udom import Block, Cell, Source

ODT_TYPE = "application/vnd.oasis.opendocument.text"
CSV_TYPE = "text/csv"
TSV_TYPE = "text/tab-separated-values"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _strip(s: str) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def _prov(source: Source, name: str, version: str, page: int = 1) -> Provenance:
    return Provenance(source_id=source.filename, parser=name, parser_version=version,
                      extraction_method="native", page_number=page)


def _table_block(cells: List[Cell], source: Source, name: str, version: str,
                 page: int = 1, header_rows: int = 0, conf: float = 0.95) -> Block:
    for cell in cells:
        if cell.confidence is None:
            cell.confidence = Confidence(value=conf, level="cell", method=f"{name}:cell")
    return Block(block_id=new_id("tbl"), type="table", page_number=page,
                 provenance=_prov(source, name, version, page),
                 confidence=Confidence(value=conf, level="table", method=name),
                 table=table_from_cells(cells, header_rows=header_rows), text=table_text(cells))


# --------------------------------------------------------------------------- ODT (OpenDocument text)
class OdtParser(Parser):
    name = "odt"
    version = "0.1.0"
    capabilities = {"text", "reading_order", "tables"}

    def supports(self, media_type: str) -> bool:
        return media_type == ODT_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        with zipfile.ZipFile(BytesIO(data)) as z:
            xml = z.read("content.xml").decode("utf-8", "ignore")
        blocks: List[Block] = []
        pattern = re.compile(
            r"(?is)<text:h\b[^>]*>.*?</text:h>|<text:p\b[^>]*>.*?</text:p>"
            r"|<table:table\b[^>]*>.*?</table:table>")
        for m in pattern.finditer(xml):
            seg = m.group(0)
            if seg.startswith("<table:table"):
                cells = self._odt_table(seg)
                if cells:
                    blocks.append(_table_block(cells, source, self.name, self.version))
            elif seg.startswith("<text:h"):
                text = _strip(seg)
                if text:
                    lvl = re.search(r'text:outline-level="(\d+)"', seg)
                    blocks.append(Block(block_id=new_id("b"), type="heading", page_number=1,
                                        provenance=_prov(source, self.name, self.version),
                                        confidence=Confidence(value=0.95, level="text",
                                                              method="odt:heading"),
                                        text=text, level=int(lvl.group(1)) if lvl else 1))
            else:
                text = _strip(seg)
                if text:
                    blocks.append(Block(block_id=new_id("b"), type="paragraph", page_number=1,
                                        provenance=_prov(source, self.name, self.version),
                                        confidence=Confidence(value=0.95, level="text",
                                                              method="odt:paragraph"),
                                        text=text))
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.95,
                              diagnostics={"format": "odt"})

    @staticmethod
    def _odt_table(seg: str) -> List[Cell]:
        rows: List[List[Tuple[str, int, int]]] = []
        for tr in re.findall(r"(?is)<table:table-row\b[^>]*>.*?</table:table-row>", seg):
            row: List[Tuple[str, int, int]] = []
            for tc in re.findall(r"(?is)<table:table-cell\b[^>]*>.*?</table:table-cell>", tr):
                cols = re.search(r'table:number-columns-spanned="(\d+)"', tc)
                rspan = re.search(r'table:number-rows-spanned="(\d+)"', tc)
                row.append((_strip(tc), int(rspan.group(1)) if rspan else 1,
                            int(cols.group(1)) if cols else 1))
            if row:
                rows.append(row)
        return _place(rows)


# --------------------------------------------------------------------------- CSV / TSV (Sheets)
class CsvParser(Parser):
    name = "csv"
    version = "0.1.0"
    capabilities = {"tables"}

    def supports(self, media_type: str) -> bool:
        return media_type in (CSV_TYPE, TSV_TYPE)

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        delimiter = "\t" if media_type == TSV_TYPE else ","
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig", "ignore")), delimiter=delimiter))
        cells = [Cell(row=r, col=c, text=(v or "").strip())
                 for r, row in enumerate(rows) for c, v in enumerate(row)]
        blocks = [_table_block(cells, source, self.name, self.version)] if cells else []
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.95,
                              diagnostics={"format": "csv", "rows": len(rows)})


# --------------------------------------------------------------------------- XLSX (Sheets)
def _ref_to_rc(ref: str) -> Tuple[int, int]:
    m = re.match(r"([A-Z]+)(\d+)", ref)
    letters, row = m.group(1), int(m.group(2))
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - 64)
    return row - 1, col - 1


class XlsxParser(Parser):
    name = "xlsx"
    version = "0.1.0"
    capabilities = {"tables"}

    def supports(self, media_type: str) -> bool:
        return media_type == XLSX_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        blocks: List[Block] = []
        with zipfile.ZipFile(BytesIO(data)) as z:
            names = z.namelist()
            shared: List[str] = []
            if "xl/sharedStrings.xml" in names:
                ss = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
                shared = [_strip(si) for si in re.findall(r"(?is)<si>(.*?)</si>", ss)]
            sheets = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml", n))
            for sheet in sheets:
                xml = z.read(sheet).decode("utf-8", "ignore")
                cellmap: Dict[Tuple[int, int], str] = {}
                maxr = maxc = -1
                for cm in re.finditer(r"(?is)<c\b([^>]*)>(.*?)</c>", xml):
                    attrs, inner = cm.group(1), cm.group(2)
                    ref = re.search(r'r="([A-Z]+\d+)"', attrs)
                    if not ref:
                        continue
                    typ = re.search(r't="(\w+)"', attrs)
                    vmatch = re.search(r"(?is)<v>(.*?)</v>", inner)
                    if vmatch:
                        raw = vmatch.group(1)
                        if typ and typ.group(1) == "s":
                            val = shared[int(raw)] if raw.isdigit() and int(raw) < len(shared) else ""
                        else:
                            val = _html.unescape(raw)
                    else:
                        inline = re.search(r"(?is)<is>(.*?)</is>", inner)
                        val = _strip(inline.group(1)) if inline else ""
                    r, c = _ref_to_rc(ref.group(1))
                    cellmap[(r, c)] = val
                    maxr, maxc = max(maxr, r), max(maxc, c)
                if cellmap:
                    cells = [Cell(row=r, col=c, text=cellmap.get((r, c), ""))
                             for r in range(maxr + 1) for c in range(maxc + 1)]
                    blocks.append(_table_block(cells, source, self.name, self.version))
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.95,
                              diagnostics={"format": "xlsx", "sheets": len(blocks)})


# --------------------------------------------------------------------------- PPTX (Slides)
class PptxParser(Parser):
    name = "pptx"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type == PPTX_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        blocks: List[Block] = []
        with zipfile.ZipFile(BytesIO(data)) as z:
            slides = sorted((n for n in z.namelist()
                             if re.match(r"ppt/slides/slide\d+\.xml", n)),
                            key=lambda n: int(re.search(r"(\d+)", n).group(1)))
            for page, slide in enumerate(slides, start=1):
                xml = z.read(slide).decode("utf-8", "ignore")
                for para in re.split(r"(?is)</a:p>", xml):
                    text = " ".join(_html.unescape(t)
                                    for t in re.findall(r"(?is)<a:t>(.*?)</a:t>", para))
                    text = " ".join(text.split())
                    if text:
                        blocks.append(Block(block_id=new_id("b"), type="paragraph",
                                            page_number=page,
                                            provenance=_prov(source, self.name, self.version, page),
                                            confidence=Confidence(value=0.95, level="text",
                                                                  method="pptx:text"),
                                            text=text))
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.95,
                              diagnostics={"format": "pptx", "slides": len(blocks)})
