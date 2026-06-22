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
from .governance import Confidence, Evidence, LineageEvent, Provenance
from .orchestration import (
    CAPABILITIES,
    Parser,
    ParserRegistry,
    Pipeline,
    PipelineConfig,
    RecoveryResult,
    Stage,
    StageNotImplemented,
    default_registry,
    guess_media_type,
)
from .udom import Block, Cell, Page, Source, Table, TextSpan, UDOMDocument, UDOM_VERSION
from .validation import validate

__version__ = "0.1.0"

__all__ = [
    "Pipeline", "PipelineConfig", "Parser", "ParserRegistry", "RecoveryResult", "Stage",
    "StageNotImplemented", "default_registry", "guess_media_type", "CAPABILITIES",
    "UDOMDocument", "Source", "Page", "Block", "Table", "Cell", "TextSpan", "UDOM_VERSION",
    "Provenance", "Confidence", "LineageEvent", "Evidence",
    "build_knowledge_artifact", "build_consumer_artifact", "validate",
    "ChangeClass", "ChangeRecord", "IMPACT_DIMENSIONS", "build_change_record", "validate_change",
    "__version__",
]
