# Quality Ledger

The **Repository Quality Ledger** (Quality Gates §94) is the running, append-only record of quality
decisions across the ecosystem. It exists so the repository's history stays **traceable and
auditable** (QG repository invariants §96: "Repository history remains traceable", "Quality decisions
remain auditable").

## What goes here
One row per quality decision emitted by `quality-review` (or a skill's self-gate), summarizing the
artifact, who decided, the outcome, and a pointer to the full decision record.

## Rules
- **Append-only / immutable.** Once written, an entry is not edited; a correction adds a **new** entry
  (QG §94.4).
- **Full record lives with the artifact.** Each artifact carries its complete decision record in its
  metadata block (`protocols/metadata-schema.md`); the ledger is the index + audit trail.
- **No real student data.** Ledger entries reference placeholder artifacts only.

## Format
See `quality-ledger.md`. Columns: `decision_id · date · artifact_id · skill · decision · composite ·
reference`. The seed entries correspond to the worked examples bundled in each skill.

## Roadmap
Phase E adds an analytics pass over this ledger to populate the success metrics in `QUALITY_MODEL.md`
/ `STATE.md` (approval rate, longitudinal trends — QG §95).
