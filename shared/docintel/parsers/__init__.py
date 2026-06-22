"""Parser plugins. Each wraps an extraction technology behind the `Parser` contract
(shared/docintel/parser-orchestration.md) so it can be added/removed without touching consumers.
"""
from .plaintext_parser import PlainTextParser
from .pymupdf_parser import PyMuPDFParser

__all__ = ["PlainTextParser", "PyMuPDFParser"]
