# Schools + programs index (canonical)

A district directory of **schools** and their **magnet/choice programs** — public, NON-PII reference data
the rest of the ecosystem can resolve against (a teacher profile's school, a family-communication letter's
campus, a transfer's destination). It is reference data, not a system of record.

## What's authoritative
- **School list + open/closed status:** the **FLDOE MSID** (Master School Identification) file — canonical
  for every Florida school, its district number (Orange = **48**), level, and status. MSID id = `DDSSSS`
  (2-digit district + 4-digit school).
- **Magnet/choice programs:** the **district** site (for OCPS, *School Choice*). Programs open, pause, and
  get eliminated independently of the school.

## Layout
- `shared/schools/<district>/schools.json` — the committed snapshot (e.g. `ocps/`). Validates against
  `schools.schema.json`. Carries `completeness: seed | partial | complete` so coverage is never overstated.
- `shared/schools/schools.py` — offline loader + query (list/filter by level/type/status, magnet lookup,
  MSID/name find, coverage stats).

## How it stays current
Schools open and close regularly, so the index is **monitored, not assumed**: the source-currency engine
(`tools/source_currency.py` + `shared/sources/ocps-schools.json`) watches the MSID file and the OCPS
School Choice page and flags `changed / removed_404 / superseded / stale_age`. A flagged change is
**advisory + human-verified** before the index is updated. Bulk population of the full ~200-school index
is a crawl job (`tools/standards_refresh.py` / the traversal crawler — firecrawl renders the JS OCPS
pages); the seed file here exists to exercise the engine until that runs.

## Governance
- **Public, non-PII only.** Never store student data or unconsented staff PII here (staff is the separate,
  gated `shared/staff/` workstream).
- **Provenance.** Every record carries `source` + `verified` (the date it was last checked against the
  authority). Unverified seed values are labelled and must not be relied on.
- **Honest coverage.** `completeness` + `--stats` always disclose that the seed is a sample, not the
  whole district. `human_review_required: true` on programmatic output.
