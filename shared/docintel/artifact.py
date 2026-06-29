"""Artifact Framework - turn a governed UDOM into durable, consumer-ready artifacts.

Canonical contract: shared/docintel/artifact-framework.md. Every artifact carries the TOS
metadata block (protocols/metadata-schema.md) with `human_review_required: true` and is NOT
certified until it passes quality-review against protocols/quality-gates.md.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .governance import new_id, now_iso
from .udom import UDOMDocument

SCHEMA_VERSION = "0.1.0"


def _metadata_block(doc: UDOMDocument, *, artifact_type: str, persona: str, grade_band: str,
                    subject: str, standards_set: Optional[str],
                    score_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The TOS artifact metadata block (protocols/metadata-schema.md)."""
    return {
        # --- Quality decision record (QG section 93) ---
        "decision_id": new_id("dec"),
        "artifact_id": doc.document_id,
        "reviewer": "document-intelligence (self-check) then quality-review",
        "date": now_iso(),
        "decision": None,                       # set by quality-review; honest until then
        "status": "pending_quality_review",
        "evidence": (f"{doc.properties.get('block_count', 0)} governed blocks; "
                     f"{len(doc.lineage)} lineage events; "
                     f"doc confidence {getattr(doc.confidence, 'value', None)}"),
        "rationale": "Skeleton self-check only; final decision pending Quality Gates.",
        "score_summary": score_summary,
        # --- Education trailer (TOS) ---
        "artifact_type": artifact_type,
        "persona": persona,
        "grade_band": grade_band,
        "subject": subject,
        "standards_set": standards_set,
        "standards_cited": [],
        "differentiation": None,
        "human_review_required": True,          # always - decision support, not a final determination
        "assumptions": ["Media type inferred from file extension when not supplied."],
    }


def build_knowledge_artifact(doc: UDOMDocument, *, persona: str = "platform",
                             grade_band: str = "K-12", subject: str = "(unspecified)",
                             standards_set: Optional[str] = None,
                             score_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The governed, normalized knowledge asset: UDOM + governance + metadata."""
    udom = doc.to_dict()
    return {
        "artifact_id": new_id("art"),
        "artifact_type": "knowledge-artifact",
        "schema_version": SCHEMA_VERSION,
        "readiness": "Draft",
        "payload": {"udom": udom},
        "governance": {
            "provenance": udom["provenance"],
            "lineage_reference": [e["event_id"] for e in udom["lineage"]],
            "document_confidence": udom.get("confidence"),
            "retrieval_state": udom.get("diagnostics", {}).get("retrieval_state"),
        },
        "metadata": _metadata_block(doc, artifact_type="knowledge-artifact", persona=persona,
                                    grade_band=grade_band, subject=subject,
                                    standards_set=standards_set, score_summary=score_summary),
    }


def build_consumer_artifact(knowledge_artifact: Dict[str, Any], *, consumer: str,
                            projection: Callable[[Dict[str, Any]], Any]) -> Dict[str, Any]:
    """A consumer-specific projection derived from the knowledge artifact (never from source)."""
    return {
        "artifact_id": new_id("art"),
        "artifact_type": "consumer-artifact",
        "schema_version": SCHEMA_VERSION,
        "readiness": "Draft",
        "consumer": consumer,
        "derived_from": knowledge_artifact["artifact_id"],
        "payload": projection(knowledge_artifact),
        "governance": knowledge_artifact["governance"],
        "metadata": {**knowledge_artifact["metadata"],
                     "artifact_type": "consumer-artifact",
                     "decision_id": new_id("dec")},
    }
