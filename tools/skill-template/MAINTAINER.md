# MAINTAINER — __SKILL_NAME__

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `__SKILL_NAME__` so a future maintainer keeps the intended
control plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- <bullets unique to this skill — the boundaries in its SKILL.md "Do NOT use for…">

## Known failure modes
- <the most common / highest-impact ways this skill goes wrong>

## Fragile fallbacks that must not become defaults
- <degraded behaviors that are acceptable as a clearly-labeled fallback but must never silently become
  the normal path — e.g. assuming a default context, omitting a citation, generic output>

## Regression cases to preserve
<numbered list; each should map to an `evals/evals.json` case>
1. <case>

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.
Skill-specific:
- <bullets>

## Minority-report policy
When sources or interpretations disagree materially, emit a decision record with a minority report via
the canonical resolver (`shared/context/sot_resolver.py`; policy `shared/context/minority-report.md`).
Preserve all four:
- the **primary interpretation** selected (`decision_log.chosen_interpretation`);
- the **alternate** plausible interpretations (`conflicts`, `failed_to_merge`);
- **why the primary won** (`decision_log.why_it_won`);
- **what evidence would overturn it** later (`residual_uncertainty.what_would_resolve_it`).

Do **not** bury disagreement in prose; do not promote recurring practice to doctrine; **escalate**
individual-student/legal determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes (synced refs byte-identical; frontmatter + resource integrity);
3. every reference named in `SKILL.md` still exists; evals still pass and a case was added for new behavior;
4. context adaptation still correct across school types (`shared/context/`);
5. skill-specific: <bullets>;
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
