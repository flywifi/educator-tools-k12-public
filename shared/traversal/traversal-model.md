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

## Parallel scheduler (opt-in)
`run_traversal(..., scheduler="parallel", max_workers=N)` runs each layer's **independent** fetches
(file reads, connector calls, external searches) concurrently in a bounded `ThreadPoolExecutor`
(I/O-bound work — stdlib, no async rewrite), then **merges single-threaded** after the gather so the
dedup reducer is race-free and the result is identical to sequential. Rules (grounded in proven
practice):
- **Sequential is the default**; parallel is opt-in and only safe because state mutation happens after
  the concurrent gather, the frontier is de-duped against `visited` *before* fetching (no double-fetch),
  and workers are bounded (`min(max_workers, len(todo))`; I/O heuristic ≈ cores×5).
- **Each fetcher owns its own rate-limit etiquette** — exponential backoff + jitter, honor
  `Retry-After`, stay below provider limits (same discipline as `standards_refresh.py`).
- **Graceful degradation:** one fetch failing is a recorded gap, not a crash — the layer proceeds with
  the rest (9/10 results still advance the answer).
The chosen scheduler is recorded in `skill_metadata.scheduler` and each `traversal_log` entry.

## Output (`to_envelope`)
Stable field names so any skill can consume it: `objective`, `seed_manifest`, `evidence`,
`relationship_graph.edges`, `retrieval_gaps`, `traversal_log`, `checkpoint_state`, rolled-up
`confidence`, `handoff` (`what_this_pass_added`, `best_next_owner`), `human_review_required: true`.
Schema: `traversal.schema.json`.

## External searches (parallel, rate-limited)
`shared/traversal/parallel_search.py` supplies the external-fan-out pieces, all plugging into the same
scheduler: `RateLimiter` (token bucket — stay below provider limits), `parallel_map` (bounded fan-out;
a failed item is a gap, not a crash), `web_fetch_fetcher` (a `url`-seed Fetcher that **prefers Firecrawl
when configured** — `firecrawl_config()` auto-detects `FIRECRAWL_API_KEY` or a self-host
`FIRECRAWL_BASE_URL`, so JS-rendered district pages work with no per-use setup — else a polite `requests`
GET honoring `Retry-After` + backoff; gap otherwise), `rss_fetcher` (a `feed`-seed Fetcher for RSS/Atom,
`feedparser` or stdlib fallback), and `search_fetcher(search_fn)` which wraps an **injected** search
callable (the host AI's native web search, or a configured API — we build no search client) into a
`query`-seed Fetcher that emits findings + `url` seeds for the next layer. So a query fans
out to results, then to pages, concurrently — with the same provenance, dedup, gaps, and stop rules.

## Use
```bash
python3 shared/traversal/traversal.py --objective "prepare for the IEP meeting" \
    --file skills/meeting-classifier/examples/sample-invite.ics \
    --file skills/meeting-classifier/examples/sample-meeting.vtt
# external, concurrent + rate-limited:
python3 shared/traversal/traversal.py --objective "FL grade-4 fractions standard" \
    --url https://www.cpalms.org/... --scheduler parallel --rate 5
```
Governance: offline, placeholders only in the repo, decision-support (a human owns the conclusion).
