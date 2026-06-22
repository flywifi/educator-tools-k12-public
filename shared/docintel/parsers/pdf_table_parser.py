"""PdfPlumberTableExtractor - optional PDF table engine (Tier 2).

Registered always, but `available()` is False unless `pdfplumber` is installed, so the engine set
stays stdlib-only by default and gains PDF table recovery transparently when the dep is present.
Table independence (V02_S06 S10/S11): swapping table engines never changes the artifact contract.
"""
from __future__ import annotations

import io
from typing import List

from ..governance import Confidence, Provenance, new_id
from ..tables import TableExtractor, table_from_cells, table_text
from ..udom import Block, Cell, Source

PDF_TYPE = "application/pdf"


class PdfPlumberTableExtractor(TableExtractor):
    name = "pdfplumber-tables"
    version = "0.1.0"

    def available(self) -> bool:
        try:
            import pdfplumber  # noqa: F401
            return True
        except Exception:
            return False

    def supports(self, media_type: str) -> bool:
        return media_type == PDF_TYPE

    def extract(self, data: bytes, media_type: str, source: Source) -> List[Block]:
        import pdfplumber  # imported lazily; only reached when available()

        blocks: List[Block] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                for grid in (page.extract_tables() or []):
                    cells: List[Cell] = []
                    for r, row in enumerate(grid):
                        for c, val in enumerate(row):
                            cells.append(Cell(row=r, col=c, text=(val or "").strip(),
                                              confidence=Confidence(value=0.8, level="cell",
                                                                    method="pdfplumber:cell")))
                    table = table_from_cells(cells)
                    prov = Provenance(source_id=source.filename, parser=self.name,
                                      parser_version=self.version, extraction_method="native",
                                      page_number=pno)
                    blocks.append(Block(block_id=new_id("tbl"), type="table", page_number=pno,
                                        provenance=prov,
                                        confidence=Confidence(value=0.8, level="table",
                                                              method="pdfplumber"),
                                        table=table, text=table_text(cells)))
        return blocks
