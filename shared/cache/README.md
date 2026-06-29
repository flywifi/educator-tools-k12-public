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
- An opt-in semantic index (**L2**, `semantic.py` + `sqlite-vec`) layers offline
  vector recall over this same data for paraphrase matches. It is **off by default**
  and activates only when the optional deps are installed *and* the teacher granted
  consent (`local_first.consents.local_semantic`, set via the teacher-profile
  wizard). Absent or declined, `semantic.search()` transparently falls back to L1
  keyword search and reports the gap — never faked. Keyword search is always available.

## L2 (optional semantic) usage

```bash
python3 shared/cache/semantic.py --status                 # availability + consent state
python3 shared/cache/semantic.py --build                  # build vector index (needs deps + consent)
python3 shared/cache/semantic.py --search "adding parts of a whole" --subject math --k 5
```

Install the optional backend with `pip install -r tools/requirements-semantic.txt`
(`sqlite-vec` + a local embedder such as `sentence-transformers`). No data leaves the
machine — only public standards text is embedded; no student data.

## L3 (manifest-driven sync) usage

`tools/sync_cache.py` keeps the cache fresh and portable by reusing existing engines —
the F2 currency checker (`tools/source_currency.py`) for upstream web-source freshness,
the L1 sha256 baseline for local drift, and a Scoop-style **bucket manifest** for
distribution. Human-approved by default: `--sync` is a dry-run; rebuilding needs
`--apply`; moving upstream baselines stays behind `source_currency.py --update-baselines`.

```bash
python3 tools/sync_cache.py --status --offline      # combined upstream + local + L2 view
python3 tools/sync_cache.py --manifest --write bucket.manifest.json   # portable, hash-verified
python3 tools/sync_cache.py --sync                  # dry-run: what would rebuild
python3 tools/sync_cache.py --apply                 # rebuild L1 (+ L2 if opted-in & ready)
```

The status view surfaces the F2 baseline gap honestly: until
`source_currency.py --update-baselines` is run (human-approved), upstream sources read
`uncertain` rather than guessing they changed.
