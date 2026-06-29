#!/usr/bin/env python3
"""Shared router — pick which skill should handle a request (offline, stdlib, data-driven).

Reads the canonical registry (routing.json) so teacher-core AND meeting-classifier route from one
source. Three dispatch modes:

  1. `route()` — top-level skill dispatch (keyword scoring + context signals)
  2. `atom_route()` — direct atom dispatch when the request is a single atomic operation
  3. `infer_atoms()` — given a task context (skill, step, artifact_type, subject, grade),
     return which atoms would add value — used by orchestrators to enrich workflows

Usage:
  python3 shared/routing/router.py --text "make a 3rd grade fractions lesson and a rubric"
  python3 shared/routing/router.py --meeting-type iep_meeting --persona teacher
  python3 shared/routing/router.py --infer-atoms --skill lesson-planner --subject Math --grade 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "routing.json"
ATOMS_REGISTRY = HERE.parent / "atoms" / "atoms.json"


def load_registry(registry: dict | None = None) -> dict:
    return registry or json.loads(REGISTRY.read_text(encoding="utf-8"))


def load_atoms() -> dict:
    if ATOMS_REGISTRY.exists():
        return json.loads(ATOMS_REGISTRY.read_text(encoding="utf-8")).get("atoms", {})
    return {}


def meeting_route(meeting_type: str, persona: str = "teacher", registry: dict | None = None) -> str:
    """meeting_type -> owner skill; observations route to school-administration for evaluator personas."""
    reg = load_registry(registry)
    skill = reg.get("meeting_routes", {}).get(meeting_type, reg.get("fallback", "manual_review"))
    if meeting_type in reg.get("observation_types", []) and persona in reg.get("evaluator_personas", []):
        skill = "school-administration"
    return skill


def score_skills(text: str, registry: dict | None = None) -> dict:
    """Count keyword cue hits per available skill (membership, not frequency)."""
    reg = load_registry(registry)
    text = (text or "").lower()
    scores: dict[str, int] = {}
    for sid, meta in reg.get("skills", {}).items():
        if meta.get("status") != "available":
            continue
        scores[sid] = sum(1 for kw in meta.get("keywords", []) if kw.lower() in text)
    return scores


def _confidence(margin: int, top: int) -> str:
    if top == 0:
        return "low"
    return "high" if margin >= 2 else ("medium" if margin == 1 else "low")


# ---------------------------------------------------------------------------
# Task-context atom inference
# ---------------------------------------------------------------------------

TASK_ATOM_MAP: dict[str, list[dict]] = {
    "lesson-planner": [
        {"atom": "standards-match",   "phase": "planning",     "value": "anchor lesson to verified standards",               "required": True},
        {"atom": "objective-write",   "phase": "planning",     "value": "write measurable objectives from standards",         "required": True},
        {"atom": "misconception",     "phase": "planning",     "value": "anticipate student misconceptions before teaching",  "required": False},
        {"atom": "vocabulary-select", "phase": "planning",     "value": "pre-teach key academic vocabulary",                  "required": False},
        {"atom": "cognitive-rigor",   "phase": "planning",     "value": "verify DOK/Bloom alignment of objectives",           "required": False},
        {"atom": "hook",             "phase": "opening",      "value": "engagement hook to activate prior knowledge",         "required": False},
        {"atom": "warm-up",          "phase": "opening",      "value": "bell-ringer to review prerequisite skills",           "required": False},
        {"atom": "activity-generate", "phase": "instruction",  "value": "generate I-do/we-do/you-do activities",              "required": True},
        {"atom": "worked-example",    "phase": "instruction",  "value": "model problem with step-by-step solution",           "required": False, "condition": {"subject": ["Math", "Science"]}},
        {"atom": "graphic-organizer", "phase": "instruction",  "value": "visual thinking tool for concept organization",      "required": False},
        {"atom": "question-set",      "phase": "instruction",  "value": "discussion or text-dependent questions",             "required": False},
        {"atom": "reading-level",     "phase": "validation",   "value": "verify text is at appropriate grade level",          "required": True},
        {"atom": "differentiate",     "phase": "adaptation",   "value": "adapt for ELL/IEP/gifted/below-grade learners",      "required": True},
        {"atom": "sentence-frame",    "phase": "adaptation",   "value": "language scaffolds for ELL students",                "required": False, "condition": {"has_ell": True}},
        {"atom": "udl-options",       "phase": "adaptation",   "value": "UDL checkpoint options for proactive access",        "required": False},
        {"atom": "quality-check",     "phase": "finalization",  "value": "verify alignment, measurability, differentiation",   "required": True},
    ],
    "assessment-designer": [
        {"atom": "standards-match",       "phase": "planning",     "value": "anchor assessment to verified standards",            "required": True},
        {"atom": "misconception",         "phase": "planning",     "value": "inform distractors with common misconceptions",      "required": True},
        {"atom": "cognitive-rigor",        "phase": "planning",     "value": "ensure DOK spread across items",                     "required": True},
        {"atom": "assessment-item",       "phase": "construction", "value": "generate individual test items",                     "required": True},
        {"atom": "distractor-generate",   "phase": "construction", "value": "create plausible wrong answers from misconceptions", "required": False, "condition": {"item_type": ["multiple_choice", "mc"]}},
        {"atom": "answer-key",            "phase": "construction", "value": "generate scoring guide with rationales",             "required": True},
        {"atom": "rubric-build",          "phase": "construction", "value": "build scoring rubric for constructed-response items","required": False, "condition": {"has_constructed_response": True}},
        {"atom": "reading-level",         "phase": "validation",   "value": "verify item stems don't exceed target reading level","required": True},
        {"atom": "differentiate",         "phase": "adaptation",   "value": "provide accommodated versions",                     "required": True},
        {"atom": "text-leveler",          "phase": "adaptation",   "value": "adjust passage complexity for below-grade readers",  "required": False, "condition": {"has_passage": True}},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify alignment, DOK, reading level",              "required": True},
    ],
    "curriculum-mapping": [
        {"atom": "standards-match",       "phase": "planning",     "value": "pull full standards set for grade/subject",          "required": True},
        {"atom": "standards-crosswalk",   "phase": "planning",     "value": "map standards across frameworks for alignment",      "required": False},
        {"atom": "objective-write",       "phase": "construction", "value": "write unit-level objectives for each unit",          "required": True},
        {"atom": "misconception",         "phase": "construction", "value": "flag conceptual gaps to inform pacing/sequencing",   "required": False},
        {"atom": "vocabulary-select",     "phase": "construction", "value": "identify spiraling academic vocabulary",             "required": False},
        {"atom": "cognitive-rigor",        "phase": "validation",   "value": "verify DOK distribution across the year",            "required": False},
        {"atom": "differentiate",         "phase": "adaptation",   "value": "annotate units with differentiation checkpoints",    "required": True},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify coverage completeness and pacing realism",    "required": True},
    ],
    "special-education-support": [
        {"atom": "standards-match",       "phase": "planning",     "value": "anchor IEP goals to grade-level standards",          "required": True},
        {"atom": "present-levels",        "phase": "documentation","value": "draft PLAAFP from placeholder data points",          "required": True},
        {"atom": "iep-goal",              "phase": "construction", "value": "write measurable annual goals from present levels",  "required": True},
        {"atom": "accommodation-match",   "phase": "construction", "value": "match accommodations to documented barriers",        "required": True},
        {"atom": "progress-monitor-plan", "phase": "construction", "value": "create monitoring schedule with probes",             "required": True},
        {"atom": "sentence-frame",        "phase": "adaptation",   "value": "language scaffolds for ELL students with IEPs",      "required": False, "condition": {"has_ell": True}},
        {"atom": "differentiate",         "phase": "adaptation",   "value": "adapt instructional materials to IEP needs",         "required": True},
        {"atom": "udl-options",           "phase": "adaptation",   "value": "UDL options for proactive access barriers",          "required": False},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify alignment, data policy compliance",           "required": True},
    ],
    "intervention-mtss": [
        {"atom": "standards-match",       "phase": "planning",     "value": "tie target skill to verified standard",              "required": True},
        {"atom": "misconception",         "phase": "planning",     "value": "identify root misconceptions causing the gap",       "required": True},
        {"atom": "intervention-select",   "phase": "construction", "value": "match evidence-based intervention to need and tier", "required": True},
        {"atom": "behavior-strategy",     "phase": "construction", "value": "function-based behavior support if behavior concern","required": False, "condition": {"behavior_concern": True}},
        {"atom": "differentiate",         "phase": "adaptation",   "value": "scaffold intervention materials by tier/group size", "required": True},
        {"atom": "progress-monitor-plan", "phase": "construction", "value": "monitoring schedule with decision rules",            "required": True},
        {"atom": "referral-draft",        "phase": "documentation","value": "draft referral when tier escalation needed",         "required": False, "condition": {"tier_escalation": True}},
        {"atom": "reading-level",         "phase": "validation",   "value": "verify materials at correct instructional level",    "required": True},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify alignment, monitoring, decision rules",       "required": True},
    ],
    "family-communication": [
        {"atom": "parent-comm",           "phase": "construction", "value": "draft the communication",                            "required": True},
        {"atom": "reading-level",         "phase": "validation",   "value": "verify readability for family audience",             "required": True},
        {"atom": "translate-comm",        "phase": "adaptation",   "value": "advisory translation to home language",              "required": False, "condition": {"target_language_specified": True}},
        {"atom": "report-card-comment",   "phase": "construction", "value": "standards-based narrative for report cards",         "required": False, "condition": {"comm_type": ["report_card"]}},
        {"atom": "email-draft",           "phase": "construction", "value": "polished email for staff or vendor communication",   "required": False, "condition": {"comm_type": ["staff_email", "vendor_email"]}},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify no real student data, appropriate tone",      "required": True},
    ],
    "document-intelligence": [
        {"atom": "document-parse",        "phase": "ingestion",    "value": "extract text and structure from raw file",           "required": True},
        {"atom": "govern-artifact",       "phase": "governance",   "value": "attach provenance, lineage, confidence metadata",   "required": True},
        {"atom": "reading-level",         "phase": "validation",   "value": "estimate reading level of extracted text",           "required": True},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify provenance, confidence, no fabrication",      "required": True},
    ],
    "meeting-classifier": [
        {"atom": "meeting-classify",      "phase": "classification","value": "classify meeting type and intent from evidence",    "required": True},
        {"atom": "meeting-agenda",        "phase": "preparation",  "value": "structured agenda from purpose and attendees",       "required": False, "condition": {"intent": ["prep", "schedule"]}},
        {"atom": "meeting-minutes",       "phase": "follow-up",    "value": "structured minutes with action items",               "required": False, "condition": {"intent": ["summarize"]}},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify no fabricated data, proper routing",          "required": True},
    ],
    "school-administration": [
        {"atom": "email-draft",           "phase": "construction", "value": "professional email for staff communication",         "required": False},
        {"atom": "meeting-agenda",        "phase": "construction", "value": "structured meeting agenda for leadership",           "required": False},
        {"atom": "meeting-minutes",       "phase": "follow-up",    "value": "document meeting outcomes and action items",          "required": False},
        {"atom": "reading-level",         "phase": "validation",   "value": "ensure admin docs are readable",                     "required": False},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify observable indicators, no real data",         "required": True},
    ],
    "feed-curator": [
        {"atom": "feed-validate",         "phase": "validation",   "value": "check feed URL liveness and staleness",              "required": True},
        {"atom": "feed-discover",         "phase": "discovery",    "value": "autodiscover RSS/Atom from seed page",               "required": False, "condition": {"seed_url_provided": True}},
        {"atom": "safe-apply",            "phase": "governance",   "value": "classify changes as mechanical vs judgment",         "required": True},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify no fabricated URLs, audit trail",             "required": True},
    ],
    "professional-learning": [
        {"atom": "reading-level",         "phase": "validation",   "value": "verify PD materials are adult-appropriate",          "required": False},
        {"atom": "question-set",          "phase": "construction", "value": "reflection questions for PD sessions",               "required": False},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify objectives, evidence-based practices",        "required": True},
    ],
    "presentation-builder": [
        {"atom": "standards-match",       "phase": "planning",     "value": "anchor slides to verified standards",                "required": True},
        {"atom": "vocabulary-select",     "phase": "planning",     "value": "key terms for vocabulary slides",                    "required": False},
        {"atom": "reading-level",         "phase": "validation",   "value": "verify slide text at appropriate level",             "required": True},
        {"atom": "graphic-organizer",     "phase": "construction", "value": "visual organizer for concept slides",                "required": False},
        {"atom": "differentiate",         "phase": "adaptation",   "value": "adapt slides for diverse learners",                  "required": False},
        {"atom": "quality-check",         "phase": "finalization",  "value": "verify alignment, readability, differentiation",     "required": True},
    ],
}

PHASE_ORDER = ["planning", "documentation", "classification", "discovery", "ingestion",
               "governance", "opening", "construction", "instruction", "preparation",
               "follow-up", "validation", "adaptation", "finalization"]


def infer_atoms(skill: str, context: dict | None = None) -> list[dict]:
    """Given a skill and optional context, return atoms that would add value to the task.

    Context keys (all optional):
      subject, grade, item_type, has_ell, has_constructed_response, has_passage,
      behavior_concern, tier_escalation, target_language_specified, comm_type,
      seed_url_provided, intent

    Returns a list of dicts sorted by phase order, each with:
      atom, phase, value, required, active (whether the condition was met)
    """
    context = context or {}
    mappings = TASK_ATOM_MAP.get(skill, [])
    result = []

    for m in mappings:
        active = True
        cond = m.get("condition")
        if cond:
            for ck, cv in cond.items():
                ctx_val = context.get(ck)
                if isinstance(cv, list):
                    active = ctx_val in cv if ctx_val else False
                elif isinstance(cv, bool):
                    active = bool(ctx_val) == cv
                else:
                    active = ctx_val == cv
                if not active:
                    break

        result.append({
            "atom": m["atom"],
            "phase": m["phase"],
            "value": m["value"],
            "required": m["required"],
            "active": active,
        })

    phase_rank = {p: i for i, p in enumerate(PHASE_ORDER)}
    result.sort(key=lambda r: phase_rank.get(r["phase"], 99))
    return result


def atom_route(text: str, registry: dict | None = None) -> dict | None:
    """Check if the request maps directly to a single atom (bypassing the orchestrator).

    Returns {atom, confidence, keywords_matched} or None if no atom match.
    Only matches when the request is clearly atomic — not a multi-step task.
    """
    reg = load_registry(registry)
    text_lower = (text or "").lower()

    multi_step_signals = [
        "and a", "with a", "plus a", "also make", "also create",
        "full lesson", "full unit", "full assessment", "complete",
        "whole", "entire", "everything for",
    ]
    if any(sig in text_lower for sig in multi_step_signals):
        return None

    best_atom = None
    best_score = 0
    best_keywords: list[str] = []
    for atom_name, meta in reg.get("atom_routes", {}).items():
        if atom_name.startswith("_"):
            continue
        matched = [kw for kw in meta.get("keywords", []) if kw.lower() in text_lower]
        score = len(matched)
        if score > best_score:
            best_atom = atom_name
            best_score = score
            best_keywords = matched

    if best_atom and best_score >= 1:
        conf = "high" if best_score >= 2 else "medium"
        return {"atom": best_atom, "confidence": conf, "keywords_matched": best_keywords,
                "basis": "atom_keyword_match"}
    return None


def route(request: dict, registry: dict | None = None) -> dict:
    """Return {recommended_skill, confidence, alternates, minority_report, basis, scores,
              atom_shortcut, inferred_atoms}.

    request keys (all optional): text, artifact_type, meeting_type, persona, context.
    """
    reg = load_registry(registry)
    fallback = reg.get("fallback", "manual_review")
    persona = request.get("persona", "teacher")

    if request.get("meeting_type"):
        skill = meeting_route(request["meeting_type"], persona, reg)
        atoms = infer_atoms(skill, request.get("context"))
        return {"recommended_skill": skill, "confidence": "high" if skill != fallback else "low",
                "alternates": [], "minority_report": None, "basis": "meeting_type", "scores": {},
                "atom_shortcut": None,
                "inferred_atoms": atoms}

    text = " ".join(str(request.get(k, "")) for k in ("text", "artifact_type")).strip()

    atom_match = atom_route(text, reg)

    scores = score_skills(text, reg)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] == 0:
        return {"recommended_skill": fallback, "confidence": "low", "alternates": [],
                "minority_report": None, "basis": "no_cue", "scores": scores,
                "atom_shortcut": atom_match,
                "inferred_atoms": []}

    (top_skill, top_score) = ranked[0]
    (second_skill, second_score) = ranked[1] if len(ranked) > 1 else (None, 0)
    margin = top_score - second_score
    confidence = _confidence(margin, top_score)
    alternates = [second_skill] if second_skill and second_score > 0 else []

    minority = None
    if second_skill and top_score == second_score:
        minority = {
            "chosen": top_skill, "alternates": [second_skill],
            "why_it_won": f"tie on cue score ({top_score}); chose registry-order winner",
            "what_would_resolve_it": "an explicit artifact type, persona, or one clarifying question",
        }
        confidence = "low"

    atoms = infer_atoms(top_skill, request.get("context"))

    return {"recommended_skill": top_skill, "confidence": confidence, "alternates": alternates,
            "minority_report": minority, "basis": "keyword_cues", "scores": scores,
            "atom_shortcut": atom_match,
            "inferred_atoms": atoms}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Route a request to the right TOS skill (offline).")
    ap.add_argument("--text", default="", help="the request text")
    ap.add_argument("--artifact-type", default="", help="explicit artifact type, if known")
    ap.add_argument("--meeting-type", default=None, help="a classified meeting_type")
    ap.add_argument("--persona", default="teacher")
    ap.add_argument("--infer-atoms", action="store_true",
                    help="show which atoms add value for a given skill+context")
    ap.add_argument("--skill", default=None, help="skill name (for --infer-atoms)")
    ap.add_argument("--subject", default=None)
    ap.add_argument("--grade", default=None)
    a = ap.parse_args(argv)

    if a.infer_atoms:
        skill = a.skill or "lesson-planner"
        ctx = {}
        if a.subject:
            ctx["subject"] = a.subject
        if a.grade:
            ctx["grade"] = a.grade
        atoms = infer_atoms(skill, ctx)
        print(json.dumps({"skill": skill, "context": ctx, "atoms": atoms}, indent=2, ensure_ascii=False))
        return 0

    req = {"text": a.text, "artifact_type": a.artifact_type, "persona": a.persona}
    if a.meeting_type:
        req["meeting_type"] = a.meeting_type
    print(json.dumps(route(req), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
