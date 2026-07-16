<!-- last_reviewed: 2026-07-15 | owner: tooling-maintainer -->
# tools/ — build, guard, and data tooling

Stdlib-first Python utilities for building the TOS, guarding it against drift, and maintaining the
canonical data. All are offline unless noted. Run from the repo root: `python3 tools/<name>.py`.

## Guards & CI (the drift gate)
- `sync_check.py` — **the drift guard / CI hard gate.** Asserts ecosystem invariants (synced-copy
  byte-identity, SKILL.md wiring, MAINTAINER presence, routing/atom integrity, url-provenance, offline
  index freshness, and the doc-drift guards). Exit 0 = clean, 1 = drift report.
- `metrics.py` — regenerates `docs/METRICS.md` from live evidence (skills, ledger, ontology).
  **Generated — do not hand-edit the output.**
- `registry_currency.py` / `source_currency.py` — freshness for committed registries (internal
  content-hash) and external web sources (`canonical-sources/registries/<domain>.json`, e.g.
  `macos-sources`). Citing an external URL in a maintainer-class doc requires registering it in a
  source registry or `url-provenance.json` — enforced as `sync_check.py` check 20.
- `mac_audit.py` — mac-lint: static cross-platform-safety checks (no bare-`python3` child spawns; no
  encoding-less text opens). Also enforced as `sync_check.py` check 19.
- `security_scan.py`, `tos_check.py`, `validate_outputs.py`, `validate_examples.py`,
  `validate_document.py` — governance/quality/output validators.
- `deps_preflight.py`, `doctor_env.py` — dependency + environment preflight. `deps_preflight.py
  --install <capability>` / `--install-all` installs optional capabilities into the isolated
  `.harvest-venv` (wheels-only; never system Python → no macOS/Homebrew PEP 668); `--python-path`
  prints that venv's interpreter for a Claude Desktop MCP `command`/GUI launch.

## Scaffolding & packaging
- `new_skill.py` — scaffold a skill from `tools/skill-template/` + copy synced refs.
- `package_skill.py` — package a skill for distribution.
- `export_reference_pack.py`, `export_chatgpt.py`, `export_openai.py` — platform export bundles.
- `version.py`, `rollback.py`, `repair_loop.py`, `skill_repair.py` — versioning + repair.

## Reference index & standards data
- `offline_index.py` — build/query the gitignored offline reference index; `--build` also writes the
  committed `canonical-sources/index/index-manifest.json` (see that dir's README).
- `parse_fl_standards.py` — parse FL standards into the indexed JSON (rebuilds the index after).
- `standards_refresh.py`, `crosswalk.py`, `fl_lookup.py`, `msid_lookup.py` — standards refresh,
  crosswalks, school MSID lookups (`--apply` rebuilds the index).

## Harvest / ingest orchestrators
- `harvest_all.py`, `ingest_sources.py`, `local_harvest.py`, `field_harvest.py`,
  `acquire.py`, `ocps_resources.py` — acquire + ingest canonical source data (rebuild the index).
- `fetch_resilient.py`, `fetch_cache.py`, `render_fetch.py`, `rate_governor.py` — resilient fetch,
  caching, rendering, and rate governance for the harvesters.

## Benchmarks & feeds
- `run_benchmark.py` — the evidence-gated benchmark harness (`--check`, `--report`).
- `make_feed.py`, `feeds_import.py`, `feeds_publish.py`, `feeds_update.py`, `verify_feeds.py`,
  `seed_curator.py`, `seed_probe.py` — content-feed tooling.

## Non-negotiable invariants
- After editing anything under `shared/` or `protocol-layer/`, run `python3 tools/sync_check.py`.
- Any tool that writes an indexed source must rebuild the offline index and commit the manifest
  (producers do this automatically; the guard catches misses).
- Never hardcode an external URL without declaring it in `tools/url-provenance.json` (check 13).
