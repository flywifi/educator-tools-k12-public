#!/usr/bin/env python3
"""Classify a teacher meeting + request intent from compact clues, then route (offline, heuristic).

A first-pass assistant, NOT the source of truth: if it conflicts with stronger document evidence, follow
the evidence (see ../references/evidence-model.md). Reuses shared/connectors (what's available, degrade/
converge) and shared/students (subject student + guardians + signed medical action plan). Emits a
machine-readable classification record incl. an IEP/504 required-cadence advisory, escalation flag, the
connector resilience fields, and a resolver-shaped minority_report on material ambiguity. Stdlib only.

Usage:
  python3 scripts/classify_meeting.py --input <clues.json> [--flags <connector-flags.json>]
  python3 scripts/classify_meeting.py --title "Formal observation" --from-title "Principal" ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared" / "connectors"))
sys.path.insert(0, str(ROOT / "shared" / "students"))
sys.path.insert(0, str(ROOT / "shared"))
try:
    import connectors as conn  # type: ignore
    import students as stu      # type: ignore
except Exception:               # pragma: no cover - engines are optional at runtime
    conn = stu = None
try:
    import docintel             # type: ignore  (uploaded-file ingest: .ics/.eml and more)
except Exception:               # pragma: no cover - docintel is optional at runtime
    docintel = None
sys.path.insert(0, str(ROOT / "shared" / "records"))
try:
    import records             # type: ignore  (emit a shared skill->skill handoff package)
except Exception:             # pragma: no cover - records is optional at runtime
    records = None

TYPE_CUES = {
    "faculty_meeting": ["faculty", "all staff", "whole staff", "staff meeting"],
    "grade_level_meeting": ["grade level", "grade-level", "plc", "team meeting", "grade team"],
    "department_meeting": ["department", "dept", "subject area"],
    "data_meeting": ["data chat", "data meeting", "data dig", "data review", "data analysis"],
    "emergency_meeting": ["emergency", "urgent", "asap", "crisis"],
    "annual_review_observation": ["formal observation", "evaluation", "annual review", "marzano",
                                   "danielson", "observation rubric", "summative", "observation"],
    "annual_review_debrief": ["debrief", "post-observation", "post conference", "post-conference",
                               "feedback meeting"],
    "interim_observation": ["walkthrough", "walk-through", "drop-in", "drop in", "informal observation",
                             "mini observation", "learning walk", "informal", "observation"],
    "parent_teacher_conference": ["parent-teacher conference", "parent teacher conference",
                                   "parent conference", "conference about"],
    "parent_contact": ["call home", "call the parent", "contact the parent", "phone call home",
                        "reach out to the parent", "call mom", "call dad", "guardian call"],
    "iep_meeting": ["iep", "individualized education"],
    "section_504_meeting": ["504"],
    "health_plan_meeting": ["health plan", "medical plan", "anaphylaxis", "allergy", "seizure",
                             "diabetes", "asthma", "epipen", "epinephrine", "action plan"],
    "mtss_meeting": ["mtss", "rti", "problem solving", "problem-solving", "tier 2", "tier 3",
                      "student support team", "intervention plan"],
    "pre_planning": ["pre-planning", "pre planning", "preplanning"],
    "planning_period": ["planning period", "common planning", "lesson planning", "plan time"],
    "post_planning": ["post-planning", "post planning", "postplanning"],
    "professional_development": ["professional development", "in-service", "inservice", "workshop",
                                  "training on", " pd "],
    "safety_training": ["safety training", "fire drill", "active shooter", "active threat", "lockdown",
                         "bloodborne", "mandated training", "code red", "drill"],
    "special_event_meeting": ["field trip", "open house", "performance", "event planning", "fundraiser",
                               "spirit week", "graduation ceremony"],
}
# Sender/attendee role -> (meeting_type, weight)
ROLE_CUES = {
    "principal": [("annual_review_observation", 2), ("faculty_meeting", 1)],
    "assistant principal": [("annual_review_observation", 2), ("faculty_meeting", 1)],
    "case manager": [("iep_meeting", 3)], "staffing": [("iep_meeting", 3)],
    "lea": [("iep_meeting", 3)], "ese": [("iep_meeting", 2)],
    "504 coordinator": [("section_504_meeting", 3)],
    "nurse": [("health_plan_meeting", 3)],
    "counselor": [("mtss_meeting", 1), ("section_504_meeting", 1)],
    "parent": [("parent_teacher_conference", 2), ("parent_contact", 1)],
    "guardian": [("parent_teacher_conference", 2), ("parent_contact", 1)],
    "instructional coach": [("professional_development", 1), ("interim_observation", 1)],
}
INTENT_CUES = {
    "prep_for_meeting": ["prepare", "what should i bring", "agenda for", "talking points", "get ready",
                          "what to expect", "prep for"],
    "draft_communication": ["draft", "email", "invite", "reminder", "follow up", "follow-up", "recap",
                             "send", "call script", "what to say", "write to", "call home",
                             "call the parent", "reach out", "phone call"],
    "summarize_or_minutes": ["minutes", "summarize", "what changed", "action items", "take notes",
                              "notes from"],
    "identify_required_attendees": ["who should attend", "who needs to be there", "required attendees",
                                     "who to invite", "who must attend"],
    "schedule_or_triage": ["today's meetings", "todays meetings", "meetings today", "my schedule",
                            "prioritize", "what do i have"],
    "documentation_or_compliance": ["form", "documentation", "sign-in", "required form", "paperwork",
                                     "compliance"],
    "extract_artifact_only": ["read this", "extract", "open this", "what's in this", "attachment"],
}
ROUTING = {
    "parent_teacher_conference": "family-communication", "parent_contact": "family-communication",
    "health_plan_meeting": "family-communication",
    "iep_meeting": "special-education-support", "section_504_meeting": "special-education-support",
    "mtss_meeting": "intervention-mtss", "data_meeting": "intervention-mtss",
    "annual_review_observation": "professional-learning", "interim_observation": "professional-learning",
    "annual_review_debrief": "professional-learning",
    "faculty_meeting": "professional-learning", "department_meeting": "professional-learning",
    "grade_level_meeting": "professional-learning", "professional_development": "professional-learning",
    "pre_planning": "curriculum-mapping", "post_planning": "curriculum-mapping",
    "planning_period": "lesson-planner",
    "safety_training": "manual_review", "special_event_meeting": "manual_review",
    "other": "manual_review", "unknown": "manual_review",
}
MEDICAL_TERMS = ["medical", "anaphylaxis", "allergy", "allergic", "epipen", "epinephrine", "seizure",
                 "diabetes", "asthma", "health", "injury", "sick", "nurse"]
ESCALATE_TYPES = {"iep_meeting", "section_504_meeting", "health_plan_meeting"}


def join_text(d: dict) -> str:
    parts = [str(d.get(k, "")) for k in ("title", "subject", "body", "from_name", "from_title",
                                          "notes", "transcript", "user_request")]
    parts += [" ".join(d.get("attendees", []) or []), " ".join(d.get("file_names", []) or [])]
    cal = d.get("calendar")
    if isinstance(cal, dict):
        parts.append(" ".join(str(v) for v in cal.values()))
    elif cal:
        parts.append(str(cal))
    return ("\n".join(p for p in parts if p)).lower()


def score_types(d: dict, text: str) -> dict:
    scores = {k: 0 for k in TYPE_CUES}
    for label, cues in TYPE_CUES.items():
        for c in cues:
            if c in text:
                scores[label] += 2
    role_text = (str(d.get("from_title", "")) + " " + " ".join(d.get("attendees", []) or [])).lower()
    for role, hits in ROLE_CUES.items():
        if role in role_text:
            for label, w in hits:
                scores[label] += w
    return scores


def score_intent(text: str) -> dict:
    scores = {k: 0 for k in INTENT_CUES}
    for label, cues in INTENT_CUES.items():
        for c in cues:
            if c in text:
                scores[label] += 2
    return scores


def top_two(scores: dict):
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ordered[0], ordered[1]


def connector_plan(flags: dict) -> dict:
    if conn is None:
        return {"states": {}, "active": [], "evidence_chain": {}, "gaps": []}
    return conn.resolve(flags)


def resolve_student(d: dict):
    ref = d.get("student_ref")
    if not ref or stu is None:
        return None
    store, _ = stu.load_store()
    return stu.find(store, str(ref))


def build_minority_report(top, second, scores) -> dict:
    return {
        "chosen_interpretation": top[0],
        "alternates": [second[0]],
        "why_it_won": f"highest cue score ({top[1]} vs {second[1]}) on the available evidence",
        "residual_uncertainty": {
            "what_would_resolve_it": "corroborating evidence (organizer role, attendee roster, an "
            "evaluation rubric vs a walkthrough note, or an explicit statement) would separate "
            f"'{top[0]}' from '{second[0]}'"
        },
    }


def apply_file_evidence(d: dict, paths: list) -> list:
    """Ingest uploaded files (.ics/.eml or any docintel-readable doc) and fold the normalized evidence
    into the clue dict, so a dropped calendar invite / saved email is read instead of retyped. Returns
    execution_trace notes; honest about missing files or an unavailable engine. Explicit clue fields
    already set by the user are never overwritten (the user statement outranks a file)."""
    notes: list = []
    if not paths:
        return notes
    if docintel is None:
        return [{"event": "file_ingest_unavailable", "class": "UNSUPPORTED",
                 "detail": "docintel engine not importable; --file inputs skipped"}]
    pipeline = docintel.Pipeline()
    recovered_text: list = []
    for p in paths:
        path = Path(p)
        if not path.exists() and not path.is_absolute() and (ROOT / p).exists():
            path = ROOT / p
        if not path.exists():
            notes.append({"event": "file_missing", "class": "NOT_FOUND", "detail": f"{p} not found"})
            continue
        doc = pipeline.run(path.read_bytes(), str(path))
        rec = doc.diagnostics.get("recovery", {})
        names = d.setdefault("file_names", [])
        if path.name not in names:
            names.append(path.name)
        for ev in rec.get("events", []) or []:
            cal = d.setdefault("calendar", {})
            if isinstance(cal, dict):
                for k in ("summary", "start", "end", "location", "organizer"):
                    if ev.get(k) and k not in cal:
                        cal[k] = ev[k]
            for a in ev.get("attendees", []) or []:
                if a not in d.setdefault("attendees", []):
                    d["attendees"].append(a)
            if ev.get("summary") and not d.get("title"):
                d["title"] = ev["summary"]
            notes.append({"event": "file_ingested", "source": "uploaded_file", "class": "SUCCESS",
                          "detail": f"calendar event '{ev.get('summary', '')}' from {path.name}"})
        em = rec.get("email")
        if em:
            for key in ("subject", "from_name", "from_domain"):
                if em.get(key) and not d.get(key):
                    d[key] = em[key]
            for att in em.get("attachments", []) or []:
                if att not in names:
                    names.append(att)
            notes.append({"event": "file_ingested", "source": "uploaded_file", "class": "SUCCESS",
                          "detail": f"email '{em.get('subject', '')}' from {path.name}"})
        text = " ".join(b.text for _, b in doc.iter_blocks() if b.text)
        if text:
            recovered_text.append(text)
        if not (rec.get("events") or em):
            notes.append({"event": "file_ingested", "source": "uploaded_file", "class": "SUCCESS",
                          "detail": f"{rec.get('parser', '?')} document {path.name}"})
    if recovered_text:
        d["body"] = (str(d.get("body", "")) + "\n" + "\n".join(recovered_text)).strip()
    return notes


def classify(d: dict, flags: dict | None = None, emit_package: bool = False) -> dict:
    flags = flags or d.get("connector_flags") or {}
    emit_package = emit_package or bool(d.pop("emit_package", False))
    file_trace = apply_file_evidence(d, d.pop("files", []) or [])
    text = join_text(d)
    tscores, iscores = score_types(d, text), score_intent(text)
    (t1, t1s), (t2, t2s) = top_two(tscores)
    (i1, i1s), _ = top_two(iscores)

    if t1s == 0:
        meeting_type, confidence = "unknown", "low"
    elif t1s == t2s or (t1s - t2s) <= 1 and t2s >= 2:
        meeting_type, confidence = t1, "low"
    else:
        meeting_type = t1
        confidence = "high" if (t1s - t2s) >= 3 else "medium"
    request_intent = i1 if i1s > 0 else "unknown"

    plan = connector_plan(flags)
    sources_unavailable = [c for c, s in plan["states"].items() if s != "available"]
    restricted_notes = plan.get("restricted_notes", [])
    degraded = bool(plan.get("gaps")) or bool(restricted_notes) or any(
        s in ("disabled", "permission_blocked", "not_installed") for s in plan["states"].values())
    execution_trace = list(file_trace)
    if degraded:
        execution_trace.append({"event": "degraded_path", "class": "DEGRADED_SUCCESS",
                                "detail": "one or more sources off/blocked/restricted; converged on available evidence; confidence lowered"})
    for n in restricted_notes:
        dest = ", ".join(n.get("fell_back_to") or []) or "no other provider (gap)"
        execution_trace.append({"event": "restricted_source", "class": n.get("failure_class", "PERMISSION"),
                                "detail": f"{n['connector']} restricted from {n['evidence']} "
                                          f"({n['reason']}); looking elsewhere: {dest}"})

    medical = any(m in text for m in MEDICAL_TERMS) or meeting_type == "health_plan_meeting"
    student = resolve_student(d)
    mode = (flags.get("student_identification") or {}).get("mode", "name")
    subject_student = guardians = medical_action_plan = None
    if student is not None and stu is not None:
        subject_student = stu.render_ref(student, mode)
        guardians = student.get("guardians") if mode != "id" else f"{len(student.get('guardians', []))} on file (hidden in id mode)"
        if medical and student.get("health_plans"):
            medical_action_plan = {"safety_critical": True, "surface_from": "the source on file (attributed; a signature is not required) — never fabricate; defer to nurse/911",
                                    "plans": student["health_plans"]}

    required_cadence = None
    if meeting_type == "iep_meeting":
        required_cadence = {"required": True, "authority": "IDEA",
                            "rule": "an existing IEP is reviewed at least annually (reeval at least every 3 years)",
                            "verify_on_source": True}
    elif meeting_type == "section_504_meeting":
        required_cadence = {"required": True, "authority": "Section 504",
                            "rule": "an existing 504 plan is reviewed periodically (commonly annual; districts vary)",
                            "verify_on_source": True}

    escalate = meeting_type in ESCALATE_TYPES or (meeting_type == "parent_contact" and medical)

    # Routing (persona-aware for observations)
    persona = d.get("persona", "teacher")
    next_skill = ROUTING.get(meeting_type, "manual_review")
    if meeting_type in ("annual_review_observation", "interim_observation", "annual_review_debrief") \
            and persona in ("administrator", "evaluator", "principal"):
        next_skill = "school-administration"
    if meeting_type == "unknown" or confidence == "low" and t1s == 0:
        next_skill = "manual_review"

    minority = None
    if t1s > 0 and (t1s == t2s or (t1s - t2s) <= 1 and t2s >= 2):
        minority = build_minority_report((t1, t1s), (t2, t2s), tscores)

    reasons = [f"top meeting cue '{t1}' scored {t1s}"]
    if d.get("from_title"):
        reasons.append(f"sender title: {d['from_title']}")
    missing = []
    if not d.get("attendees"):
        missing.append("attendee roster")
    if not (d.get("calendar") or d.get("transcript") or d.get("body")):
        missing.append("calendar event / body / transcript")

    result = {
        "meeting_type": meeting_type,
        "request_intent": request_intent,
        "confidence": confidence,
        "persona": persona,
        "subject_student": subject_student,
        "guardians": guardians,
        "medical_action_plan": medical_action_plan,
        "required_cadence": required_cadence,
        "recommended_next_skill": next_skill,
        "escalate_to_human": escalate,
        "source_availability": plan["states"],
        "sources_unavailable": sources_unavailable,
        "restricted_sources": plan.get("restrictions", {}),
        "degraded": degraded,
        "convergence_path": plan.get("evidence_chain", {}),
        "execution_trace": execution_trace,
        "reasons": reasons,
        "missing_evidence": missing,
        "minority_report": minority,
        "human_review_required": True,
        "scores": {"meeting_type": tscores, "request_intent": iscores},
    }
    # Emit the shared skill->skill handoff package (records engine) so the next skill gets a
    # consistent, governed record instead of an ad-hoc packet.
    if emit_package and records is not None and d.get("student_ref"):
        mode = (flags.get("student_identification") or {}).get("mode", "name")
        try:
            result["handoff_package"] = records.build_package(
                "skill_to_skill", str(d["student_ref"]), mode=mode,
                modules=records.resolve_modules(flags, None), flags=flags, next_skill=next_skill)
        except Exception as exc:  # pragma: no cover - records is best-effort here
            result["handoff_package_error"] = str(exc)
    return result


def parse_args():
    ap = argparse.ArgumentParser(description="Classify a teacher meeting + intent (offline heuristic).")
    ap.add_argument("--input", help="path to a JSON file with clues")
    ap.add_argument("--flags", help="path to a connector feature-flags JSON")
    for f in ("title", "subject", "body", "from-name", "from-title", "from-domain", "notes",
              "transcript", "user-request", "student-ref", "persona"):
        ap.add_argument(f"--{f}", default=None)
    ap.add_argument("--attendee", action="append", dest="attendees", default=[])
    ap.add_argument("--file-name", action="append", dest="file_names", default=[])
    ap.add_argument("--file", action="append", dest="files", default=[],
                    help="uploaded .ics/.eml (or other docintel-readable) file to ingest")
    ap.add_argument("--emit-package", action="store_true", dest="emit_package",
                    help="also emit the shared skill->skill handoff package (shared/records/)")
    return ap.parse_args()


def main() -> int:
    a = parse_args()
    flags = json.loads(Path(a.flags).read_text(encoding="utf-8")) if a.flags else {}
    if a.input:
        data = json.loads(Path(a.input).read_text(encoding="utf-8"))
    else:
        data = {k: v for k, v in {
            "title": a.title, "subject": a.subject, "body": a.body, "from_name": a.from_name,
            "from_title": a.from_title, "from_domain": a.from_domain, "notes": a.notes,
            "transcript": a.transcript, "user_request": a.user_request, "student_ref": a.student_ref,
            "persona": a.persona, "attendees": a.attendees, "file_names": a.file_names,
        }.items() if v not in (None, [], "")}
    if a.files:
        data["files"] = list(data.get("files", []) or []) + a.files
    print(json.dumps(classify(data, flags, emit_package=a.emit_package), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
