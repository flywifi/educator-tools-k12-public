"""Table Intelligence (V02_S06): detect, reconstruct, normalize tables into UDOM Table/Cell.

"Tables are structures, not formatted text." Table engines are swappable + replaceable
(independence, S10/S11) behind the `TableExtractor` contract - exactly like parsers. The stdlib
engine handles .docx/.html/.md today (detection, row/col/header/merged-cell reconstruction,
normalization, conflict handling, confidence); PDF table engines (pdfplumber/Camelot) plug in
behind the same contract. Normalized tables are platform outputs; nothing is fabricated.
"""
from __future__ import annotations

import html as _html
import re
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from .governance import Confidence, Provenance, new_id
from .udom import Block, Cell, Source, Table

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# A normalized table candidate: (Table, confidence, diagnostics).
TableCandidate = Tuple[Table, float, Dict[str, object]]


# --------------------------------------------------------------------------- normalization
def _norm(s: str) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def _attr_int(attrs: str, name: str, default: int = 1) -> int:
    m = re.search(rf'{name}\s*=\s*"?(\d+)', attrs, re.I)
    return int(m.group(1)) if m else default


def table_from_cells(cells: List[Cell], header_rows: int = 0) -> Table:
    """Normalize a list of placed cells into a UDOM Table (rows/cols from cell extents)."""
    rows = max((c.row + c.rowspan for c in cells), default=0)
    cols = max((c.col + c.colspan for c in cells), default=0)
    return Table(rows=rows, cols=cols, cells=cells, header_rows=header_rows)


def table_text(cells: List[Cell]) -> str:
    """Plain-text rendering of a table so text-only consumers still see something."""
    grid: Dict[int, Dict[int, str]] = {}
    for c in cells:
        grid.setdefault(c.row, {})[c.col] = c.text
    return "\n".join(" | ".join(grid[r][c] for c in sorted(grid[r])) for r in sorted(grid))


def _place(rows: List[List[Tuple[str, int, int]]]) -> List[Cell]:
    """Occupancy-aware placement: assign (row,col) accounting for row/col spans (conflict S8)."""
    cells: List[Cell] = []
    occupied: set = set()
    for r, row in enumerate(rows):
        c = 0
        for text, rs, cs in row:
            while (r, c) in occupied:
                c += 1
            cells.append(Cell(row=r, col=c, text=text, rowspan=rs, colspan=cs))
            for dr in range(rs):
                for dc in range(cs):
                    if dr or dc:
                        occupied.add((r + dr, c + dc))
            c += cs
    return cells


# --------------------------------------------------------------------------- markdown
def _is_md_sep(line: str) -> bool:
    s = line.strip()
    return bool(s) and set(s) <= set("|:- ") and "-" in s


def _split_md(line: str) -> List[str]:
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") else s
    return [c.strip() for c in s.split("|")]


def extract_markdown_tables(text: str) -> List[TableCandidate]:
    out: List[TableCandidate] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if ("|" in lines[i] and not _is_md_sep(lines[i])
                and i + 1 < len(lines) and _is_md_sep(lines[i + 1])):
            header = _split_md(lines[i])
            ncols = len(header)
            grid = [header]
            j = i + 2
            while j < len(lines) and "|" in lines[j] and not _is_md_sep(lines[j]):
                grid.append(_split_md(lines[j]))
                j += 1
            ragged = sum(1 for row in grid if len(row) != ncols)
            cells: List[Cell] = []
            for r, row in enumerate(grid):
                for c in range(ncols):
                    cells.append(Cell(row=r, col=c, text=row[c] if c < len(row) else ""))
            conf = 0.90 if not ragged else 0.75
            out.append((table_from_cells(cells, header_rows=1), conf,
                        {"format": "markdown", "ragged_rows": ragged}))
            i = j
        else:
            i += 1
    return out


# --------------------------------------------------------------------------- html
def extract_html_tables(htmltext: str) -> List[TableCandidate]:
    out: List[TableCandidate] = []
    for tbl in re.findall(r"(?is)<table\b.*?</table>", htmltext):
        rows: List[List[Tuple[str, int, int]]] = []
        row_is_header: List[bool] = []
        for tr in re.findall(r"(?is)<tr\b.*?</tr>", tbl):
            row: List[Tuple[str, int, int]] = []
            had_th = False
            for m in re.finditer(r"(?is)<(t[dh])\b([^>]*)>(.*?)</\1>", tr):
                tag, attrs, content = m.group(1), m.group(2), m.group(3)
                had_th = had_th or tag.lower() == "th"
                row.append((_norm(content), _attr_int(attrs, "rowspan"), _attr_int(attrs, "colspan")))
            if row:
                rows.append(row)
                row_is_header.append(had_th)
        # Header rows are the contiguous header-bearing rows at the top of the table.
        header_rows = 0
        for is_h in row_is_header:
            if is_h:
                header_rows += 1
            else:
                break
        cells = _place(rows)
        if cells:
            out.append((table_from_cells(cells, header_rows=header_rows), 0.90, {"format": "html"}))
    return out


# --------------------------------------------------------------------------- docx
def _docx_cell(inner: str) -> Tuple[str, int, Optional[str]]:
    tcpr = re.search(r"(?is)<w:tcPr>.*?</w:tcPr>", inner)
    tcpr_s = tcpr.group(0) if tcpr else ""
    gs = re.search(r'<w:gridSpan[^>]*w:val="(\d+)"', tcpr_s)
    colspan = int(gs.group(1)) if gs else 1
    vm = re.search(r"<w:vMerge([^>]*)>", tcpr_s)
    vstate = None
    if vm:
        val = re.search(r'w:val="(\w+)"', vm.group(1))
        vstate = "restart" if (val and val.group(1) == "restart") else "continue"
    body = re.sub(r"(?is)<w:tcPr>.*?</w:tcPr>", "", inner)
    return _norm(body), colspan, vstate


def extract_docx_tables(document_xml: str) -> List[TableCandidate]:
    out: List[TableCandidate] = []
    for tbl in re.findall(r"(?is)<w:tbl>.*?</w:tbl>", document_xml):
        cells: List[Cell] = []
        restart_at: Dict[int, Cell] = {}
        merge_conflicts = 0
        for r, tr in enumerate(re.findall(r"(?is)<w:tr\b.*?</w:tr>", tbl)):
            c = 0
            for m in re.finditer(r"(?is)<w:tc\b[^>]*>(.*?)</w:tc>", tr):
                text, colspan, vstate = _docx_cell(m.group(1))
                if vstate == "continue":
                    cell = restart_at.get(c)
                    if cell:
                        cell.rowspan += 1
                    else:
                        merge_conflicts += 1
                    c += colspan
                    continue
                cell = Cell(row=r, col=c, text=text, colspan=colspan, rowspan=1)
                cells.append(cell)
                if vstate == "restart":
                    restart_at[c] = cell
                else:
                    restart_at.pop(c, None)
                c += colspan
        if cells:
            conf = 0.95 if not merge_conflicts else 0.85
            out.append((table_from_cells(cells), conf,
                        {"format": "docx", "merge_conflicts": merge_conflicts}))
    return out


# --------------------------------------------------------------------------- engine contract
class TableExtractor(ABC):
    """Swappable table engine (independence/replacement, V02_S06 S10/S11)."""
    name: str = "table-extractor"
    version: str = "0"

    def available(self) -> bool:
        return True

    @abstractmethod
    def supports(self, media_type: str) -> bool: ...

    @abstractmethod
    def extract(self, data: bytes, media_type: str, source: Source) -> List[Block]: ...


def _to_blocks(candidates: List[TableCandidate], source: Source, engine: str,
               version: str, page_number: int = 1) -> List[Block]:
    blocks: List[Block] = []
    for table, conf, diag in candidates:
        prov = Provenance(source_id=source.filename, parser=engine, parser_version=version,
                          extraction_method="native", page_number=page_number)
        for cell in table.cells:
            if cell.confidence is None:
                cell.confidence = Confidence(value=conf, level="cell", method=f"{engine}:cell")
        blocks.append(Block(block_id=new_id("tbl"), type="table", page_number=page_number,
                            provenance=prov,
                            confidence=Confidence(value=conf, level="table",
                                                  method=f"{engine}:{diag.get('format')}"),
                            table=table, text=table_text(table.cells)))
    return blocks


class StdlibTableExtractor(TableExtractor):
    name = "stdlib-tables"
    version = "0.1.0"

    def supports(self, media_type: str) -> bool:
        return media_type in (DOCX_TYPE, "text/html", "text/markdown")

    def extract(self, data: bytes, media_type: str, source: Source) -> List[Block]:
        if media_type == DOCX_TYPE:
            with zipfile.ZipFile(BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            candidates = extract_docx_tables(xml)
        elif media_type == "text/html":
            candidates = extract_html_tables(data.decode("utf-8", "ignore"))
        else:
            candidates = extract_markdown_tables(data.decode("utf-8", "ignore"))
        return _to_blocks(candidates, source, self.name, self.version)


class TableRegistry:
    def __init__(self) -> None:
        self._engines: List[TableExtractor] = []

    def register(self, engine: TableExtractor) -> "TableRegistry":
        self._engines.append(engine)
        return self

    def available(self) -> List[TableExtractor]:
        return [e for e in self._engines if e.available()]

    def select(self, media_type: str) -> Optional[TableExtractor]:
        for e in self.available():
            if e.supports(media_type):
                return e
        return None

    def describe(self) -> List[Dict[str, object]]:
        return [{"name": e.name, "version": e.version, "available": e.available()}
                for e in self._engines]


def default_table_registry() -> TableRegistry:
    """PDF table engine preferred for PDFs when available; stdlib engine always handles docx/html/md."""
    from .parsers.pdf_table_parser import PdfPlumberTableExtractor

    reg = TableRegistry()
    reg.register(PdfPlumberTableExtractor())
    reg.register(StdlibTableExtractor())
    return reg
