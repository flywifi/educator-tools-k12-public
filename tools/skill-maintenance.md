# Skill maintenance & update instructions (canonical)

Every skill ships a **`MAINTAINER.md`** — durable update instructions so the ecosystem is *used and
maintained consistently*. `SKILL.md` is the runtime contract (what the model does); `MAINTAINER.md` is
the maintainer contract (what must not drift, what to check on every change, how disagreements are
handled). Template: `tools/skill-template/MAINTAINER.md`; presence is enforced by `tools/sync_check.py`.

## Why this exists
Skills drift one convenient edit at a time. Capturing the non-negotiables, failure modes, and
regression cases next to each skill keeps behavior consistent across maintainers and across the 13
skills, and it makes the **canonical source-of-truth resolver + minority report**
(`shared/context/source-of-truth.md`, `shared/context/minority-report.md`) the single, shared way every
skill resolves a conflict — not ad-hoc per-skill logic.

## Required sections (every `MAINTAINER.md`)
1. **Purpose of this maintainer file** — what the skill is and its hard boundary.
2. **Non-negotiable invariants** — shared (see `CLAUDE.md`) + skill-specific behaviors that must not be
   weakened casually.
3. **Known failure modes** — the highest-impact ways the skill goes wrong.
4. **Fragile fallbacks that must not become defaults** — degraded behavior that is acceptable only when
   clearly labeled, never as the silent normal path.
5. **Regression cases to preserve** — numbered; each should map to an `evals/evals.json` case.
6. **Approval-gated changes** — changes that are behavior-changing and require explicit review (never a
   "trivial fix"): synced references, frontmatter, output schemas, and the skill's own policy surfaces.
7. **Minority-report policy** — when/how to emit a decision record with a minority report, preserving the
   primary interpretation, the alternates, why the primary won, and what evidence would overturn it.
8. **Update checklist** — the ordered checks to run on any change (always includes `tools/sync_check.py`).

## How it ties to the resolver
When sources disagree about which standard/rule/SOP governs, skills resolve it through
`shared/context/sot_resolver.py` and attach the decision record (`shared/context/decision.schema.json`)
to artifact metadata (`protocols/metadata-schema.md`); the procedure is canon in
`protocols/conflict-protocol.md` §4a. A `MAINTAINER.md` does not re-implement this — it points to it, so
the policy stays in one place.

## When you change a skill
Run its `MAINTAINER.md` update checklist top to bottom, then `python3 tools/sync_check.py` (which checks
synced references, frontmatter, resource integrity, **and that every skill still has a `MAINTAINER.md`
with the required sections**). New skills get the template automatically via
`python3 tools/new_skill.py <name>`; fill in the `<…>` placeholders before shipping.

## Editing the shared parts
The shared invariants live in `CLAUDE.md` and `shared/quality/quality-gates.md`; the minority-report
policy lives in `shared/context/minority-report.md`. Edit those canonical sources — do not fork
shared rules into a single skill's `MAINTAINER.md`.
