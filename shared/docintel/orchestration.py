"""Parser Orchestration + the document-processing pipeline.

Canonical contract: shared/docintel/parser-orchestration.md and README.md.
Parsers are swappable plugins behind one contract (Principle 4); the pipeline runs the
governed stages (V02 S02) and never bypasses governance. The default happy-path runs end to
end; advanced execution modes are staged behind `StageNotImplemented`.
"""
from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .governance import Confidence, LineageEvent, Provenance, new_id, now_iso
from .ocr import OcrRegistry, default_ocr_registry
from .tables import TableRegistry, default_table_registry
from .udom import Block, Page, Source, UDOMDocument

CAPABILITIES = {"text", "ocr", "tables", "layout", "reading_order", "figures", "formulas"}

# Retrieval-state ladder (visibility != extraction): how much of the document was actually recovered.
RETRIEVAL_STATES = ("referenced", "metadata_only", "content_ingested", "local_artifact_saved")


def retrieval_state(doc: "UDOMDocument") -> str:
    """Honest recovery level. `content_ingested` only when real content (text or a table) was
    recovered; `metadata_only` when something was seen but no content (e.g. an image with no OCR
    engine); `referenced` when nothing was recovered. `local_artifact_saved` is a downstream state."""
    has_content = any((b.text or b.table) for _, b in doc.iter_blocks())
    if has_content:
        return "content_ingested"
    if any(True for _ in doc.iter_blocks()):
        return "metadata_only"
    return "referenced"

_EXT_MEDIA = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".htm": "text/html",
    ".html": "text/html",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    # Google Workspace exports + open/office equivalents
    ".json": "application/json",  # Google Docs API resource (content-sniffed)
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Lightweight workplace evidence files (calendar invites, saved email)
    ".ics": "text/calendar",
    ".eml": "message/rfc822",
    # Caption / transcript tracks (video calls, recordings)
    ".vtt": "text/vtt",
    ".srt": "application/x-subrip",
    # Audio / video (transcribed via a Transcriber engine when available; gap-reported otherwise)
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".ogg": "audio/ogg", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
    # Rich text + legacy/ODF office (read via LibreOffice when present, else universal fallback)
    ".rtf": "application/rtf",
    ".doc": "application/msword", ".ppt": "application/vnd.ms-powerpoint", ".xls": "application/vnd.ms-excel",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odg": "application/vnd.oasis.opendocument.graphics",
    # Common text/code/markup -> the stdlib text parser; anything unmapped -> universal fallback
    ".xml": "text/plain", ".yaml": "text/plain", ".yml": "text/plain", ".toml": "text/plain",
    ".ini": "text/plain", ".cfg": "text/plain", ".log": "text/plain", ".rst": "text/plain",
    ".tex": "text/plain", ".py": "text/plain", ".js": "text/plain", ".ts": "text/plain",
    ".java": "text/plain", ".c": "text/plain", ".cpp": "text/plain", ".h": "text/plain",
    ".go": "text/plain", ".rb": "text/plain", ".sh": "text/plain", ".sql": "text/plain",
}


def guess_media_type(filename: str) -> str:
    return _EXT_MEDIA.get(os.path.splitext(filename)[1].lower(), "application/octet-stream")


class Stage(str, Enum):
    INGESTION = "ingestion"
    RECOVERY = "recovery"
    OCR = "ocr"
    TABLES = "table_intelligence"
    STRUCTURE = "structure"
    GOVERNANCE = "governance"
    KNOWLEDGE = "knowledge_construction"
    ARTIFACT = "artifact_generation"
    DELIVERY = "consumer_delivery"


class StageNotImplemented(NotImplementedError):
    """A pipeline stage/mode that is part of the skeleton and not yet filled in."""


@dataclass
class RecoveryResult:
    blocks: List[Block]
    extraction_method: str = "native"
    confidence: float = 0.0
    diagnostics: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- parsers
class Parser(ABC):
    """Contract every parser/OCR wrapper implements. Consumers never name a parser."""
    name: str = "parser"
    version: str = "0"
    capabilities: Set[str] = set()

    def available(self) -> bool:
        """True if this parser's dependencies are importable in this environment."""
        return True

    @abstractmethod
    def supports(self, media_type: str) -> bool: ...

    @abstractmethod
    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult: ...


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: List[Parser] = []

    def register(self, parser: Parser) -> "ParserRegistry":
        self._parsers.append(parser)
        return self

    def available(self) -> List[Parser]:
        return [p for p in self._parsers if p.available()]

    def select(self, media_type: str, required: Optional[Set[str]] = None) -> Optional[Parser]:
        """Pick by required-capability coverage then registration priority. Never by name."""
        required = required or set()
        candidates = [p for p in self.available() if p.supports(media_type)]
        if not candidates:
            return None
        candidates.sort(key=lambda p: len(required & p.capabilities), reverse=True)
        return candidates[0]

    @staticmethod
    def capability_gaps(parser: Optional[Parser], required: Optional[Set[str]]) -> Set[str]:
        return set(required or set()) - (parser.capabilities if parser else set())

    def describe(self) -> List[Dict[str, Any]]:
        return [
            {"name": p.name, "version": p.version, "available": p.available(),
             "capabilities": sorted(p.capabilities)}
            for p in self._parsers
        ]


def default_registry() -> ParserRegistry:
    """PDF/image/Workspace parsers match by media type; stdlib text parser is the always-on fallback."""
    from .google import GoogleDocsParser
    from .parsers.calendar_parser import IcsParser
    from .parsers.caption_parser import SrtParser, VttParser
    from .parsers.email_parser import EmlParser
    from .parsers.image_parser import ImageParser
    from .parsers.libreoffice_parser import LegacyOfficeParser
    from .parsers.media_parser import MediaTranscriptParser
    from .parsers.plaintext_parser import PlainTextParser
    from .parsers.pymupdf_parser import PyMuPDFParser
    from .parsers.universal_parser import RtfParser, UniversalFallbackParser
    from .parsers.workspace_parsers import CsvParser, OdtParser, PptxParser, XlsxParser

    reg = ParserRegistry()
    reg.register(PyMuPDFParser())
    reg.register(ImageParser())
    reg.register(GoogleDocsParser())          # Google Docs API JSON
    reg.register(OdtParser())                 # Docs → ODF text
    reg.register(CsvParser())                 # Sheets → CSV/TSV
    reg.register(XlsxParser())                # Sheets → XLSX
    reg.register(PptxParser())                # Slides → PPTX
    reg.register(IcsParser())                 # calendar invite (.ics)
    reg.register(EmlParser())                 # saved email (.eml)
    reg.register(VttParser())                 # WebVTT caption/transcript
    reg.register(SrtParser())                 # SubRip caption/transcript
    reg.register(MediaTranscriptParser())     # audio/video → transcription engine (gap if none)
    reg.register(RtfParser())                 # .rtf
    reg.register(LegacyOfficeParser())        # .doc/.ppt/.xls/.odp/.ods via LibreOffice (gated on soffice)
    reg.register(PlainTextParser())           # .txt/.md/.html/.docx
    reg.register(UniversalFallbackParser())   # last resort: read ANY file (text decode, else binary metadata)
    return reg


# --------------------------------------------------------------------------- pipeline
@dataclass
class PipelineConfig:
    required_capabilities: Set[str] = field(default_factory=lambda: {"text", "reading_order"})
    # Feature flags: experimental stages default OFF (see SKILL.md "experimental features").
    flags: Dict[str, bool] = field(default_factory=dict)


class Pipeline:
    """Document -> governed knowledge asset. Each stage appends lineage; nothing skips governance."""

    def __init__(self, registry: Optional[ParserRegistry] = None,
                 config: Optional[PipelineConfig] = None,
                 table_registry: Optional[TableRegistry] = None,
                 ocr_registry: Optional[OcrRegistry] = None) -> None:
        self.registry = registry or default_registry()
        self.table_registry = table_registry or default_table_registry()
        self.ocr_registry = ocr_registry or default_ocr_registry()
        self.config = config or PipelineConfig()

    def run(self, data: bytes, filename: str, media_type: Optional[str] = None) -> UDOMDocument:
        media_type = media_type or guess_media_type(filename)
        doc = self._ingest(data, filename, media_type)
        self._recover(doc, data, media_type)
        self._ocr(doc, data, media_type)
        self._tables(doc, data, media_type)
        self._structure(doc)
        self._govern(doc)
        self._knowledge(doc)
        return doc

    # -- stages ----------------------------------------------------------
    def _ingest(self, data: bytes, filename: str, media_type: str) -> UDOMDocument:
        sha = hashlib.sha256(data).hexdigest()
        source = Source(filename=os.path.basename(filename), media_type=media_type,
                        sha256=sha, byte_length=len(data))
        prov = Provenance(source_id=source.filename, parser="ingestion",
                          extraction_method="manual", page_number=None)
        doc = UDOMDocument(document_id=new_id("doc"), source=source, provenance=prov)
        doc.add_lineage(LineageEvent(stage=Stage.INGESTION.value, operation="register",
                                     tool="docintel.pipeline", inputs=[source.filename],
                                     outputs=[doc.document_id]))
        return doc

    def _recover(self, doc: UDOMDocument, data: bytes, media_type: str) -> None:
        required = self.config.required_capabilities
        parser = self.registry.select(media_type, required)
        if parser is None:
            doc.diagnostics["recovery"] = {"status": "no_parser_available",
                                           "media_type": media_type}
            doc.add_lineage(LineageEvent(stage=Stage.RECOVERY.value, operation="recover",
                                         tool="none", outputs=[]))
            return
        result = parser.parse(data, media_type, doc.source)
        gaps = ParserRegistry.capability_gaps(parser, required)
        # Group recovered blocks into pages (preserving order).
        pages: Dict[int, Page] = {}
        for block in result.blocks:
            pages.setdefault(block.page_number, Page(page_number=block.page_number)).blocks.append(block)
        doc.pages = [pages[k] for k in sorted(pages)]
        doc.diagnostics["recovery"] = {
            "status": "ok",
            "parser": parser.name,
            "extraction_method": result.extraction_method,
            "capability_gaps": sorted(gaps),  # honest: what we could NOT do (e.g. ocr)
            **result.diagnostics,
        }
        doc.add_lineage(LineageEvent(stage=Stage.RECOVERY.value, operation="recover",
                                     tool=parser.name, tool_version=parser.version,
                                     inputs=[doc.source.filename],
                                     outputs=[b.block_id for b in result.blocks]))

    def _ocr(self, doc: UDOMDocument, data: bytes, media_type: str) -> None:
        # OCR (V02_S04): recovery only when native extraction is insufficient. Targeted + flaggable.
        if not self.config.flags.get("ocr", True):
            doc.diagnostics["ocr"] = {"status": "disabled"}
            return
        if media_type.startswith("audio/") or media_type.startswith("video/"):
            doc.diagnostics["ocr"] = {"status": "not_applicable", "media_type": media_type}  # text comes from transcription
            return
        _texty = {"paragraph", "heading", "list", "list_item"}
        has_text = any(b.text for _, b in doc.iter_blocks() if b.type in _texty)
        target_pages: Optional[List[int]] = None
        if media_type.startswith("image/") or not has_text:
            need = True
        else:
            empty = [p.page_number for p in doc.pages
                     if not any(b.text for b in p.blocks if b.type in _texty)]
            need, target_pages = (bool(empty), empty or None)
        if not need:
            doc.diagnostics["ocr"] = {"status": "not_needed"}
            return

        engine = self.ocr_registry.select(media_type)
        if engine is None:
            doc.diagnostics["ocr"] = {"status": "capability_unavailable", "needed": True,
                                      "media_type": media_type}
            rec = doc.diagnostics.setdefault("recovery", {})
            gaps = set(rec.get("capability_gaps", [])) | {"ocr"}
            rec["capability_gaps"] = sorted(gaps)  # honest: we needed OCR and had none
            doc.add_lineage(LineageEvent(stage=Stage.OCR.value, operation="ocr", tool="none"))
            return
        try:
            blocks = engine.recognize(data, media_type, doc.source, pages=target_pages)
        except StageNotImplemented as exc:
            doc.diagnostics["ocr"] = {"status": "staged", "engine": engine.name, "reason": str(exc)}
            doc.add_lineage(LineageEvent(stage=Stage.OCR.value, operation="ocr", tool=engine.name))
            return
        pages = {p.page_number: p for p in doc.pages}
        for blk in blocks:
            page = pages.get(blk.page_number)
            if page is None:
                page = Page(page_number=blk.page_number)
                doc.pages.append(page)
                pages[blk.page_number] = page
            page.blocks.append(blk)
        doc.pages.sort(key=lambda p: p.page_number)
        doc.diagnostics["ocr"] = {"status": "ok", "engine": engine.name, "blocks": len(blocks),
                                  "targeted": bool(target_pages)}
        doc.add_lineage(LineageEvent(stage=Stage.OCR.value, operation="ocr", tool=engine.name,
                                     tool_version=engine.version,
                                     outputs=[b.block_id for b in blocks]))

    def _tables(self, doc: UDOMDocument, data: bytes, media_type: str) -> None:
        # Table Intelligence (V02_S06): a dedicated, replaceable stage. Feature-flaggable.
        if not self.config.flags.get("tables", True):
            doc.diagnostics["tables"] = {"status": "disabled"}
            return
        engine = self.table_registry.select(media_type)
        if engine is None:
            doc.diagnostics["tables"] = {"status": "no_engine", "media_type": media_type}
            return
        table_blocks = engine.extract(data, media_type, doc.source)
        pages = {p.page_number: p for p in doc.pages}
        for blk in table_blocks:
            page = pages.get(blk.page_number)
            if page is None:
                page = Page(page_number=blk.page_number)
                doc.pages.append(page)
                pages[blk.page_number] = page
            page.blocks.append(blk)
        doc.pages.sort(key=lambda p: p.page_number)
        doc.diagnostics["tables"] = {"status": "ok", "engine": engine.name,
                                     "tables": len(table_blocks)}
        doc.add_lineage(LineageEvent(stage=Stage.TABLES.value, operation="extract_tables",
                                     tool=engine.name, tool_version=engine.version,
                                     outputs=[b.block_id for b in table_blocks]))

    def _structure(self, doc: UDOMDocument) -> None:
        # Default reading order = recovered (document) order. Advanced layout models overwrite this.
        for page in doc.pages:
            page.reading_order = [b.block_id for b in page.blocks]
        headings = sum(1 for _, b in doc.iter_blocks() if b.type == "heading")
        doc.diagnostics["structure"] = {"pages": len(doc.pages), "headings": headings}
        doc.add_lineage(LineageEvent(stage=Stage.STRUCTURE.value, operation="reading_order",
                                     tool="docintel.structure"))

    def _govern(self, doc: UDOMDocument) -> None:
        # Roll block confidences up to a document-level value (governance invariant: confidence propagates).
        values = [b.confidence.value for _, b in doc.iter_blocks() if b.confidence]
        doc.confidence = Confidence(value=(sum(values) / len(values) if values else 0.0),
                                    level="document", method="mean_block_confidence")
        doc.add_lineage(LineageEvent(stage=Stage.GOVERNANCE.value, operation="stamp_confidence",
                                     tool="docintel.governance"))

    def _knowledge(self, doc: UDOMDocument) -> None:
        for _, block in doc.iter_blocks():
            if block.text:
                block.text = " ".join(block.text.split())
        doc.properties.update({
            "page_count": len(doc.pages),
            "block_count": sum(len(p.blocks) for p in doc.pages),
            "processed_at": now_iso(),
        })
        doc.diagnostics["retrieval_state"] = retrieval_state(doc)   # visibility != extraction
        doc.add_lineage(LineageEvent(stage=Stage.KNOWLEDGE.value, operation="normalize",
                                     tool="docintel.knowledge"))

    # -- staged (skeleton) ----------------------------------------------
    def recover_parallel(self, *args: Any, **kwargs: Any) -> RecoveryResult:
        """Parallel/targeted multi-parser reconciliation (V02 S04) - filled in during Parser Eval."""
        raise StageNotImplemented("parallel/targeted recovery reconciliation is not yet implemented")
