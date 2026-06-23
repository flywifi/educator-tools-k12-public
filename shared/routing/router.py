#!/usr/bin/env python3
"""Shared router — pick which skill should handle a request (offline, stdlib, data-driven).

Reads the canonical registry (routing.json) so teacher-core AND meeting-classifier route from one
source. `route()` scores a request and returns the recommended skill + confidence + alternates and,
on a tie, a minority report (never a silent guess). `meeting_route()` maps a classified meeting_type
to its owner skill (persona-aware for observations). Supports multi-hop: a skill that discovers it
needs another skill simply calls `route()` again. No network.

Usage:
  python3 shared/routing/router.py --text "make a 3rd grade fractions lesson and a rubric"
  python3 shared/routing/router.py --meeting-type iep_meeting --persona teacher
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "routing.json"


def load_registry(registry: dict | None = None) -> dict:
    return registry or json.loads(REGISTRY.read_text(encoding="utf-8"))


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


def route(request: dict, registry: dict | None = None) -> dict:
    """Return {recommended_skill, confidence, alternates, minority_report, basis, scores}.

    request keys (all optional): text, artifact_type, meeting_type, persona.
    """
    reg = load_registry(registry)
    fallback = reg.get("fallback", "manual_review")
    persona = request.get("persona", "teacher")

    # Meeting classification is an explicit, high-signal basis.
    if request.get("meeting_type"):
        skill = meeting_route(request["meeting_type"], persona, reg)
        return {"recommended_skill": skill, "confidence": "high" if skill != fallback else "low",
                "alternates": [], "minority_report": None, "basis": "meeting_type", "scores": {}}

    text = " ".join(str(request.get(k, "")) for k in ("text", "artifact_type")).strip()
    scores = score_skills(text, reg)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] == 0:
        return {"recommended_skill": fallback, "confidence": "low", "alternates": [],
                "minority_report": None, "basis": "no_cue", "scores": scores}

    (top_skill, top_score) = ranked[0]
    (second_skill, second_score) = ranked[1] if len(ranked) > 1 else (None, 0)
    margin = top_score - second_score
    confidence = _confidence(margin, top_score)
    alternates = [second_skill] if second_skill and second_score > 0 else []

    minority = None
    if second_skill and top_score == second_score:  # genuine tie -> don't bury the disagreement
        minority = {
            "chosen": top_skill, "alternates": [second_skill],
            "why_it_won": f"tie on cue score ({top_score}); chose registry-order winner",
            "what_would_resolve_it": "an explicit artifact type, persona, or one clarifying question",
        }
        confidence = "low"

    return {"recommended_skill": top_skill, "confidence": confidence, "alternates": alternates,
            "minority_report": minority, "basis": "keyword_cues", "scores": scores}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Route a request to the right TOS skill (offline).")
    ap.add_argument("--text", default="", help="the request text")
    ap.add_argument("--artifact-type", default="", help="explicit artifact type, if known")
    ap.add_argument("--meeting-type", default=None, help="a classified meeting_type")
    ap.add_argument("--persona", default="teacher")
    a = ap.parse_args(argv)
    req = {"text": a.text, "artifact_type": a.artifact_type, "persona": a.persona}
    if a.meeting_type:
        req["meeting_type"] = a.meeting_type
    print(json.dumps(route(req), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
