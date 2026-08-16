"""TesseractEngine - optional OCR for images via pytesseract (+ Pillow).

Registered always, but `available()` is False unless `pytesseract` and `PIL` import, so the engine
set stays stdlib-only by default. Produces confidence-aware text blocks. PDF OCR needs a
rasterization pass (PyMuPDF/pdf2image) and is staged - reported, never faked.
"""
from __future__ import annotations

import io
from typing import List, Optional

from ..ocr import OcrEngine, ocr_blocks
from ..orchestration import StageNotImplemented
from ..udom import Block, Source

PDF_TYPE = "application/pdf"

def _find(name: str):
    """health.binaries.find_binary, importable however this module was loaded."""
    import sys
    from pathlib import Path
    try:
        from health.binaries import find_binary
    except ImportError:                                  # shared/ not yet on sys.path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from health.binaries import find_binary
    return find_binary(name)



class TesseractEngine(OcrEngine):
    name = "tesseract"
    version = "0.1.0"

    def available(self) -> bool:
        """True only when the Python wrapper AND the tesseract ENGINE are both present.

        This used to return True on the wrapper alone, so a machine with pytesseract but no
        tesseract binary advertised OCR and then failed at call time — the opposite of the honest
        capability gap this registry exists to report. The engine is off PATH by default on macOS
        (Homebrew) and Windows, so the lookup is health.binaries, not shutil.which."""
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except BaseException:
            return False
        return _find("tesseract") is not None

    def supports(self, media_type: str) -> bool:
        # Images directly; PDFs are rasterized locally (PyMuPDF) then OCR'd - fully offline.
        return media_type.startswith("image/") or media_type == PDF_TYPE

    def recognize(self, data: bytes, media_type: str, source: Source,
                  pages: Optional[List[int]] = None) -> List[Block]:
        import pytesseract
        from PIL import Image

        if media_type == PDF_TYPE:
            return self._ocr_pdf(data, source, pages)
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)
        conf = _mean_confidence(pytesseract, image)
        return ocr_blocks(text, source, self, page_number=1, confidence=conf)

    def _ocr_pdf(self, data: bytes, source: Source,
                 pages: Optional[List[int]]) -> List[Block]:
        """Rasterize PDF pages locally (PyMuPDF) and OCR each - no network at any step."""
        try:
            import fitz  # PyMuPDF, local rasterizer
        except BaseException:
            raise StageNotImplemented(
                "PDF OCR needs PyMuPDF to rasterize pages (pip install pymupdf); reported, not faked")
        import pytesseract
        from PIL import Image

        blocks: List[Block] = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            targets = pages or range(1, pdf.page_count + 1)
            for pno in targets:
                if pno < 1 or pno > pdf.page_count:
                    continue
                pix = pdf[pno - 1].get_pixmap(dpi=200)        # render at 200 DPI for OCR
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img)
                conf = _mean_confidence(pytesseract, img)
                blocks.extend(ocr_blocks(text, source, self, page_number=pno, confidence=conf))
        return blocks


def _mean_confidence(pytesseract, image) -> float:
    """Average per-word confidence (0-1) from Tesseract, defaulting to 0.6 if unavailable."""
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        vals = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
        return round(sum(vals) / len(vals) / 100.0, 3) if vals else 0.6
    except Exception:
        return 0.6
