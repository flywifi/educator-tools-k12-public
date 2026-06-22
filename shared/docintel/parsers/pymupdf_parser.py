"""PyMuPDFParser - optional native-PDF reference parser (Tier 1).

Registered always, but `available()` is False unless `pymupdf` (import name `fitz`) is installed,
so the pipeline stays stdlib-only by default and gains PDF support transparently when the dep is
present. This is the parser-independence pattern: add capability without changing any consumer.
"""
from __future__ import annotations

from typing import List

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

PDF_TYPE = "application/pdf"


class PyMuPDFParser(Parser):
    name = "pymupdf"
    version = "0.1.0"
    capabilities = {"text", "layout", "reading_order", "figures"}

    def available(self) -> bool:
        try:
            import fitz  # noqa: F401  (pymupdf)
            return True
        except Exception:
            return False

    def supports(self, media_type: str) -> bool:
        return media_type == PDF_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        import fitz  # imported lazily; only reached when available()

        blocks: List[Block] = []
        confidences: List[float] = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            page_count = pdf.page_count
            for pno in range(page_count):
                page = pdf[pno]
                for raw in page.get_text("blocks"):
                    # raw = (x0, y0, x1, y1, text, block_no, block_type)
                    x0, y0, x1, y1, text = raw[0], raw[1], raw[2], raw[3], raw[4]
                    text = (text or "").strip()
                    if not text:
                        continue
                    bbox = [float(x0), float(y0), float(x1), float(y1)]
                    prov = Provenance(source_id=source.filename, parser=self.name,
                                      parser_version=self.version, extraction_method="native",
                                      page_number=pno + 1, bbox=bbox)
                    conf = Confidence(value=0.99, level="text", method="pymupdf:native")
                    blocks.append(Block(block_id=new_id("b"), type="paragraph",
                                        page_number=pno + 1, provenance=prov, confidence=conf,
                                        text=text, bbox=bbox))
                    confidences.append(0.99)
        return RecoveryResult(blocks=blocks, extraction_method="native",
                              confidence=(sum(confidences) / len(confidences) if confidences else 0.0),
                              diagnostics={"pages": page_count, "blocks": len(blocks)})
