---
name: meeting-classify
description: "Classify a meeting from available evidence (email subject/body, sender role, attendees, calendar event, prior thread) and return the meeting type, intent, and confidence. Use this atom when meeting-classifier or teacher-core needs to determine what kind of meeting is being discussed BEFORE routing or attaching advisories. Do NOT use for meeting prep, agenda creation, or minutes — those are separate atoms/skills."
---

# meeting-classify

Pure classification atom: infers meeting type (IEP, 504, MTSS, parent contact, observation, PD, planning, etc.) and intent (prep, draft, summarize, schedule, compliance) from evidence clues. Does not route or attach advisories.

## Input

```json
{
  "evidence": {
    "email_subject": "IEP Annual Review - [Student Name]",
    "sender_title": "Special Education Case Manager",
    "attendees": ["teacher", "case_manager", "parent", "school_psych"],
    "calendar_event": "IEP Annual Review",
    "prior_thread": "re: IEP documentation"
  }
}
```

## Output

```json
{
  "tool": "meeting-classify",
  "meeting_type": "iep",
  "intent": "compliance",
  "confidence": 0.95,
  "evidence_strength": {"explicit": 5, "role_based": 4, "calendar": 3},
  "minority_report": null,
  "human_review_required": true
}
```

## Do NOT use this atom for
- Meeting prep or agenda creation (use atom-meeting-agenda)
- Meeting minutes or summarization (use atom-meeting-minutes)
- Attaching IEP/504/medical advisories (that is a separate step)
- Routing to a skill (the orchestrator handles routing after classification)

## Pipeline note
Follows `references/method.md` at the Analysis step (classification). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — meeting classification is model-inferred; teacher should verify before compliance actions.
