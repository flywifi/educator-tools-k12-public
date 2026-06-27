# artifact-types.md
## Artifacts produced by feed-curator

These are governance/maintenance artifacts (not student-facing). All carry the metadata block from
`protocols/metadata-schema.md` with `human_review_required: true`, and none fabricate URLs, labels, or
verification status.

### catalog-health-report
- Purpose: the per-feed validation of `shared/feeds/feeds.json` — freshness state + label sanity.
- Required elements: per feed `id`, `url`, `tier`, `authority`, `state`
  (`current/changed/removed_404/unreachable/stale_age/superseded/uncertain`), `label_issues`,
  `redirect_to`; plus a `state_counts` rollup.
- Source of truth: F2 currency engine (`tools/source_currency.py`) + static label checks.
- Validation: every reachable verdict backed by an HTTP status or a recorded baseline; offline gives
  age-only triage, never a guess. Produced by `python3 tools/seed_curator.py --validate`.

### discovery-candidate-list
- Purpose: candidate feeds found by polite RSS autodiscovery from an authoritative page.
- Required elements: each candidate `url`, `discovered_from`, proposed `authority`/`tier`,
  `verified: false`, and a note to classify + human-approve before adding.
- Validation: public pages only, robots-respecting; a policy-blocked host is reported, not bypassed.
  Produced by `python3 tools/seed_curator.py --discover-from PAGE_URL`.

### seed-change-proposal
- Purpose: a single human-reviewable change set for the catalog.
- Required elements: `add` / `remove` / `repair` / `relabel` lists, each entry with a reason, source,
  and a `safe_repair` flag.
- Validation: only `safe_repair: true` entries are eligible for auto-apply. Produced by
  `python3 tools/seed_curator.py --propose`.

### applied-change-log-entry
- Purpose: the audit record of an applied catalog change (the unit of `ledger/feeds-change-log.json`).
- Required elements: `id`, `ts`, `feed_id`, `action` (add/remove/repair/relabel/revert), `before`,
  `after`, `reason`, `source`, `mode` (auto|approved).
- Validation: append-only; every change logged; reversible via `--revert ENTRY_ID`. Mirrors
  `ledger/rollback-log.json`.
