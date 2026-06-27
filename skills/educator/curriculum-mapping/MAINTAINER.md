# MAINTAINER — curriculum-mapping

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `curriculum-mapping` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`curriculum-mapping` is long-range planning artifacts — curriculum maps, pacing guides, scope & sequence — with full coverage and vertical/horizontal alignment.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- realistic pacing with no coverage gaps or redundancy across the span
- spans multiple units/weeks/months (not a single lesson or assessment)
- respects the resolved calendar and the individual-grade testing schedule

## Known failure modes
- pacing that ignores the calendar or statewide testing windows
- coverage gaps or double-coverage
- treating a grade band as uniform when grade-level testing differs

## Fragile fallbacks that must not become defaults
- a generic calendar is a placeholder until the district/school calendar is supplied
- an assumed start date / term structure must be logged

## Regression cases to preserve
1. an 8th-grade map reflects 8th-grade assessment (e.g., Statewide Science) distinct from 6/7
2. a private-school map sequences the school's framework, not B.E.S.T. by default
3. pacing aligns to the resolved calendar

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the coverage-completeness rule
- the map/scope-and-sequence schema

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
   - a coverage check against the standards set
   - calendar alignment is verified
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
