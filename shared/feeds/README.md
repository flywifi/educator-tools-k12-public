# feeds — feed self-update engine (L7)

A small, tiered **address book of trusted education feeds** (`feeds.json`) plus a local store of the
items harvested from them. On command the runner visits each *due* feed, asks "anything new since last
time?" with a polite conditional GET (HTTP 304 ⇒ skip), files only genuinely-new items into a local
**gitignored** SQLite database, and produces a **"what's new" digest at zero model-token cost**.

- **Polite + cheap** — conditional GET (ETag/Last-Modified) reused from `tools/source_currency.py`;
  unchanged feeds cost almost nothing. Dedupe by content hash; only new items are stored.
- **Offline-graceful** — `--offline` does age-only triage; a blocked/unreachable feed is reported
  honestly (`unreachable`/`uncertain`), never guessed.
- **Advisory, never auto-acting** — a `tier:canonical` / `authority:primary` feed signalling a change
  routes to "verify on the primary source / hand to the curator (L8)". `human_review_required: true`.
- **stdlib-first** — parses with `feedparser` if present, else stdlib ElementTree.

## Catalog tiers (authoritative-first)
| tier | meaning | confirms a change? |
|---|---|---|
| `canonical` | primary gov/standards sources (FLDOE/CPALMS/leg/WIDA) | **yes** — only this tier |
| `news_teacher_student` | curated secondary news on issues affecting teachers/students | no (discovery) |
| `product_updates` | edtech/vendor product news — **OFF by default** (`layers.product_updates.enabled`) | no |

Every feed carries `category`, `authority`, `tier`, `purpose`, `grade_band`, `subject`, `scope`, and
`cadence_days`. URLs marked `verified:false` are **seed candidates pending curator validation** (L8) —
never assumed live or correct.

## Usage
```bash
python3 tools/feeds_update.py --status                 # due feeds + the active update mode
python3 tools/feeds_update.py --update [--offline]     # fetch due feeds, store new items (advisory)
python3 tools/feeds_update.py --digest --since 2026-06-01 --category program   # what's new
```

## Trigger (tied to setup, separately overridable)
The cadence is driven by the teacher's L0 `feed_update_mode` preference (default derived from their
`offline_tier`; set via `skills/teacher-profile/scripts/profile_wizard.py --preferences`):
`manual` (pull on demand), `on_session_start` (an opt-in hook refreshes on open), or `scheduled` (a
documented cron/CI line for deployments). The runner reads the preference and falls back to `manual`
with no profile. Changing the mode is data — never a rebuild.

## Health & curation
Feed rot (dead links, redirects, mislabels, new feeds worth adding) is handled by the **L8 curator**
(`tools/seed_curator.py` + the `feed-curator` skill): it validates the catalog, discovers candidates,
auto-applies only mechanically-safe repairs, logs every change to `ledger/feeds-change-log.json`, and
proposes the rest for human approval.
