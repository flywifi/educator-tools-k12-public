# MAINTAINER — skill-repair

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior and boundaries
for `skill-repair`. Canonical procedure: `tools/skill-maintenance.md`. Engine: `tools/skill_repair.py`;
diagnosis source: `shared/health/health.py`; principles: `references/patch-principles.md`.

## Non-negotiable invariants
Shared (every skill) — `CLAUDE.md` + `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) + metadata schema; emits `human_review_required: true`;
- never fabricate; **no real student data** — placeholders only; resolve context first; gate before final.

Skill-specific:
- **Smallest durable change.** Fix the root cause minimally; never expand a narrow fix into a redesign;
  preserve purpose, voice, triggering, and untouched files.
- **Approval is explicit.** Dry-run by default; `--apply` performs ONLY safe mechanical fixes; judgment
  items are proposed in plain language and never auto-changed.
- **Stdlib / always runs.** The repair tool must work with zero optional libraries.
- **Honesty.** Never present a patch as complete if the risky parts could not be validated; if the real
  problem is architectural drift, recommend a refactor instead of hiding it in a small patch.
- **Canon, not copies.** Fix a synced reference in `shared/`/`protocols/` and re-sync — never edit a
  per-skill copy.

## Known failure modes
- Scope creep: a "small fix" quietly becomes a rewrite.
- Auto-applying a judgment change (wording, routing, schema) as if mechanical.
- Declaring success without re-running the drift guard / health re-scan.

## Fragile fallbacks that must not become defaults
- `--apply` with no diagnosable plan should do nothing and say so — not invent fixes.
- Skipping a validation step is acceptable only when explicitly reported as "not run".

## Regression cases to preserve
(each maps to an `evals/evals.json` case)
1. Dry-run is the default and finalizes as "waiting for approval".
2. Every plan step is classified mechanical vs judgment.
3. `--apply` runs only safe mechanical fixes, then re-runs `tools/sync_check.py`.
4. A judgment finding is proposed, never auto-changed.

## Approval-gated changes (do not treat as a trivial fix)
Shared: synced references, frontmatter, output schema. Skill-specific:
- which repair classes are labeled **mechanical** vs **judgment** in `tools/skill_repair.py` (widening
  "mechanical" is the highest-risk change here);
- the set of derived files `--apply` may regenerate.

## Minority-report policy
When a fix path is genuinely ambiguous, emit a decision record with a minority report via
`shared/context/sot_resolver.py` (`shared/context/minority-report.md`): chosen path, alternates, why, and
what would overturn it. Escalate individual-student/legal determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description specific + scoped, "Do NOT use for…" intact;
2. `python3 tools/sync_check.py` passes;
3. references resolve; evals parse; add a case for any new repair class;
4. `tools/skill_repair.py` still dry-runs by default and never auto-applies judgment items;
5. re-confirm mechanical/judgment classification is conservative;
6. minority-report behavior unchanged unless explicitly approved.
