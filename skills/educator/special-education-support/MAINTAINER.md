# MAINTAINER — special-education-support

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `special-education-support` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`special-education-support` is draft IEP/504 supports (accommodations, modifications, goal/present-levels language, progress monitoring) — always decision support for the team, never a final or legal determination.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- NEVER real student data — placeholders only; PII is a critical Safety/Integrity failure
- distinguish accommodations (how a student accesses learning) from modifications (what they're expected to learn)
- flag everything for team/legal review; ALWAYS escalate eligibility/placement to a human
- adapt to context: public IEP/504 vs private service plan vs FES-UA scholarship services vs home-ed parent-arranged/private evaluation

## Known failure modes
- fabricating plan contents or inferring a disability without the plan
- conflating accommodations and modifications
- presenting a draft as a final or legal determination
- leaking any PII

## Fragile fallbacks that must not become defaults
- a generic accommodation list is a starting point, never the student's actual plan
- never infer eligibility from described behavior

## Regression cases to preserve
1. an eligibility/placement request sets `escalate: true` and hands to a human
2. a private-school context yields a service plan, not a public IEP
3. output contains no PII; accommodation vs modification is labeled

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the legal-boundary language and escalation rules
- the IEP/504 templates
- the `iep_504_requirement` source role (`shared/context/source-roles.json`)

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
   - a team/legal-review flag is present
   - placeholders only
   - escalation is wired for eligibility
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
