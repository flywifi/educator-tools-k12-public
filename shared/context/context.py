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
OVERLAYS_DIR = HERE / "overlays"

# Default precedence for MANDATES/compliance: higher authority wins, then more-specific scopes.
# Highest authority FIRST: state > district > county > school > grade (individual) > grade_band >
# subject > department > framework > course (CPALMS #) > course_level > program > classroom/teacher;
# national is the baseline. Instructional-style decisions may invert toward the classroom; pass a
# custom order. (`department` = an org unit within a school, e.g., the HS math department.)
_PRECEDENCE_ORDER = ["state", "district", "county", "school", "grade", "grade_band", "subject",
                     "department", "framework", "course", "course_level", "program", "classroom",
                     "national"]
DEFAULT_PRECEDENCE = list(_PRECEDENCE_ORDER)

# Overlay merge rank: higher = applied later = wins on `overrides`. Inverse of the precedence order
# (state highest, national baseline lowest). Per-overlay `precedence` overrides this.
SCOPE_RANK = {scope: len(_PRECEDENCE_ORDER) - i for i, scope in enumerate(_PRECEDENCE_ORDER)}

# Individual grade level always matters (8th grade tests/standards differ from 6th/7th); bands are a
# convenience derived from it.
GRADE_TO_BAND = {**{g: "K-2" for g in ("K", "1", "2")}, **{g: "3-5" for g in ("3", "4", "5")},
                 **{g: "6-8" for g in ("6", "7", "8")},
                 **{g: "9-12" for g in ("9", "10", "11", "12")}}


def grade_to_band(grade) -> Optional[str]:
    return GRADE_TO_BAND.get(str(grade).strip().upper()) if grade not in (None, "") else None


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
                  grade: Optional[str] = None, grade_band: Optional[str] = None,
                  course: Optional[str] = None, course_level: Optional[str] = None,
                  instructional_model: Optional[str] = None,
                  calendar: Optional[str] = None, program: Optional[List[str]] = None,
                  mandates: Optional[List[Dict[str, Any]]] = None,
                  sop_refs: Optional[List[Dict[str, Any]]] = None,
                  precedence: Optional[List[str]] = None) -> Dict[str, Any]:
    """Assemble a context contract. Unknowns are honest nulls; human_review_required is always true.

    `grade` is the individual grade level (K, 1..12) and always matters — 8th grade standards/testing
    differ from 6th/7th. `grade_band` is a convenience derived from `grade` when not given explicitly.
    `course` is a CPALMS/Course-Code-Directory number; `course_level` is the level enum
    (remedial/standard/advanced/gifted/honors/ap/ib/aice/dual_enrollment).
    """
    d = find_district(district) if district else None
    rules = school_type_rules(school_type)
    grade = str(grade).strip() if grade not in (None, "") else None
    band = grade_band or grade_to_band(grade)
    return {
        "context_id": f"ctx-{uuid.uuid4().hex[:12]}",
        "state": "FL",
        "district": {"fldoe_district_number": d["fldoe_district_number"], "name": d["name"]} if d else None,
        "school": {"name": school_name, "type": school_type},
        "school_type": school_type,
        "program": program or ["general"],
        "subject": subject,
        "grade": grade,
        "grade_band": band,
        "course": course,
        "course_level": course_level,
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


def load_overlays() -> List[Dict[str, Any]]:
    """Load every overlay JSON under overlays/ (any scope). Stored offline; filled in over time."""
    out: List[Dict[str, Any]] = []
    if OVERLAYS_DIR.exists():
        for f in sorted(OVERLAYS_DIR.rglob("*.json")):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
    return out


def _matches(match: Optional[Dict[str, Any]], selectors: Dict[str, Any]) -> bool:
    for k, v in (match or {}).items():
        sv = selectors.get(k)
        if isinstance(v, str) and isinstance(sv, str):
            if v.lower() != sv.lower():
                return False
        elif sv != v:
            return False
    return True


def _rank(ov: Dict[str, Any]) -> int:
    p = ov.get("precedence")
    return p if isinstance(p, int) else SCOPE_RANK.get(ov.get("scope"), 50)


def resolve(selectors: Optional[Dict[str, Any]] = None, **kw) -> Dict[str, Any]:
    """Resolve a full context by stacking matching OVERLAYS onto the base context contract.

    Selectors may include: school_type, district, county, school_name, framework, subject,
    grade, grade_band, course, course_level, instructional_model, calendar, program, precedence.
    Overlays whose `match` is a subset of the selectors are merged in precedence order
    (sets = defaults; adds = accumulate; overrides = highest precedence wins). Records
    `overlays_applied`.
    """
    selectors = {**(selectors or {}), **kw}
    ctx = build_context(
        school_type=selectors.get("school_type", "traditional_public"),
        district=selectors.get("district"), school_name=selectors.get("school_name"),
        subject=selectors.get("subject"), grade=selectors.get("grade"),
        grade_band=selectors.get("grade_band"), course=selectors.get("course"),
        course_level=selectors.get("course_level"),
        instructional_model=selectors.get("instructional_model"),
        calendar=selectors.get("calendar"), program=selectors.get("program"),
        precedence=selectors.get("precedence"))
    if selectors.get("framework"):
        ctx["framework"] = selectors["framework"]
    if selectors.get("county"):
        ctx["county"] = selectors["county"]

    sel = {**selectors, "state": ctx["state"], "school_type": ctx["school_type"],
           "subject": ctx.get("subject"), "grade": ctx.get("grade"),
           "grade_band": ctx.get("grade_band"), "course": ctx.get("course"),
           "course_level": ctx.get("course_level"),
           "district": (ctx["district"]["name"] if ctx.get("district") else selectors.get("district"))}
    applied: List[Dict[str, Any]] = []
    for ov in sorted(load_overlays(), key=_rank):
        if not _matches(ov.get("match", {}), sel):
            continue
        for k, v in (ov.get("sets") or {}).items():
            if ctx.get(k) in (None, [], "", {}):
                ctx[k] = v
        for k, v in (ov.get("overrides") or {}).items():
            ctx[k] = v
        for k, v in (ov.get("adds") or {}).items():
            cur = ctx.setdefault(k, [])
            if isinstance(cur, list) and isinstance(v, list):
                cur.extend(v)
        applied.append({"id": ov.get("id"), "scope": ov.get("scope"), "precedence": _rank(ov)})
    ctx["overlays_applied"] = applied
    return ctx


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


if __name__ == "__main__":  # demo: stacked overlay resolution
    # grade="8" is carried individually (8th-grade testing/standards differ from 6/7) and the band
    # 6-8 is derived from it; course/course_level model a specific CPALMS course at a level.
    ctx = resolve(school_type="charter_public", district="Orange", framework="IB",
                  subject="Mathematics", grade="8", course="1205070", course_level="advanced",
                  instructional_model="blended")
    apply_override(ctx, "Use the district pacing guide over the school default", by="teacher")
    print(json.dumps({
        "school_type": ctx["school_type"],
        "district": ctx["district"],
        "framework": ctx.get("framework"),
        "grade": ctx["grade"],
        "grade_band": ctx["grade_band"],
        "course": ctx["course"],
        "course_level": ctx["course_level"],
        "standards_applicability": ctx["standards_applicability"],
        "overlays_applied": ctx["overlays_applied"],
        "notes": ctx.get("notes", []),
        "validation": validate_context(ctx),
    }, indent=2))
