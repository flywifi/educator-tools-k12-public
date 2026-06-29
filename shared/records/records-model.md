# Student records + handoff packages (canonical)

A shared, governed record so student information travels **consistently across handoffs** — between TOS
skills at runtime, to next year's teacher, and when a student transfers schools — instead of being
re-described ad hoc each time. Modeled on an enterprise education data model but kept **minimum-necessary,
governance-first, placeholders-in-repo**. Identity/guardians/health come from `shared/students/`;
School/District/AcademicYear/course context links to `shared/context/`; standards use
`shared/standards/`; availability/restrictions use `shared/connectors/`. First consumer:
`skills/meeting-classifier/` (the skill→skill package).

Files: `records.schema.json` (contract), `records.example.json` (placeholder store), `records.py`
(offline assembler), this prose. Real records live in `records.local.json` (gitignored) or a live SIS.

## Universal entity pattern
Every entity reference carries a human-readable name alongside every id:
`*_id` · `*_code` · `*_name` · `*_display_name` (e.g. `course_id`/`course_code`/`course_name`/
`course_display_name`). This is what keeps a course/section/standard recognizable across every handoff.

## Lifecycle / audit envelope → metadata block
Every major object carries `lifecycle` (`created_date, last_modified_date, created_by, last_modified_by,
status, active`). This **maps to** the governance metadata block (`protocols/metadata-schema.md`) — audit
entries reference the decision record / Quality Ledger id rather than duplicating governance. Every
generated package ends with that metadata block and `human_review_required: true`.

## Core baseline (default, always on)
Identity (extends the `shared/students/` profile), Guardians (authorization / court-restriction flags),
Enrollment, Course/CourseLevel/Section (course_level is separate from course_code), StandardsMastery,
**assessment results + curriculum/learning objectives** (so teachers — or the AI — can scaffold from how
the student tested and what they're learning), active Interventions/Accommodations, minimum-necessary
**summaries** (attendance, behavior, health, counseling), teacher recommendations/notes, parent-contact
summary, the **three handoff packages**,
EducationalTimeline, MobilityHistory, TransitionHandoff. School/District/AcademicYear/Term **link to**
`shared/context/` (records adds Year/Term/Section that context does not model).

## Extended modules (independent feature flags — opt in per category)
Enable only the categories a deployment needs via `records_modules` (or `--modules`); each is configured
**with the end user** when turned on. `records_modules: "all"` (or `--modules all`) is shorthand for
"every module." Schema-complete but **inactive** unless enabled; minimum-necessary + placeholders still
apply (each widens the PII surface, hence per-category opt-in).

| module | adds | sensitivity |
|---|---|---|
| `gradebook` | assignments, rubrics, submissions, grade calc, grading policy, competencies | moderate |
| `scheduling` | scheduling & placement, section capacity/occupancy | low |
| `transportation` | transportation profile + dismissal plan | moderate |
| `activities` | athletics, activities, leadership, service learning | low |
| `credentials` | credentials + portfolio | low |
| `discipline` | discipline incident detail (beyond core behavior summary) | high |
| `counseling` | counseling detail (beyond core counseling summary) | high |
| `communications` | communications log | moderate |
| `documents` | document repository | depends_on_content |
| `health_detail` | extended health records — multi-source, attributed (ePHI) | high |
| `state_reporting` | state student id + demographics for state reporting | high |

`records.py --list-modules` prints this; `--setup-module <id>` prints a per-module setup checklist
(high-sensitivity modules add a data-privacy review step).

## The three interconnected handoff packages
All share the universal pattern, the lifecycle/metadata block, identification mode, provenance, and
minimum-necessary redaction, and **compose** around one **Academic Handoff Package** (academic_summary,
course_history, course_grades [reconstructable], standards_mastery, attendance/behavior summaries, active
interventions/accommodations, health/counseling summaries, teacher recommendations/notes, parent-contact
summary; enabled-module data under `modules`).
1. **`skill_to_skill` (primary)** — the runtime envelope between TOS skills: rendered `subject_student`,
   the carried context contract, the academic package, guardians (when contact is relevant), the medical
   safety banner, connector `source_availability`/`restricted_sources`/`execution_trace`, optional
   `source_decisions`/`minority_report`, and `recommended_next_skill`.
2. **`teacher_to_teacher` (year-end)** — the academic package focused on next year's teacher.
3. **`school_transfer` (mobility)** — `transition_handoff` + `mobility_history` wrapping the full academic
   package so a receiving school can reconstruct the record.

## Identification mode
`name` (default) renders the student/guardians by name; `id`-only renders by `student_id` and hides
names/contacts (resolve on demand) — for shareable/saved packages. Reuses `shared/students/`.

## Student health information (multi-source, attributed — NOT signed-plan-only)
Health guidance usually lives on **district/school health forms, nurse notes, guardian notes, sick
notes** — a physician signature is rarely available and **not required**. Each health item carries
`source_type` + `source_authority` (official form/action plan = high; nurse/guardian note = medium;
verbal = low) + `provided_by` + optional `signed`. The banner is surfaced **verbatim from the source,
attributed with its authority + date; never fabricated**; defer to the **nurse / 911** in an emergency;
minimum-necessary. Conflicting sources go through `shared/context/sot_resolver.py` (authority tier orders
them; never silently merged). See `shared/students/student-data-policy.md`.

## SIS authority + conflicts
A connected **SIS is authoritative** for records and is used first unless overridden; the local store is
the fallback/cache. SIS↔local (and multi-source) conflicts are **never auto-merged** — raise via
`sot_resolver` and keep a minority report.

## Privacy boundary
Repo content is **placeholders only** (`is_placeholder`); real records live only in the gitignored store
or a live SIS; **minimum-necessary**; `human_review_required: true` on every package. Decision support,
not a determination.

## Use the helper
```bash
python3 shared/records/records.py --list-modules
python3 shared/records/records.py --package skill_to_skill --student S-000123 [--mode name|id] \
    [--modules transportation,gradebook | all] [--flags <connector-flags.json>]
```
Offline, stdlib only. Not added to `tools/sync_manifest.json` (no per-skill synced copies).
