# Meeting taxonomy + routing (meeting-classifier)

Classify into exactly **one** meeting type and **one** request intent. Prefer `unknown` over a forced
label; emit a minority report when two types are materially plausible (`evidence-model.md`).

## Meeting types (cues)
- **faculty_meeting** — whole-staff; organizer = principal/AP; recurring schoolwide.
- **grade_level_meeting** — a grade team / PLC; attendees share a grade; "PLC", "team meeting".
- **department_meeting** — a subject department (ties to the `department` context scope); "dept", chair.
- **data_meeting** — data chat / data PLC; assessment data, progress monitoring (intervention data →
  also consider mtss_meeting).
- **emergency_meeting** — urgent/crisis/safety; "emergency", "ASAP", crisis-team language.
- **annual_review_observation** — a **formal evaluation** observation of the teacher; evaluator =
  principal/AP; rubric (e.g., Marzano/Danielson); "formal observation", "evaluation".
- **annual_review_debrief** — the **post-observation conference**; "debrief", "post-conference",
  "feedback meeting" after an observation.
- **interim_observation** — informal/walkthrough/mini-observation; "walkthrough", "drop-in", "informal".
- **parent_teacher_conference** — scheduled family conference about a student's progress.
- **parent_contact** — a call/email home (discipline or **medical** issue); often teacher-initiated.
- **iep_meeting** — IEP team meeting (annual review, eligibility, amendment); attendees incl. case
  manager / LEA rep / staffing specialist.
- **section_504_meeting** — 504 plan meeting; 504 coordinator / counselor.
- **health_plan_meeting** — a meeting about a student's medical/health plan (e.g., anaphylaxis); nurse.
- **mtss_meeting** — MTSS / RTI / problem-solving / student-support team; tiers, interventions.
- **pre_planning** — start-of-year teacher workdays before students.
- **planning_period** — planning / common-planning / lesson-planning time.
- **post_planning** — end-of-year teacher workdays after students.
- **professional_development** — PD / training (non-safety); "PD", "in-service", "workshop".
- **safety_training** — drills + mandated safety/compliance training (active-threat, bloodborne, etc.).
- **special_event_meeting** — planning for an event (field trip, open house, performance).
- **other / unknown** — none clearly fits, or evidence too weak.

## Request intents
`prep_for_meeting · draft_communication · summarize_or_minutes · identify_required_attendees ·
schedule_or_triage · documentation_or_compliance · extract_artifact_only · unknown`.

## Required-cadence advisories (IEP / 504) — ADVISORY, verify on source
For a student who **already has a plan**:
- **iep_meeting** — under **IDEA**, the IEP team must review the IEP **at least annually**
  (reevaluation **at least every 3 years**). Output `required: true`, `authority: "IDEA"`,
  `verify_on_source: true` (the student's plan + district policy). The classifier states the **general
  rule only** — it never determines a specific student's obligation → **escalate** +
  `special-education-support`.
- **section_504_meeting** — **Section 504** requires **periodic** review (commonly annual; districts
  vary). Output `required: true`, `authority: "Section 504"`, `verify_on_source: true`. Escalate.

(If no plan exists, `required` is not asserted — flag as "verify whether a plan exists".)

## Routing table (route, don't author)
| Meeting type | Route to | Note |
|---|---|---|
| parent_teacher_conference, parent_contact (discipline) | `family-communication` | talking points / call prep; privacy-emphasized |
| parent_contact (medical), health_plan_meeting | `family-communication` + surface the signed medical action plan; **escalate** | from the signed plan only; defer to nurse / 911 |
| iep_meeting, section_504_meeting | `special-education-support` | **escalate**; team/legal review; never a determination |
| mtss_meeting, data_meeting (intervention focus) | `intervention-mtss` | MTSS doc / data-based decision note |
| annual_review_observation, interim_observation, annual_review_debrief | `professional-learning` (teacher being observed) or `school-administration` (the evaluator) | pick by persona/evidence |
| faculty_meeting, department_meeting, grade_level_meeting, professional_development | `professional-learning` (agenda/PD) or `school-administration` (admin-run) | |
| pre_planning, post_planning, planning_period | `curriculum-mapping` / `lesson-planner` | pacing vs lesson work |
| safety_training, special_event_meeting, other, unknown | `manual_review` | no authoring owner — ask one clarifying question |

Rules: recommend a single best-fit skill that **exists**, else `manual_review`; never run
student-specific work on weak evidence; high-stakes types (IEP/504/observation/medical) must be
**corroborated** before asserting (`evidence-model.md`).
