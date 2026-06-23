# MAINTAINER — meeting-classifier

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `meeting-classifier` so a future maintainer keeps the intended
control plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- **Classifies + routes only** — it never authors the meeting's artifacts (lessons, assessments,
  IEP/504 content, letters); it recommends the owner skill or `manual_review`.
- **No per-student determination** — never decide a student's IEP/504 obligation, eligibility,
  evaluation result, or a medical decision. The IEP/504 `required_cadence` is an **advisory** with
  `verify_on_source: true`; escalate specifics to the team.
- **ePHI is surfaced, never generated** — a medical/anaphylaxis action plan is quoted from the
  student's **signed plan** with its source; never fabricate instructions/dosages; defer to nurse/911.
- **Connector honesty** — a disabled/blocked/`metadata_only` source is never shown as an active path;
  degraded paths lower confidence and are recorded in `execution_trace`.
- **Real student data never enters a tracked/committed file** (placeholders only; real data lives in
  the storage adapter — `shared/students/`).

## Known failure modes
- Forcing a label on weak/single-source evidence instead of returning `unknown` / `manual_review`.
- Collapsing `annual_review_observation` vs `interim_observation` (or SIS↔local) into a guess instead
  of a minority report.
- Treating a connector that is visible but off as if it returned content.
- Echoing a medical instruction that is not in the signed plan.

## Fragile fallbacks that must not become defaults
- Classifying from a **single weak** cue (e.g., a bare calendar title) — acceptable only as a clearly
  low-confidence result, never promoted to high confidence.
- Defaulting student identification to names in a saved/shared record when the deployment set ID-only.

## Regression cases to preserve
(each maps to an `evals/evals.json` case)
1. `iep_annual_required_and_escalates` — IEP advisory (IDEA) + escalate + special-education-support.
2. `section_504_required` — 504 advisory (Section 504) + escalate.
3. `observation_vs_interim_minority_report` — material ambiguity emits a minority report.
4. `formal_observation_corroborated_no_minority` — corroboration removes the ambiguity.
5. `medical_parent_contact_surfaces_action_plan_and_escalates` — ePHI surfaced + escalate.
6. `connector_degradation_lowers_confidence` — a blocked connector sets `degraded`.
7. `id_only_mode_uses_student_id_not_name` — ID-only mode pseudonymizes the record.
8. `weak_evidence_unknown` — weak evidence → `unknown` / `manual_review`.

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.
Skill-specific:
- the meeting/intent taxonomies + routing table (`references/meeting-taxonomy.md`);
- the required-cadence advisories (legal cadence wording) — keep `verify_on_source: true`;
- the classification record shape consumed by routed skills;
- the SIS-first precedence / conflict policy (mirror `shared/students/student-data-policy.md`).

## Minority-report policy
When sources or interpretations disagree materially, emit a decision record with a minority report via
the canonical resolver (`shared/context/sot_resolver.py`; policy `shared/context/minority-report.md`).
Preserve all four:
- the **primary interpretation** selected (`decision_log.chosen_interpretation`);
- the **alternate** plausible interpretations (`conflicts`, `failed_to_merge`);
- **why the primary won** (`decision_log.why_it_won`);
- **what evidence would overturn it** later (`residual_uncertainty.what_would_resolve_it`).

Do **not** bury disagreement in prose; do not promote recurring practice to doctrine; **escalate**
individual-student/legal/medical determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes (synced refs byte-identical; frontmatter + resource integrity);
3. every reference named in `SKILL.md` still exists; evals still pass and a case was added for new behavior;
4. context adaptation still correct across school types (`shared/context/`); connector degradation still honest;
5. skill-specific: routing targets still exist; required-cadence stays advisory; ePHI surfaced-not-generated;
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
