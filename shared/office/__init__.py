"""Office + Google authoring — real .pptx/.docx/.xlsx and Google Docs/Sheets/Slides outputs (gated)."""
from .google_bridge import to_google
from .office_authoring import build_docx, build_pptx, build_xlsx, convert

__all__ = ["build_pptx", "build_docx", "build_xlsx", "convert", "to_google"]
