<!-- last_reviewed: 2026-07-15 | owner: atoms-registry-maintainer -->
# shared/atoms — the atom registry + IO contract

Single-operation **atoms** (`skills/atoms/*`) are the smallest composable units the orchestrators
chain into workflows. This directory holds the canonical registry of every atom and the IO envelope
they hand off through.

## What's here
- `atoms.json` — canonical list of all single-operation atoms (currently `count: 43`). For each atom:
  `description`, `version`, `group`, and `path` (e.g. `skills/atoms/accommodation-match`). **Source of
  truth** for routing, workflow dispatch, and health checks — mirrors each atom's `SKILL.md`
  frontmatter.
- `atom-io.schema.json` — the JSON-Schema IO contract: every atom accepts an `input` envelope and
  returns an `output` envelope conforming to this schema, so orchestrators can validate hand-offs
  between atoms in a workflow chain.

## Non-negotiable invariants
- **The registry mirrors the installed atoms.** Every `path` in `atoms.json` must resolve to a real
  `skills/atoms/<name>/SKILL.md`, and every atom named in a `workflow.json` must be an installed skill
  — enforced by `tools/sync_check.py` **check 11**.
- `count` must equal the number of entries in `atoms` (keep them in step when adding/removing an atom).

## Maintainer gotchas
- Adding an atom is not just a new `skills/atoms/<name>/` dir: also register it in `atoms.json`, update
  `count`, and re-run `python3 tools/sync_check.py`.
- Atom I/O changes are hand-off-breaking — bump the atom `version` and keep the `atom-io.schema.json`
  envelope backward-compatible, or update every orchestrator that chains it.
