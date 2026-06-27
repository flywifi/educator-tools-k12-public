# MAINTAINER — intervention-mtss

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `intervention-mtss` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`intervention-mtss` is tiered MTSS/RTI materials (Tier 1/2/3 plans, documentation, progress-monitoring) as team decision support.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- MTSS tiers are INSTRUCTIONAL tiers, NOT special-education eligibility
- pick an evidence-aligned intervention for a named target skill; set a tier; define a progress-monitoring cadence + decision rules
- placeholder student data only; route IEP/504 work to special-education-support

## Known failure modes
- conflating MTSS with special-education eligibility/placement
- a vague target skill or missing progress-monitoring cadence
- treating tier movement as an eligibility decision

## Fragile fallbacks that must not become defaults
- a generic intervention without the target skill is not acceptable as the default
- data-light placeholders must be clearly marked

## Regression cases to preserve
1. an IEP/504 request is redirected to special-education-support, not handled here
2. a tier is set with a monitoring cadence and a decision rule
3. no eligibility/placement determination is made

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the tier model
- the MTSS-is-not-special-education boundary

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
   - cadence + decision rules are present
   - the MTSS/special-ed boundary is preserved
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
