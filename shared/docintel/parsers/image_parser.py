"""ImageParser - stdlib image ingestion (no OCR).

Recognizes image inputs and recovers their format + dimensions from the header (a `figure` block),
and signals that text recovery needs OCR. Always available; the actual text comes from the OCR stage
(`ocr.py`) when an engine is installed. Nothing is fabricated when no OCR engine is present.
"""
from __future__ import annotations

from ..governance import Confidence, Provenance, new_id
from ..images import image_info
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source


class ImageParser(Parser):
    name = "image"
    version = "0.1.0"
    capabilities = {"figures"}  # no text; OCR (ocr.py) adds text when available

    def available(self) -> bool:
        return True

    def supports(self, media_type: str) -> bool:
        return media_type.startswith("image/")

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        info = image_info(data) or {"format": media_type.split("/")[-1],
                                    "width": None, "height": None}
        prov = Provenance(source_id=source.filename, parser=self.name,
                          parser_version=self.version, extraction_method="native", page_number=1)
        conf = Confidence(value=1.0 if info.get("width") else 0.5, level="page",
                          method="image_header")
        figure = Block(block_id=new_id("img"), type="figure", page_number=1,
                       provenance=prov, confidence=conf, text=None)
        return RecoveryResult(blocks=[figure], extraction_method="native",
                              confidence=conf.value,
                              diagnostics={"image": info, "needs_ocr": True})
