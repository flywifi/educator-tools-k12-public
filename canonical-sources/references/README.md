<!-- last_reviewed: 2026-07-15 | owner: reference-data-maintainer -->
# canonical-sources/references — authoritative reference corpora

Verbatim reference data traced to a real, cited source. Skills embed **found** rows from here (never
generated values), so a lookup can't hallucinate a course code, a standard, or a taxonomy level.

## What's here (each carries `provenance`)
| file | what it is | provenance |
|---|---|---|
| `fl-course-codes.json` | 4,607 FL course codes/titles (~1 MB) | FLDOE Course Code Directory |
| `toolkit-content/*.json` | standard → CPALMS toolkit resource links | CPALMS instructional toolkits |
| `fl-instructional-toolkits.json` | the toolkit **subject catalog** (read separately from `toolkit-content/`) | CPALMS |
| `fl-feaps.json` | FL Educator Accomplished Practices | FLDOE Rule 6A-5.065, F.A.C. |
| `blooms-taxonomy.json` | revised Bloom's levels | Anderson & Krathwohl (2001) |
| `webbs-dok.json` | Webb's Depth of Knowledge | Webb (1997), CCSSO/WCEPS |
| `cast-udl-3.0.json` | UDL Guidelines 3.0 | CAST (2024), udlguidelines.cast.org |
| `coxhead-awl.json` | Academic Word List | Coxhead (2000), TESOL Quarterly |
| `private-school-associations.json` | FL private-school affiliations | FLDOE affiliation picker |

## How it's consumed
Most of these feed the **offline reference index** (`canonical-sources/index/`, see its README) for
zero-token, deterministic lookups. Results are advisory + carry provenance; standards/courses should
still be verified on CPALMS.

## Non-negotiable invariants / gotchas
- **Editing any indexed source here requires an index rebuild.** `fl-course-codes.json`,
  `toolkit-content/*.json`, and `fl-instructional-toolkits.json` are fingerprinted in
  `canonical-sources/index/index-manifest.json` — after editing, run
  `python3 tools/offline_index.py --build` and commit the manifest, or `tools/sync_check.py` **check
  14** fails. (Most producer tools rebuild automatically.)
- **Never edit values to "fix" a lookup.** These are verbatim from a cited source; correct the source
  trace, don't invent data.
