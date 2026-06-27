# MAINTAINER — assessment-designer

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `assessment-designer` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`assessment-designer` is standards-aligned assessments and rubrics/scoring tools that actually measure the intended learning.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- every item/criterion maps to a real cited standard **per applicability**, with balanced difficulty and cognitive level
- always supply an answer key or scoring guide, plus accessibility + accommodations
- does NOT build a full lesson (lesson-planner) or slides (presentation-builder)

## Known failure modes
- items not actually aligned to the stated objective
- missing or inconsistent answer key / scoring guide
- biased or inaccessible items
- fabricated standard codes

## Fragile fallbacks that must not become defaults
- an item bank without a blueprint is a draft, not a finished assessment
- difficulty/cognitive-level estimates are approximate and must be labeled as such

## Regression cases to preserve
1. a home-ed rubric is scored on objective↔task coherence, not for a missing state code
2. a public assessment requires verified codes
3. a performance task ships with a scoring guide

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the scoring-guide/answer-key format
- the item-to-standard alignment requirement

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
   - an answer key / scoring guide is present
   - an item↔standard alignment table is present
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
