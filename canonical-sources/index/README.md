# Offline reference index — zero-token lookups

`tools/offline_index.py` builds a local SQLite **FTS5** index (`offline.db`, a gitignored,
regenerable build artifact) over every committed FL reference corpus, so skills answer reference
questions with a **deterministic tool call** instead of loading the corpus into the model's context
or recalling it from memory (which costs tokens and risks hallucination).

```bash
python3 tools/offline_index.py --build     # (re)build from the canonical JSON
python3 tools/offline_index.py --stats     # row counts + token-savings table
python3 tools/offline_index.py --course "Precalculus Honors"
python3 tools/offline_index.py --standards "fractions" --grade 3 --subject math
python3 tools/offline_index.py --school "Boone" --district 48
python3 tools/offline_index.py --resource SC.5.P.10.1     # CPALMS toolkit links for a standard
python3 tools/offline_index.py --source assessment        # authoritative data endpoints
```

## What's indexed (12,911 rows)

| table | rows | source |
|---|---|---|
| `standards` | 6,583 | `shared/standards/resources/florida/data/*.json` |
| `courses` | 4,607 | `canonical-sources/references/fl-course-codes.json` |
| `schools` | 712 | `canonical-sources/schools/*/schools.json` |
| `toolkit_resources` | 949 | `canonical-sources/references/toolkit-content/*.json` (standard → CPALMS link) |
| `data_sources` | 60 | `canonical-sources/registries/fldoe-data-sources.json` |

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

**Whole corpus ≈ 1,012,896 tokens; a typical lookup returns ≈100–350.** That is a **~99.9% reduction
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
should still be verified on CPALMS. Rebuild after any change to the underlying canonical JSON;
`--stats` reports freshness and counts.
