"""Parser + table/OCR-engine plugins. Each wraps an extraction technology behind a stable contract
(`Parser` in parser-orchestration.md; `TableExtractor` in table-intelligence.md; `OcrEngine` in
ocr-architecture.md) so it can be added/removed without touching consumers.
"""
from .calendar_parser import IcsParser
from .email_parser import EmlParser
from .image_parser import ImageParser
from .pdf_table_parser import PdfPlumberTableExtractor
from .plaintext_parser import PlainTextParser
from .pymupdf_parser import PyMuPDFParser
from .tesseract_ocr import TesseractEngine
from .workspace_parsers import CsvParser, OdtParser, PptxParser, XlsxParser

__all__ = [
    "PlainTextParser", "PyMuPDFParser", "ImageParser",
    "PdfPlumberTableExtractor", "TesseractEngine",
    "OdtParser", "CsvParser", "XlsxParser", "PptxParser",
    "IcsParser", "EmlParser",
]
