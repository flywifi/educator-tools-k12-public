"""docintel - TOS-native Document Intelligence engine.

Documents in, governed knowledge assets out. Parser-independent, artifact-centric, governed.
Canonical design: shared/docintel/README.md. Runnable entry point: tools/docintel_run.py.
"""
from __future__ import annotations

from .artifact import build_consumer_artifact, build_knowledge_artifact
from .change import (
    IMPACT_DIMENSIONS,
    ChangeClass,
    ChangeRecord,
    build_change_record,
    validate_change,
)
from .google import DRIVE_EXPORT_MIME, GoogleDocsParser, is_google_doc_json
from .governance import Confidence, Evidence, LineageEvent, Provenance
from .images import image_info
from .ocr import OcrEngine, OcrRegistry, default_ocr_registry, ocr_blocks
from .tables import (
    StdlibTableExtractor,
    TableExtractor,
    TableRegistry,
    default_table_registry,
    extract_docx_tables,
    extract_html_tables,
    extract_markdown_tables,
)
from .orchestration import (
    CAPABILITIES,
    RETRIEVAL_STATES,
    Parser,
    ParserRegistry,
    Pipeline,
    PipelineConfig,
    RecoveryResult,
    Stage,
    StageNotImplemented,
    default_registry,
    guess_media_type,
    retrieval_state,
)
from .udom import Block, Cell, Page, Source, Table, TextSpan, UDOMDocument, UDOM_VERSION
from .validation import validate
from .recurse import iter_children, parse_recursive
from .html_util import decode_bytes, get_links, get_tables, get_text_blocks

__version__ = "0.1.0"

__all__ = [
    "Pipeline", "PipelineConfig", "Parser", "ParserRegistry", "RecoveryResult", "Stage",
    "StageNotImplemented", "default_registry", "guess_media_type", "retrieval_state",
    "CAPABILITIES", "RETRIEVAL_STATES",
    "UDOMDocument", "Source", "Page", "Block", "Table", "Cell", "TextSpan", "UDOM_VERSION",
    "Provenance", "Confidence", "LineageEvent", "Evidence",
    "build_knowledge_artifact", "build_consumer_artifact", "validate",
    "iter_children", "parse_recursive",
    "decode_bytes", "get_links", "get_tables", "get_text_blocks",
    "ChangeClass", "ChangeRecord", "IMPACT_DIMENSIONS", "build_change_record", "validate_change",
    "TableExtractor", "TableRegistry", "StdlibTableExtractor", "default_table_registry",
    "extract_docx_tables", "extract_html_tables", "extract_markdown_tables",
    "OcrEngine", "OcrRegistry", "default_ocr_registry", "ocr_blocks", "image_info",
    "GoogleDocsParser", "DRIVE_EXPORT_MIME", "is_google_doc_json",
    "__version__",
]
