"""context engine - resolve a teaching-context contract from district + school-type + SOPs.

The operating-reference pattern, adapted for K-12: classify the operating context FIRST, apply the
school-type exception rule-set, resolve authority precedence + overrides, and emit a context contract
(context.schema.json) that downstream skills consume and carry across handoffs. Stdlib only.

Canonical prose: shared/context/README.md, context-model.md, sop-model.md.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
DISTRICTS_PATH = HERE / "florida-districts.json"
SCHOOL_TYPES_PATH = HERE / "school-types.json"

# Default precedence for MANDATES/compliance: higher authority wins. Instructional-style
# decisions may invert this (classroom discretion); callers can pass a custom order.
DEFAULT_PRECEDENCE = ["state", "district", "school", "classroom"]


def load_districts() -> Dict[str, Any]:
    return json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))


def load_school_types() -> Dict[str, Any]:
    return json.loads(SCHOOL_TYPES_PATH.read_text(encoding="utf-8"))


def find_district(name_or_number) -> Optional[Dict[str, Any]]:
    reg = load_districts()
    for d in reg["districts"]:
        if str(d["fldoe_district_number"]) == str(name_or_number) or \
           d["name"].lower() == str(name_or_number).lower():
            return d
    return None


def school_type_rules(school_type: str) -> Dict[str, Any]:
    """The exception rule-set for a school type: what it overrides vs. the traditional-public baseline."""
    types = load_school_types()["types"]
    return types.get(school_type, {})


def _standards_applicability(school_type: str) -> str:
    rules = school_type_rules(school_type)
    txt = (rules.get("standards_applicability") or "").lower()
    if "not" in txt and "parent" in txt:
        return "parent_selected"
    if "not" in txt or "school selects" in txt or "school-defined" in txt:
        return "school_defined"
    if "apply" in txt:
        return "best_ngsss_apply"
    return "unknown"


def build_context(*, school_type: str = "traditional_public", district: Optional[str] = None,
                  school_name: Optional[str] = None, subject: Optional[str] = None,
                  grade_band: Optional[str] = None, instructional_model: Optional[str] = None,
                  calendar: Optional[str] = None, program: Optional[List[str]] = None,
                  mandates: Optional[List[Dict[str, Any]]] = None,
                  sop_refs: Optional[List[Dict[str, Any]]] = None,
                  precedence: Optional[List[str]] = None) -> Dict[str, Any]:
    """Assemble a context contract. Unknowns are honest nulls; human_review_required is always true."""
    d = find_district(district) if district else None
    rules = school_type_rules(school_type)
    return {
        "context_id": f"ctx-{uuid.uuid4().hex[:12]}",
        "state": "FL",
        "district": {"fldoe_district_number": d["fldoe_district_number"], "name": d["name"]} if d else None,
        "school": {"name": school_name, "type": school_type},
        "school_type": school_type,
        "program": program or ["general"],
        "subject": subject,
        "grade_band": grade_band,
        "instructional_model": instructional_model,
        "calendar": calendar,
        "standards_applicability": _standards_applicability(school_type),
        "mandates": mandates or [],
        "sop_refs": sop_refs or [],
        "authority_precedence": precedence or list(DEFAULT_PRECEDENCE),
        "overrides": [],
        "school_type_exceptions": rules.get("overrides_baseline", []),
        "sop_override_targets": rules.get("sop_overrides", []),
        "resolved_by": "context-engine",
        "confidence": "high" if d or school_type != "traditional_public" else "medium",
        "human_review_required": True,
        "assumptions": [
            "School-type exception rule-set applied from school-types.json (verify on cited sources).",
            "District rules/norms are stubs to be populated per district.",
        ],
    }


def apply_override(context: Dict[str, Any], instruction: str, by: str = "user",
                   effect: Optional[str] = None) -> Dict[str, Any]:
    """Control-plane reset: log an explicit override (prefer/avoid a rule or source)."""
    from datetime import datetime, timezone
    context.setdefault("overrides", []).append({
        "instruction": instruction, "by": by,
        "timestamp": datetime.now(timezone.utc).isoformat(), "effect": effect})
    return context


def resolve_conflict(context: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick the winning rule among candidates by authority precedence (each candidate has a `scope`)."""
    order = {s: i for i, s in enumerate(context.get("authority_precedence", DEFAULT_PRECEDENCE))}
    ranked = sorted((c for c in candidates if c.get("scope") in order),
                    key=lambda c: order[c["scope"]])
    return ranked[0] if ranked else None


def validate_context(context: Dict[str, Any]) -> Dict[str, Any]:
    problems: List[str] = []
    if context.get("state") != "FL":
        problems.append("only FL is populated so far")
    if context.get("school_type") not in load_school_types()["types"]:
        problems.append(f"unknown school_type: {context.get('school_type')}")
    if context.get("human_review_required") is not True:
        problems.append("human_review_required must be true")
    if not context.get("authority_precedence"):
        problems.append("authority_precedence is required")
    return {"valid": not problems, "problems": problems}


if __name__ == "__main__":  # tiny demo
    ctx = build_context(school_type="charter_public", district="Orange", subject="Math",
                        grade_band="6-8", instructional_model="blended")
    apply_override(ctx, "Use the district pacing guide over the school default", by="teacher")
    print(json.dumps({"context": ctx, "validation": validate_context(ctx)}, indent=2))
