<!-- last_reviewed: 2026-07-15 | owner: routing-engine-maintainer -->
# shared/routing — one data-driven router (offline, stdlib)

Picks which skill (or atom) should handle a request, from a **single canonical registry** so that
`teacher-core` and `meeting-classifier` route from one source of truth instead of each hard-coding
their own logic.

## What's here
- `routing.json` — the canonical registry: `skills` (keyword/context signals per skill),
  `meeting_routes`, `atom_routes`, and a `fallback`. **Source of truth** for dispatch.
- `router.py` — three dispatch modes:
  1. `route()` — top-level skill dispatch (keyword scoring + context signals);
  2. `atom_route()` — direct dispatch when the request is a single atomic operation;
  3. `infer_atoms()` — given a task context, return which atoms would enrich a workflow.
- `__init__.py` — re-exports `route`, `meeting_route`, `score_skills`, `load_registry`.

## Non-negotiable invariants
- **Every route target must be an installed skill** (or the declared `fallback`). This is enforced by
  `tools/sync_check.py` **check 10** (routing integrity) and **check 11** (workflow atom resolution) —
  a route pointing at a non-existent skill fails the drift guard.
- Routing is **offline and deterministic** (pure stdlib, no network) so it behaves identically on
  every surface.

## Maintainer gotchas
- When you add/rename/remove a skill, update `routing.json` **and** re-run `python3 tools/sync_check.py`
  — checks 10/11 will name any dangling target. `skills/core/skill-health` also lists the full set of
  files that must move together (routing, `ROUTING_MODEL.md`, the routing-map, `STATE.md`,
  `METRICS.md`, the ontology).
- Leaf skill names are the stable identifier after the sub-grouping refactor — route on the leaf name
  (`lesson-planner`), not a grouped path.
