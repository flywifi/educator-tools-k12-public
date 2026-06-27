# Source-currency registries (`shared/sources/`)

Domain registries of **authoritative web sources** to monitor for freshness. The engine
`tools/source_currency.py` reads each `<domain>.json` here, fetches every source with a polite
conditional GET, and classifies a **freshness state** with a reason + recommended action.

This is the **external** counterpart to `tools/registry-sources.json` / `tools/registry_currency.py`
(which watch *internal* files for drift). The two compose: `registry_currency` watches the source-list
file itself drifting; `source_currency` watches the live sources it points to.

## Freshness states
| state | meaning |
|-------|---------|
| `current` | reachable + unchanged (HTTP 304, or content sha256 matches the recorded baseline) |
| `changed` | reachable + content hash differs from baseline — re-verify, then re-baseline |
| `superseded` | a supersession/"rescinded/repealed/archived/program eliminated" keyword found, or a `superseded_by` link is recorded |
| `removed_404` | HTTP 404/410 — the page/program is gone |
| `stale_age` | last verified longer ago than `stale_age_days` (or a passed effective date never verified) |
| `unreachable` | transport error / 5xx / robots-disallowed — could not verify (≠ gone) |
| `uncertain` | no fetch capability (offline / deps absent) or ambiguous — an honest gap |

## Detection (multi-pronged)
Conditional GET (ETag/`If-None-Match` + Last-Modified/`If-Modified-Since`) · normalized content sha256 ·
supersession sentinel keywords · recency/effective-date · 404/410 sweep. RSS/Atom (`type: feed`) and
sitemap (`type: sitemap`) sources are recognized and parsed when reachable.

## Registry shape
```json
{
  "domain": "florida-standards",
  "freshness_policy": {"stale_age_days": 365, "supersession_keywords": ["rescinded", "..."]},
  "sources": [
    {"id": "...", "url": "...", "label": "...", "category": "legislation|standards|program|directory",
     "authority": "primary|secondary", "type": "page|feed|sitemap",
     "state": {"etag": null, "last_modified": null, "content_sha256": null, "last_checked": null,
               "last_status": null, "effective_date": null, "superseded_by": null}}
  ]
}
```

## Usage
```bash
python3 tools/source_currency.py --summary                    # all domains, human-readable + stale list
python3 tools/source_currency.py --check --domain florida-standards   # JSON report
python3 tools/source_currency.py --offline                    # age-only triage, no network
python3 tools/source_currency.py --update-baselines --domain florida-standards   # after human approval
```

## Governance
Standards/legal/program changes are **advisory + human-verified** — flagged with a reason, never
auto-applied and never fabricated. Offline, the engine degrades to age-only triage rather than guessing.
Nothing re-baselines without a human (`--update-baselines`). `human_review_required: true` on every
report. Only PRIMARY sources count for a confirmed change; secondary sources are discovery-only.
