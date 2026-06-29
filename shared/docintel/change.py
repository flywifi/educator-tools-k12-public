"""Change Control for docintel contracts and governed artifacts (from V03_S07).

"Controlled change preserves integrity while uncontrolled change creates uncertainty."
Any modification to an approved artifact contract, the UDOM schema, or a governed artifact is
**classified, evaluated for impact, approved with evidence, and kept traceable** - and may never
bypass governance/review or reduce traceability/integrity (V03_S07 S9). Canonical prose lives in
shared/docintel/artifact-framework.md ("Artifact contract stability").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .governance import new_id, now_iso


class ChangeClass(str, Enum):
    """Change classification (V03_S07 S5)."""
    ADMINISTRATIVE = "administrative"
    PLANNING = "planning"
    GOVERNANCE = "governance"
    ACCEPTANCE = "acceptance"


# Dimensions every change is evaluated against before adoption (V03_S07 S6).
IMPACT_DIMENSIONS = ("scope", "architecture", "acceptance", "governance")

_TERMINAL = {"approved", "rejected"}


@dataclass
class ChangeRecord:
    """A controlled, traceable change to an approved artifact/contract (V03_S07 S7/S8)."""
    title: str
    classification: ChangeClass
    description: str
    impact: Dict[str, str] = field(default_factory=dict)      # dimension -> assessed impact
    decision: Optional[str] = None                            # approved | rejected | deferred
    approval_evidence: Optional[str] = None                   # what justifies the decision
    rationale: Optional[str] = None
    approval_references: List[str] = field(default_factory=list)
    status: str = "proposed"                                  # proposed|evaluated|approved|rejected
    change_id: str = field(default_factory=lambda: new_id("chg"))
    created: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "title": self.title,
            "classification": self.classification.value,
            "description": self.description,
            "impact": self.impact,
            "decision": self.decision,
            "approval_evidence": self.approval_evidence,
            "rationale": self.rationale,
            "approval_references": self.approval_references,
            "status": self.status,
            "created": self.created,
        }


def build_change_record(title: str, classification: ChangeClass, description: str, *,
                        impact: Optional[Dict[str, str]] = None,
                        rationale: Optional[str] = None) -> ChangeRecord:
    """Create a proposed change with every impact dimension accounted for (defaults to 'none')."""
    assessed = {dim: "none" for dim in IMPACT_DIMENSIONS}
    if impact:
        assessed.update({k: v for k, v in impact.items() if k in IMPACT_DIMENSIONS})
    return ChangeRecord(title=title, classification=classification, description=description,
                        impact=assessed, rationale=rationale, status="evaluated")


def validate_change(rec: ChangeRecord) -> Dict[str, Any]:
    """Enforce the V03_S07 S9 constraints: a change may not bypass governance/review or
    reduce traceability/integrity. Returns {valid, violations}."""
    violations: List[str] = []
    # Integrity: must be evaluated for impact on every dimension before adoption (S2, S6).
    missing = [d for d in IMPACT_DIMENSIONS if d not in rec.impact]
    if missing:
        violations.append(f"not evaluated for impact on: {', '.join(missing)}")
    # No bypassing review: cannot jump straight from proposed to approved.
    if rec.status == "approved" and rec.decision != "approved":
        violations.append("approved status without an approval decision (bypasses review)")
    # No bypassing governance: approval requires evidence + an approval reference (S7).
    if rec.decision == "approved":
        if not rec.approval_evidence:
            violations.append("approval requires evidence (no bypassing governance)")
        if not rec.approval_references:
            violations.append("approval requires at least one approval reference (traceability)")
    # Traceability: identifier + rationale + status (S8).
    if not rec.change_id or not rec.rationale:
        violations.append("change must keep an id and rationale (traceability)")
    return {"valid": not violations, "violations": violations}
