# MAINTAINER — atom-misconception

## Purpose
`SKILL.md` is the runtime contract; this file preserves non-negotiable behavior for `atom-misconception` so a future maintainer keeps the intended scope.

## Non-negotiable invariants
- References `references/method.md` and emits `human_review_required: true`.
- Does exactly ONE thing — returns one structured JSON artifact.
- Never fabricates standards, citations, or student data.
- No real student data — placeholders only (`[Student Name]`, `[Date]`, etc.).
- Output is advisory, not final. See SKILL.md "Do NOT use this atom for" clause.

## Known failure modes
- Scope creep: being asked to do multiple things (generate + differentiate + check). Refuse and redirect to the appropriate atom.
- Fabricating a standard code when lookup fails. Always return empty `standards: []` with an honest `note` instead.

## Fragile fallbacks that must not become defaults
- Model-inferred match_method when L1 cache is absent — must be labeled `uncertain`, never presented as confirmed.

## Regression cases to preserve
1. Returns `human_review_required: true` in every response.
2. Does not generate content outside its declared scope.
3. Returns an honest gap (not fabricated output) when required inputs are missing.

## Approval-gated changes
Editing synced references (method.md, quality-gates.md), frontmatter keys, or the output JSON schema.


## Minority-report policy
Atoms are narrow-scope — when sources or interpretations disagree on this atom's single operation,
emit a decision record via `shared/context/sot_resolver.py` (policy `shared/context/minority-report.md`)
and escalate to the calling workflow skill. Do not bury disagreement in prose.

## Update checklist
1. SKILL.md description still specific + scoped with "Do NOT use for…" clause intact.
2. `python3 tools/sync_check.py` passes.
3. All references named in SKILL.md still exist.
