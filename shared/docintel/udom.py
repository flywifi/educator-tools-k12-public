"""UDOM - Unified Document Object Model (parser-independent document representation).

Canonical prose: shared/docintel/udom.md. Machine contract: shared/docintel/udom.schema.json.
`UDOMDocument.to_dict()` serializes to a structure that validates against that schema.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .governance import Confidence, LineageEvent, Provenance

UDOM_VERSION = "0.1.0"

BLOCK_TYPES = {
    "heading", "paragraph", "list", "list_item", "table", "figure",
    "caption", "header", "footer", "formula", "page_number", "other",
}


@dataclass
class Source:
    filename: str
    media_type: str
    sha256: Optional[str] = None
    byte_length: Optional[int] = None


@dataclass
class TextSpan:
    text: str
    bbox: Optional[List[float]] = None
    confidence: Optional[Confidence] = None


@dataclass
class Cell:
    row: int
    col: int
    text: str
    rowspan: int = 1
    colspan: int = 1
    bbox: Optional[List[float]] = None
    confidence: Optional[Confidence] = None


@dataclass
class Table:
    rows: int
    cols: int
    cells: List[Cell] = field(default_factory=list)
    header_rows: int = 0


@dataclass
class Block:
    block_id: str
    type: str
    page_number: int
    provenance: Provenance
    confidence: Confidence
    bbox: Optional[List[float]] = None
    text: Optional[str] = None
    level: Optional[int] = None
    spans: List[TextSpan] = field(default_factory=list)
    table: Optional[Table] = None


@dataclass
class Page:
    page_number: int
    blocks: List[Block] = field(default_factory=list)
    reading_order: List[str] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class UDOMDocument:
    document_id: str
    source: Source
    provenance: Provenance
    pages: List[Page] = field(default_factory=list)
    lineage: List[LineageEvent] = field(default_factory=list)
    confidence: Optional[Confidence] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    udom_version: str = UDOM_VERSION

    # -- mutation helpers -------------------------------------------------
    def add_lineage(self, event: LineageEvent) -> None:
        """Append-only: lineage is never rewritten (governance invariant 2)."""
        self.lineage.append(event)

    def iter_blocks(self) -> Iterator[Tuple[Page, Block]]:
        for page in self.pages:
            for block in page.blocks:
                yield page, block

    # -- serialization ----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "udom_version": self.udom_version,
            "document_id": self.document_id,
            "source": asdict(self.source),
            "properties": self.properties,
            "provenance": asdict(self.provenance),
            "lineage": [asdict(e) for e in self.lineage],
            "confidence": asdict(self.confidence) if self.confidence else None,
            "diagnostics": self.diagnostics,
            "pages": [asdict(p) for p in self.pages],
        }
