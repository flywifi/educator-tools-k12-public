"""Parser + table-engine plugins. Each wraps an extraction technology behind a stable contract
(`Parser` in shared/docintel/parser-orchestration.md; `TableExtractor` in table-intelligence.md)
so it can be added/removed without touching consumers.
"""
from .pdf_table_parser import PdfPlumberTableExtractor
from .plaintext_parser import PlainTextParser
from .pymupdf_parser import PyMuPDFParser

__all__ = ["PlainTextParser", "PyMuPDFParser", "PdfPlumberTableExtractor"]
