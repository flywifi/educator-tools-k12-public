# MAINTAINER — family-communication

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `family-communication` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`family-communication` is family-facing communication — newsletters, parent/guardian letters & emails, conference talking points, report-card comments.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- placeholder names ONLY; never real student data, grades, behavior, or health/SpEd details
- plain, jargon-free, translation-friendly language at an accessible reading level; strengths-based tone
- for an individual child, keep specifics general and mark where the teacher must personalize
- adapt to context: district comm policy vs private handbook vs home-ed (the parent IS the teacher; comms target a co-op/umbrella/evaluator)

## Known failure modes
- leaking student specifics into an otherwise general message
- reading level too high or jargon-heavy
- deficit-framed tone
- assuming a district communication policy for a home-ed family

## Fragile fallbacks that must not become defaults
- personalization placeholders must be clearly marked for the teacher to fill
- an assumed home language / reading level must be stated

## Regression cases to preserve
1. an individual-student message keeps specifics general and flags personalization
2. a home-ed audience is reframed (no district policy assumed)
3. the reading level matches the audience

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the privacy rules
- the tone policy

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
   - the output is PII-free
   - the reading level is appropriate
   - the tone is strengths-based
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
