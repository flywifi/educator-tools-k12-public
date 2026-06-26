# Context-confirmation spine (canonical, LIGHT shell)

A thin **unifying view** over what the ecosystem already knows about one teacher's situation — their
profile (F4), school + programs (F3), and (gated) staff directory (F5) — plus a **confirmation step** so
the teacher confirms/corrects inferences before anything drives behavior. This is deliberately the
*light* spine the plan calls for; the full knowledge-graph engine + national scaling remain a later
vision, not this shell.

## What it composes (no new source of truth)
The spine **reads** the existing engines and assembles a snapshot; it stores nothing of its own:
- `shared/context/profiles/teacher.local.json` (or the placeholder example) — roles, handoffs, prefs.
- `shared/schools/` (`schools.py`) — resolves the teacher's `school_msid` → name/status/programs.
- `shared/staff/` (`staff.py`) — resolves each handoff `counterparty_role` → person(s), honoring the gate
  (placeholder data when unauthorized; honest gaps when a role isn't in the directory).

## Outputs (`shared/graph/spine.py`)
- `--snapshot` — the unified situation (teacher, school, roles, handoffs, preferences) with a
  `confidence_floor` rolled up from provenance + unresolved links.
- `--graph` — a light relationship graph: nodes (teacher, school, program, role, counterparty_role,
  person) + edges (`works_at`, `offers`, `has_role`, `hands_off_to/from`, `filled_by`).
- `--confirm` — a **confirmation checklist**: every fact that is *not* teacher-stated/high, or any
  unresolved link, with a reason + a suggested action. Teacher-stated facts need no confirmation.

## Principles
- **User-truth vs inference.** Teacher-stated facts outrank crawled/inferred (RFC Vol 2/12); the checklist
  surfaces only what needs confirming, so the teacher isn't re-asked what they already told us.
- **Gaps over guesses.** An unresolved school or handoff is a recorded gap, never fabricated.
- **Read-only + composable.** The spine never writes; it is safe to run anytime and is the natural place
  for routing/recommendation to read a consolidated context. `human_review_required: true` on every output.

## Use
```bash
python3 shared/graph/spine.py --snapshot
python3 shared/graph/spine.py --graph
python3 shared/graph/spine.py --confirm
```

## Later (deferred, not in this shell)
A persistent knowledge-graph store, cross-teacher/school graph queries, recommendation/routing over the
graph, and national scaling — tracked in the RFC as future work.
