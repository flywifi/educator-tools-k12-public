# MAINTAINER — quality-review

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `quality-review` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`quality-review` is run the Quality Gates on any artifact and return a scored, evidence-based, auditable decision — the mandatory final gate. It evaluates; it never creates.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- score 9 weighted dimensions 0–5 and compute the composite (`scripts/score.py` — deterministic math)
- critical-failure overrides force Rejected regardless of composite (fabrication, real PII, unsafe/legal overreach, approval without evidence)
- Accuracy/Alignment are CONTEXT-CONDITIONAL: the absence of a mandated code is not a deduction for home-ed/private; a fabricated code is always a critical failure
- only evaluates — routes creation to the capability skills — and emits a decision record

## Known failure modes
- letting a high composite override a critical failure
- penalizing a home-ed/private artifact for omitting state codes
- scoring drift/inconsistency between reviews
- creating artifacts instead of evaluating them

## Fragile fallbacks that must not become defaults
- conditional approval is allowed only with no critical failures and clearly-defined remediation
- never fabricate evidence to 'pass' an artifact

## Regression cases to preserve
1. a fabricated code → Rejected regardless of composite
2. a home-ed artifact with no state codes → passes, Alignment not penalized
3. a public artifact with unverified codes → not Approved

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the dimension weights (governance approval, QG §32.5)
- the thresholds and critical-failure list
- the `scripts/score.py` math

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
   - weights match `protocols/quality-gates.md`
   - the context-conditional rule is applied
   - a decision record is emitted
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
