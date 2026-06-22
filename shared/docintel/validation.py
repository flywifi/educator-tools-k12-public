"""Validation Framework - measure accuracy/governance/reusability objectively.

Canonical contract: shared/docintel/validation-framework.md. Computable metrics return values;
metrics that need a labeled reference set or longitudinal data return status "staged" (honest,
never fabricated). The report feeds `score_summary`; quality-review makes the final decision.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .udom import UDOMDocument

_SCHEMA_PATH = Path(__file__).resolve().parent / "udom.schema.json"
_CORE_STAGES = {"ingestion", "recovery", "structure", "governance", "knowledge_construction"}
_STAGED = {"status": "staged", "value": None}


def provenance_coverage(doc: UDOMDocument) -> float:
    blocks = [b for _, b in doc.iter_blocks()]
    if not blocks:
        return 0.0
    return sum(1 for b in blocks if b.provenance is not None) / len(blocks)


def confidence_coverage(doc: UDOMDocument) -> float:
    blocks = [b for _, b in doc.iter_blocks()]
    if not blocks:
        return 0.0
    return sum(1 for b in blocks if b.confidence is not None) / len(blocks)


def reading_order_ok(doc: UDOMDocument) -> bool:
    """A-002: every page lists each of its block ids exactly once."""
    for page in doc.pages:
        ids = [b.block_id for b in page.blocks]
        if sorted(page.reading_order) != sorted(ids):
            return False
    return True


def lineage_coverage(doc: UDOMDocument) -> float:
    seen = {e.stage for e in doc.lineage}
    return len(_CORE_STAGES & seen) / len(_CORE_STAGES)


def schema_valid(doc: UDOMDocument) -> Dict[str, Any]:
    """Validate the serialized UDOM against udom.schema.json if jsonschema is installed."""
    try:
        import jsonschema  # optional dep
    except Exception:
        return {"status": "skipped", "reason": "jsonschema not installed"}
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc.to_dict(), schema)
        return {"status": "ok", "valid": True}
    except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
        return {"status": "ok", "valid": False, "error": str(exc).splitlines()[0]}


def _table_wellformed(table: Any) -> bool:
    if table is None or table.rows <= 0 or table.cols <= 0:
        return False
    for c in table.cells:
        if c.row < 0 or c.col < 0 or c.row + c.rowspan > table.rows or c.col + c.colspan > table.cols:
            return False
    return True


def table_recovery(doc: UDOMDocument) -> Dict[str, Any]:
    """A-003: count recovered tables and check structural well-formedness."""
    tables = [b for _, b in doc.iter_blocks() if b.type == "table" and b.table is not None]
    if not tables:
        return dict(_STAGED)
    return {
        "status": "computed",
        "tables": len(tables),
        "cells": sum(len(b.table.cells) for b in tables),
        "wellformed": sum(1 for b in tables if _table_wellformed(b.table)),
    }


def artifact_completeness(artifact: Dict[str, Any]) -> float:
    required = ["artifact_id", "artifact_type", "schema_version", "payload",
               "governance", "metadata"]
    present = sum(1 for k in required if artifact.get(k) is not None)
    return present / len(required)


def validate(doc: UDOMDocument, artifact: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Full validation report keyed by metric id (see validation-framework.md)."""
    report: Dict[str, Any] = {
        # Governance
        "G-001_provenance_coverage": round(provenance_coverage(doc), 4),
        "G-002_lineage_coverage": round(lineage_coverage(doc), 4),
        "G-004_confidence_coverage": round(confidence_coverage(doc), 4),
        "G-005_audit_reconstruction": lineage_coverage(doc) >= 1.0,
        # Accuracy
        "A-002_reading_order_ok": reading_order_ok(doc),
        "A-004_metadata_present": bool(doc.properties),
        "A-001_text_recovery": _STAGED,
        "A-003_table_recovery": table_recovery(doc),
        "A-005_structure_recovery": _STAGED,
        # Reusability
        "R-002_consistency": _STAGED,
        "R-004_reprocessing_reduction": _STAGED,
        "R-005_knowledge_preservation": _STAGED,
        # Schema conformance
        "schema": schema_valid(doc),
        # Retrieval state (visibility != extraction)
        "retrieval_state": doc.diagnostics.get("retrieval_state"),
    }
    if artifact is not None:
        report["R-001_artifact_completeness"] = round(artifact_completeness(artifact), 4)
        report["R-003_consumer_independence"] = "payload" in artifact and bool(
            artifact["payload"])

    governance_ok = (report["G-001_provenance_coverage"] >= 1.0
                     and report["G-004_confidence_coverage"] >= 1.0
                     and report["G-005_audit_reconstruction"])
    report["summary"] = {
        "governance_ok": governance_ok,
        "reading_order_ok": report["A-002_reading_order_ok"],
        "note": "Staged metrics need a labeled reference set or longitudinal data; "
                "final Approved/Remediation decision is made by quality-review.",
    }
    return report
