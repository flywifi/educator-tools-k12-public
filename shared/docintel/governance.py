"""Governance records for docintel: provenance, lineage, confidence, evidence.

Canonical contract: shared/docintel/governance-contract.md. These objects travel with every
UDOM object so that decisions are traceable, auditable, and reconstructable (Principle 2 & 3).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def now_iso() -> str:
    """UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class Provenance:
    """Where an object came from. Attached to every recovered object."""
    source_id: str
    parser: str
    extraction_method: str = "native"  # native | ocr | heuristic | manual
    parser_version: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None
    timestamp: str = field(default_factory=now_iso)


@dataclass
class Confidence:
    """How sure we are, at the granularity it was produced."""
    value: float                       # 0.0 - 1.0
    level: str = "text"                # text | page | document
    method: Optional[str] = None       # how the value was derived (explainable)


@dataclass
class LineageEvent:
    """One transformation in the append-only processing history."""
    stage: str
    operation: str
    tool: str
    tool_version: Optional[str] = None
    event_id: str = field(default_factory=lambda: new_id("ev"))
    timestamp: str = field(default_factory=now_iso)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class Evidence:
    """A back-reference from an extracted fact to the source location proving it."""
    page: Optional[int] = None
    bbox: Optional[List[float]] = None
    char_range: Optional[List[int]] = None
