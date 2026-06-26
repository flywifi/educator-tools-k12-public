# Verifying feeds — two methods + the open-net hand-off

The TOS build/run container's **egress is blocked** (every outbound URL 403s), so feeds cannot be
fetched or verified *inside* it. Verification happens **where the internet is open** and the result is
handed back. The curator supports two methods; **Option B is the current default.**

## Option A — portable verifier script (most reliable)
Run `tools/verify_feeds.py` anywhere with open network (a laptop, a CI job, or a chatbot that has a
real **code interpreter** — not just a browser tool, which can't read raw XML):

```bash
python3 tools/verify_feeds.py shared/feeds/feed_candidates.json > verified.json
```

It fetches each candidate, autodiscovers the RSS/Atom `<link rel="alternate">` when given a page,
parses the feed (stdlib), and emits **catalog-ready** entries (`verified: true` + a proof item +
etag/last-modified/sha256 baseline) for `shared/feeds/feeds.json`, plus an `unverified` list with the
reason. No dependencies; nothing fabricated. `shared/feeds/feed_candidates.json` is pre-seeded with the
current discovery leads.

## Option B — chatbot via a reader-proxy (CURRENT default)
For a web chatbot whose browser can't read raw XML, fetch each feed **through a reader-proxy that
renders XML as text** — `https://r.jina.ai/<FEED_URL>`. The full prompt is in
`shared/feeds/FEED_DISCOVERY_PROMPT.md`; the key rule: a feed is only `verified: true` if the proxied
content shows real items (title/link/date), otherwise it goes to `unverified` — never guessed. The
chatbot returns the same JSON schema as Option A, which drops straight into `shared/feeds/feeds.json`.

> **Why B is current:** it needs no local setup from the teacher — just paste a prompt into any
> web-enabled chat. Promote to A when a teacher/admin can run Python where the net is open (it is exact
> and scriptable).

## The hand-off — how verified feeds reach the egress-blocked TOS
Whichever method runs, the verified JSON must travel from the **open-net writer** to the
**egress-blocked reader** (this repo). Two strategies, mirroring OpenCLAW's `crawlkit` and Firebase:

### Primary — local-first git snapshot (OpenCLAW / `crawlkit` model)
The writer (Option A/B, or a `crawlkit`-style crawler) produces SQLite + a `manifest.json` and **commits
a snapshot to a git "share repo"**; the reader **clones/pulls and imports** it with **live sources
disabled** — exactly our situation. This is what TOS already does: `ledger/snapshots.json`
(git-anchored snapshots), the L3 bucket manifest (`tools/sync_cache.py`), and `verify_feeds.py` output →
`shared/feeds/feeds.json` → `git pull`. crawlkit adds incremental **shard fingerprints** so only changed
tail shards transfer and local FTS rows are preserved — a good future upgrade for the feed store. This
is the **recommended** hand-off: it needs no live network in the reader.
- crawlkit: https://github.com/openclaw/crawlkit · openclaw: https://github.com/openclaw/openclaw

### Optional — Firebase realtime (for ONLINE teacher deployments)
The writer pushes verified feeds to **Firebase Realtime Database** (JSON; offline edits merge on
reconnect) and online teacher clients subscribe in realtime. Useful for a deployed, networked teacher
environment, but **not** for the egress-blocked container (it can't reach Firebase). Treat Firebase as a
`cloud_optional` backend, off by default, bound by `shared/students/student-data-policy.md`; never send
student data, only public feed metadata.

## Recommended libraries (optional, capability-gated future boosters)
The engine is stdlib-first (ElementTree); these are drop-in upgrades, never required:
- **XML / feeds:** `feedparser` (gold standard; already an optional `read_feeds` capability),
  **FastFeedParser** (kagisearch — ~25x faster, feedparser-compatible API), `atoma`, `rss-parser`
  (type-safe via `xmltodict` + `pydantic`), `lxml` (fast, fine-grained).
  - https://github.com/kagisearch/fastfeedparser · https://github.com/NicolasLM/atoma
- **SQL / SQLite:** `sqlite-utils` (simonw — build/manipulate SQLite from data), `datasette` (browse +
  publish), **`sqlglot`** (no-dependency pure-Python SQL parser/transpiler, 31 dialects — handy for
  validating/normalizing any SQL the catalog or reports emit).
  - https://github.com/simonw/sqlite-utils · https://github.com/tobymao/sqlglot
