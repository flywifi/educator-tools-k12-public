# MAINTAINER — presentation-builder

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `presentation-builder` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`presentation-builder` is instructional slide decks that teach well, rendered to `.pptx` via the pptx skill.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- one idea per slide; gradual release; visuals and checks for understanding
- aligned to a real cited standard **per applicability**; readable for the grade band
- does NOT write the lesson plan itself (lesson-planner) or a test/rubric (assessment-designer)

## Known failure modes
- text-dense slides; no checks for understanding
- text/visuals unreadable for the grade band
- fabricated standard codes

## Fragile fallbacks that must not become defaults
- placeholder images/diagrams must be marked
- an assumed deck length must be stated

## Regression cases to preserve
1. the deck includes checks for understanding and a gradual-release arc
2. the deck renders to `.pptx`
3. alignment follows the context's applicability

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the deck structure
- the pptx rendering path

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
   - the `.pptx` renders
   - readability for the grade band
   - alignment is correct
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
