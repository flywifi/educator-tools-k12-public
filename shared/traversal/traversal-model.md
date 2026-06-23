# Traversal & evidence-accumulation engine (canonical)

Turns **multiple inputs** (uploaded files, connector hits, record ids, prior findings) into a growing,
provenance-tagged **evidence envelope** that downstream skills enrich further. Adapts a mature
traversal-companion design to TOS sources (docintel, connectors, records, standards). It is a
**companion pass**, not the final interpreter.

## Principles
- **Append-only + provenance.** Every finding records `source` + `added_by`; upstream facts are never
  overwritten — enrichment is added alongside (duplicates become graph edges, never silent drops).
- **Sequential by default; checkpoint often.** Expand one layer at a time; persist the frontier/visited
  set so a run can pause/resume. Parallel only when state can be coordinated safely.
- **Layered, not a hop counter.** Use ~4 *meaningful* layers before asking a human to go deeper:
  1. seeds / anchor hits → 2. open the strongest anchors → 3. follow their high-signal branches
  (attachments, references, related records) → 4. the underlying source-of-truth artifacts.
- **Score then expand.** Expand only high-signal branches (relevance, authority, recency, value).
- **Stop honestly.** Stop a run on `saturated` (a layer adds nothing new), `depth_cap_reached`,
  `size_cap_reached`, or `frontier_exhausted` — recorded in `checkpoint_state.stop_reason`.
- **Gaps over guesses.** A blocked/missing/permission-denied branch is recorded in `retrieval_gaps`
  (with `capability_gaps` from docintel when relevant), never fabricated.
- **Retrieval-state ladder (shared with docintel):** `referenced · metadata_only · content_ingested ·
  local_artifact_saved` — a shallow hit never masquerades as ingested content.
- **Convergence → confidence.** 2+ corroborating findings raise confidence; a single weak finding stays
  low (mirrors the connectors/evidence policy).

## Loop (`run_traversal`)
`seeds → for each layer: pick a fetcher per seed_type → fetch → accumulate findings (dedup) + discover
new seeds (recursion) + record gaps → stop on saturation/caps`. Fetchers are **injected** so the core is
dependency-free; `docintel_file_fetcher()` reads file seeds (and turns email attachments into new file
seeds for the next layer). `route_handoff()` asks the shared router (`shared/routing/`) for the best next
skill.

## Output (`to_envelope`)
Stable field names so any skill can consume it: `objective`, `seed_manifest`, `evidence`,
`relationship_graph.edges`, `retrieval_gaps`, `traversal_log`, `checkpoint_state`, rolled-up
`confidence`, `handoff` (`what_this_pass_added`, `best_next_owner`), `human_review_required: true`.
Schema: `traversal.schema.json`.

## Use
```bash
python3 shared/traversal/traversal.py --objective "prepare for the IEP meeting" \
    --file skills/meeting-classifier/examples/sample-invite.ics \
    --file skills/meeting-classifier/examples/sample-meeting.vtt
```
Governance: offline, placeholders only in the repo, decision-support (a human owns the conclusion).
