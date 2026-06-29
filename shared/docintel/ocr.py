"""OCR - text recovery for image-based content (V02_S04).

"OCR is a recovery capability used when information cannot be recovered through native extraction
alone." OCR engines are swappable + replaceable behind the `OcrEngine` contract (independence S9,
replacement S10), produce **confidence-aware** text, and are run by the pipeline's targeted OCR stage
only when needed. There is no stdlib OCR, so engines activate only when their deps are installed; when
none is available the pipeline reports a capability gap and **never fabricates** text.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Optional

from .governance import Confidence, Provenance, new_id
from .udom import Block, Source


class OcrEngine(ABC):
    """Swappable OCR engine (independence/replacement, V02_S04 S9/S10)."""
    name: str = "ocr-engine"
    version: str = "0"

    def available(self) -> bool:
        return True

    @abstractmethod
    def supports(self, media_type: str) -> bool: ...

    @abstractmethod
    def recognize(self, data: bytes, media_type: str, source: Source,
                  pages: Optional[List[int]] = None) -> List[Block]: ...


def ocr_blocks(text: str, source: Source, engine: "OcrEngine", page_number: int,
               confidence: float) -> List[Block]:
    """Turn recognized text into governed UDOM blocks (extraction_method='ocr')."""
    blocks: List[Block] = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        prov = Provenance(source_id=source.filename, parser=engine.name,
                          parser_version=engine.version, extraction_method="ocr",
                          page_number=page_number)
        conf = Confidence(value=confidence, level="text", method=f"{engine.name}:ocr")
        blocks.append(Block(block_id=new_id("ocr"), type="paragraph", page_number=page_number,
                            provenance=prov, confidence=conf, text=para))
    return blocks


class OcrRegistry:
    def __init__(self) -> None:
        self._engines: List[OcrEngine] = []

    def register(self, engine: OcrEngine) -> "OcrRegistry":
        self._engines.append(engine)
        return self

    def available(self) -> List[OcrEngine]:
        return [e for e in self._engines if e.available()]

    def select(self, media_type: str) -> Optional[OcrEngine]:
        for e in self.available():
            if e.supports(media_type):
                return e
        return None

    def describe(self) -> List[dict]:
        return [{"name": e.name, "version": e.version, "available": e.available()}
                for e in self._engines]


def default_ocr_registry() -> OcrRegistry:
    """Tesseract handles images when installed; PDF OCR (rasterize+OCR) is added the same way."""
    from .parsers.tesseract_ocr import TesseractEngine

    reg = OcrRegistry()
    reg.register(TesseractEngine())
    return reg
