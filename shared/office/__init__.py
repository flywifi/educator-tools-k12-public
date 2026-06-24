"""Office authoring engine — real .pptx/.docx/.xlsx from a spec (capability-gated). See office_authoring.py."""
from .office_authoring import build_docx, build_pptx, build_xlsx, convert

__all__ = ["build_pptx", "build_docx", "build_xlsx", "convert"]
