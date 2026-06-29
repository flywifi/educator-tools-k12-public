# MAINTAINER — teacher-core

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `teacher-core` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`teacher-core` is the ecosystem hub — classify an educator's request, route it to the right capability skill, run the shared pipeline, and apply the Quality Gates before anything is final. It routes; it does not author final artifacts.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- routes to a capability skill — it never becomes the generator of a final artifact itself
- resolves the teaching context FIRST, then routes, and passes the context into the routed skill
- always runs the shared pipeline (`references/method.md`) and the Quality Gates
- defaults to traditional-public Florida only when context is unstated, and says so

## Known failure modes
- routing to the wrong skill (e.g., an IEP request to lesson-planner instead of special-education-support)
- skipping context resolution before routing
- dropping or mutating the context contract across a handoff
- treating itself as a content generator

## Fragile fallbacks that must not become defaults
- the traditional-public-FL default context is an explicit, logged default — never a silent override of a stated context
- a best-guess route must be stated to the user, not hidden

## Regression cases to preserve
1. an IEP/504 request routes to special-education-support, not lesson-planner
2. an MTSS/RTI request routes to intervention-mtss, not special-education-support
3. an ambiguous request is clarified or its assumed route is logged, not silently misrouted
4. the resolved context appears unchanged in the routed skill's metadata

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the routing map / skill taxonomy
- the pipeline order and gate sequence

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
   - the routing table matches the installed capability skills (add new skills to it)
   - context is resolved before routing and survives the handoff
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
