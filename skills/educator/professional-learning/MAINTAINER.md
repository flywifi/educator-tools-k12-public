# MAINTAINER — professional-learning

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `professional-learning` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`professional-learning` is coaching and PD resources (observation/look-for tools, coaching guides, PD session plans) grounded in adult-learning principles.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- coaching is NON-EVALUATIVE and growth-oriented — distinct from administrator evaluation (school-administration)
- ground resources in adult-learning principles; tie look-fors to concrete, observable practice
- the audience is educators, not students or families

## Known failure modes
- drifting into evaluative judgment
- vague, non-observable look-fors
- child-pedagogy framing applied to adult learners

## Fragile fallbacks that must not become defaults
- a generic PD agenda is a starting point until the focus practice is set
- an assumed session length must be stated

## Regression cases to preserve
1. look-fors are observable and concrete
2. the non-evaluative framing is preserved
3. evaluative walkthrough requests route to school-administration

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the non-evaluative boundary

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
   - look-fors are observable
   - the tone is non-evaluative
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
