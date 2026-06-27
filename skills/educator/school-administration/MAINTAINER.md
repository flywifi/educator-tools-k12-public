# MAINTAINER — school-administration

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `school-administration` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`school-administration` is school/district leadership tools — walkthrough instruments, implementation plans, progress-monitoring/data systems — at the implementation level.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- aggregate / implementation-level focus; placeholders, never student or staff PII
- walkthrough tools support IMPLEMENTATION monitoring, not formal personnel evaluation (that is district policy + human judgment)
- adapt governance to context: district board vs charter independent board + sponsor vs private governance vs co-op/umbrella

## Known failure modes
- drifting from implementation monitoring into personnel evaluation
- assuming a district-board structure for a charter or private school
- including staff/student PII

## Fragile fallbacks that must not become defaults
- a generic rollout template is a starting point until roles/phases are confirmed
- an assumed governance structure must be stated

## Regression cases to preserve
1. a charter context uses an independent board + sponsor relationship
2. a private context uses private governance/accreditation, not district policy
3. a walkthrough is framed as implementation monitoring, not evaluation

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the personnel-evaluation boundary
- the governance taxonomy

## Minority-report policy
When sources or interpretations disagree materially, emit a decision record with a minority report via
the canonical resolver (`shared/context/sot_resolver.py`; policy `shared/context/minority-report.md`).
Preserve all four: the **primary interpretation** (`decision_log.chosen_interpretation`), the
**alternates** (`conflicts`, `failed_to_merge`), **why the primary won** (`decision_log.why_it_won`),
and **what evidence would overturn it** (`residual_uncertainty.what_would_resolve_it`). Do not bury
disagreement in prose; do not promote recurring practice to doctrine; **escalate** individual-student/
legal determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes (synced refs byte-identical; frontmatter + resource integrity);
3. every reference named in `SKILL.md` still exists; evals still pass and a case was added for new behavior;
4. context adaptation still correct across school types (`shared/context/`);
5. skill-specific:
   - the governance structure matches the school type
   - the evaluation boundary is intact
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
