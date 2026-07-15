# Offline reference index — zero-token lookups

`tools/offline_index.py` builds a local SQLite **FTS5** index (`offline.db`, a gitignored,
regenerable build artifact) over every committed FL reference corpus, so skills answer reference
questions with a **deterministic tool call** instead of loading the corpus into the model's context
or recalling it from memory (which costs tokens and risks hallucination).

```bash
python3 tools/offline_index.py --build     # (re)build from the canonical JSON + write the manifest
python3 tools/offline_index.py --verify    # is the index stale vs its sources? (exit 1 if so)
python3 tools/offline_index.py --stats     # row counts + token-savings + freshness
python3 tools/offline_index.py --course "Precalculus Honors"
python3 tools/offline_index.py --standards "fractions" --grade 3 --subject math
python3 tools/offline_index.py --school "Boone" --district 48
python3 tools/offline_index.py --resource SC.5.P.10.1     # CPALMS toolkit links for a standard
python3 tools/offline_index.py --source assessment        # authoritative data endpoints
```

## What's indexed

| table | rows | source |
|---|---|---|
| `standards` | 6,583 | `shared/standards/resources/florida/data/*.json` |
| `courses` | 4,607 | `canonical-sources/references/fl-course-codes.json` |
| `schools` | 712 | `canonical-sources/schools/*/schools.json` |
| `private_schools` | 508 | `canonical-sources/schools/private/*.json` |
| `toolkit_resources` | 1,445 | `canonical-sources/references/toolkit-content/*.json` + `references/fl-instructional-toolkits.json` (standard → CPALMS link) |
| `data_sources` | 60 | `canonical-sources/registries/fldoe-data-sources.json` |

(Counts are also recorded in `index-manifest.json`; regenerate with `--build` if this table drifts.)

## Token reduction — how it's achieved, and how much

**The mechanism.** A reference need (a standard's exact text, a course code, a school's MSID, the
CPALMS resources for a standard) has three ways to be answered:

1. **Put the corpus in the prompt** — e.g. the full course directory is ~1 MB ≈ **272,000 tokens**;
   all standards ≈ **470,000 tokens**. Loading that per call is enormous (often over the context
   limit) and repeats every turn.
2. **Let the model recall it** — cheaper in tokens but unreliable: the model invents plausible
   codes/text (the exact failure this project fought elsewhere).
3. **Look it up in the index** — a tool call returns only the matching rows.

The index makes (3) cheap and exact. **Measured** per-query output (actual `--json` result size ÷ 4
chars/token), against the corpus you would otherwise have to load:

| lookup | corpus tokens (if loaded) | measured lookup tokens | reduction |
|---|---|---|---|
| course code ("Precalculus") | 272,579 | **244** | 99.91% |
| school ("Boone", district 48) | 93,728 | **95** | 99.90% |
| standards ("fractions", gr 3) | 469,986 | **344** | 99.93% |
| toolkit resources (SC.5.P.10.1) | 169,368 | **191** | 99.89% |
| data source ("assessment") | 7,236 | **155** | 97.86% |

**The whole corpus is well over a million tokens** (`--stats` prints the live figure)**; a typical lookup returns ≈100–350.** That is a **~99.9% reduction
per reference need** — and because ~1 M tokens exceeds the context window, the index doesn't just
*save* tokens, it makes corpus-wide reference *possible at all* without an external retrieval step.

### Why it's also more accurate (not just cheaper)
Every row is verbatim from the committed canonical JSON (which itself traces to a real saved
page/export — see each file's `provenance`). The model returns *found* data, never *generated*
data, so a lookup can't hallucinate a course code or standard.

## How a skill uses it (integration)
A capability skill (lesson-planner, assessment-designer, curriculum-mapping, …) that needs a
standard, course code, school, or CPALMS resource calls `offline_index.py` (or imports its `_q`
helper) and embeds only the returned rows. Results are advisory + carry provenance; standards/courses
should still be verified on CPALMS.

## Freshness — why `offline.db` can't silently go stale
The db is gitignored (a 4 MB regenerable binary), so it can't itself signal drift in git/CI. Instead
`--build` writes a **committed** `index-manifest.json` holding the sha256 of every source file it
indexed. Three things then keep the db honest:

1. **`--verify`** (and `--stats`) compare the live sources to the manifest and report STALE if any
   changed — reading only committed files, so it works with no db and on a fresh clone.
2. **The drift guard** (`tools/sync_check.py`, a CI hard gate) fails the build if the index is stale,
   naming the changed files and the one-line fix.
3. **Producers self-heal:** the tools that regenerate an index source (`parse_fl_standards.py`,
   `msid_lookup.py --apply`, and the harvest orchestrators) rebuild the index automatically, so the
   manifest travels with the data change.

**The rule:** after editing any source in the table above, run `python3 tools/offline_index.py
--build` and **commit `index-manifest.json`** alongside the data change. (Most producers do this for
you; the guard catches it if something didn't.)

## Maintainer gotchas (learned the hard way — read before changing the index tooling)

- **The db is content-hashed, not mtime-checked.** Freshness compares sha256 of each source to the
  manifest, so a `touch` with no content change is *not* stale, and a real edit always is. Don't
  "optimize" this to mtimes.
- **`source_files()` is the single source of truth for what's indexed.** If you add a new table to
  `build()`, you MUST add its inputs to `source_files()` too — otherwise the new source isn't
  fingerprinted and can drift undetected. (`build()` and the manifest deliberately share the same
  `_*_files()` helpers so they can't diverge; keep it that way. `stats()` has its own display-only
  path list — never use it as the input set.)
- **Two easy-to-miss inputs:** `canonical-sources/schools/private/*.json` (the `private_schools`
  table) and `canonical-sources/references/fl-instructional-toolkits.json` (the toolkit *subject
  catalog*, read separately from `toolkit-content/`). Both are fingerprinted; if you refactor,
  don't drop them.
- **Manifest keys are POSIX (`as_posix()`), on purpose.** A manifest built on Windows with native
  backslash keys would make Linux/CI read every path as changed (false "stale", red CI for
  everyone). Keep `.as_posix()` on both the write and the compare side.
- **A missing or corrupt `index-manifest.json` is a HARD FAILURE, not a skip.** It's a committed
  baseline; its absence means it was deleted or a write truncated, so `--verify` exits 1 and
  `sync_check` fails. Do not "soften" this back to a note — that reopens a silent bypass
  (`git rm` the manifest → guard goes quiet).
- **Producers rebuild non-fatally with a `--no-index` escape hatch.** `parse_fl_standards.py`,
  `msid_lookup.py --apply`, and the harvest tools rebuild after writing a source. `--no-index`
  skips it (for parse-only runs) — but then YOU must rebuild + commit the manifest, or CI reddens.
  A build hiccup only warns; it never fails the producer.
- **`--build` is destructive + non-atomic:** it `unlink`s and fully recreates `offline.db`, and
  `write_text` on the manifest isn't atomic. A crash mid-build leaves a partial db (fine — it's
  regenerable) and an *unchanged* manifest (write happens only after a clean build), so `--verify`
  correctly still reports stale. Don't move `write_manifest()` inside the build's `try` block.
- **"index fresh" ≠ "db exists."** `--verify` checks sources-vs-manifest, not the db. On a fresh
  clone it can say fresh before any `--build`; the query path still errors `index not built` until
  you build. This is intended.
