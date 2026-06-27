# MAINTAINER — lesson-planner

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `lesson-planner` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`lesson-planner` is standards-aligned, differentiated instructional materials (lessons, units, guided notes, exit tickets, centers, performance tasks).

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- select + cite REAL, verified standards **per the context's standards applicability** (state codes for public/charter/virtual; the school framework for private; advisory objectives for home-ed)
- build in UDL plus tiering / EL / IEP supports by default
- does NOT build standalone tests/rubrics (assessment-designer) or slide decks (presentation-builder)

## Known failure modes
- fabricating or mis-coding a standard
- forcing B.E.S.T./NGSSS onto a home-ed/private context
- shallow or bolted-on differentiation
- using the grade band when the individual grade matters

## Fragile fallbacks that must not become defaults
- assuming a grade/subject when unstated is acceptable only if logged as an assumption
- an included check-for-understanding is not a substitute for a full assessment

## Regression cases to preserve
1. a home-ed lesson is not penalized for omitting a mandated code
2. a public lesson requires a verified, correctly-coded standard
3. an 8th-grade lesson uses grade-8 expectations, not just the 6-8 band

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the lesson/unit artifact template
- the standards-applicability branching

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
   - a differentiation block is present
   - the check-for-understanding aligns to the objective
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
