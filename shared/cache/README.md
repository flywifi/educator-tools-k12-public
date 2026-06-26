# cache — Local-First standards cache (L1)

Deterministic, offline, low-token retrieval over the enumerated Florida standards.
This is the **default offline tier** of the Local-First / Modular track: a local
SQLite full-text index that returns a handful of ranked **snippets + provenance**
instead of making the model read ~1.9 MB of standards JSON.

- **Pure stdlib** — `sqlite3` + FTS5. No external dependency, fully offline, zero
  token cost at query time.
- **Regenerable artifact** — the index (`index.local.db`) is **gitignored** and never
  committed; rebuild it from the canonical JSON at
  `shared/standards/resources/florida/data/*.json` (6,583 codes).
- **Honest gaps** — if the host SQLite lacks FTS5, the engine builds a LIKE fallback
  and says so; it never pretends ranked full-text search ran.
- **No fabrication** — every result carries its source file and is **advisory**;
  verify on CPALMS (https://www.cpalms.org/search/Standard).

## Usage

```bash
python3 shared/cache/cache.py --build                          # (re)build the local index
python3 shared/cache/cache.py --stats                          # row counts + freshness
python3 shared/cache/cache.py --query "fractions" --subject math --grade 3 --limit 5
python3 shared/cache/cache.py --query "main idea" --json       # machine-readable snippets
python3 shared/cache/cache.py --verify                         # source files vs build baseline
```

Filters (`--subject`, `--grade`, `--type`, `--code` prefix) combine with the
full-text `--query` (AND). `--code` does prefix matching like `tools/fl_lookup.py`.

## How it fits the ecosystem

- Complements `tools/fl_lookup.py` (linear JSON scan) with an indexed, ranked,
  snippet-returning path — same canonical data, far less context spent per lookup.
- `--verify` compares source files against the sha256 baseline recorded at build
  time, so the future manifest-driven sync (L3) can rebuild only what changed. It
  reuses the same conditional-GET + sha256 currency idea as `tools/source_currency.py`.
- A later opt-in semantic index (L2, `sqlite-vec`) layers vector recall onto this
  same SQLite file; absent or declined, queries fall back here. Keyword search is
  always available.
