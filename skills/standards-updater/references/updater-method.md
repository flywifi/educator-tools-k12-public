# updater-method.md
## The standards-update workflow + crawler design

Keeps the stored standards corpus current. The crawler design adapts a robots-respecting
**detect → polite-crawl → report** pattern, deliberately **without** the evasive parts (a standards
updater hits public `.gov` sources, so it stays transparent and compliant).

## What we borrowed (and what we did not)
| Pattern (from a scraper design) | Adopted here | Why |
|---|---|---|
| robots.txt analysis | ✅ respect + skip disallowed | compliance |
| polite crawling (random 2–4s delays) | ✅ randomized jitter delays | be a good citizen |
| JS-required detection (`noscript`, "enable javascript", tiny page) | ✅ detect + **report** | CPALMS *search* is a JS SPA; don't fake it — use downloads/CDN or a browser render |
| rate-limit detection (429 / latency) | ✅ detect + **back off** | never hammer a public site |
| realistic headers | ✅ Accept/Accept-Language | basic compatibility |
| structured JSON report | ✅ timestamped report | auditable, reviewable |
| **User-Agent rotation / browser impersonation** | ❌ **not used** | one honest UA; we identify ourselves, not evade |
| **CAPTCHA bypass / rate-limit bypass** | ❌ **not used** | bypassing protections is out of scope/unethical |

## The tools
- `tools/standards_refresh.py` — the crawler/reporter (`--check` offline, `--crawl`, `--download`,
  `--report`). Reads `crawl_seeds` from each state's `sources.json`. Stdlib-only; uses
  `requests`/`bs4` if installed (`tools/requirements-scraper.txt`).
- `tools/parse_fl_standards.py` — re-enumerate the queryable standards JSON after applying updates.
- `tools/fl_lookup.py` — query the enumerated standards.

## Step-by-step
1. **Crawl + report:** `python3 tools/standards_refresh.py --crawl --report report.json`.
2. **Triage the report:** `new` (filename not in the snapshot), `changed` (sha256 differs),
   `js_required` (fetch via browser/downloads page), `skipped_robots`, `rate_limited`, `errors`.
3. **Verify on CPALMS** before trusting any change (standards are the high-stakes part —
   `protocols/standards-verification.md`).
4. **Download accepted updates:** add `--download out/`; place them in
   `resources/<state>/<category>/`.
5. **Re-enumerate + re-sync:** `parse_fl_standards.py`, then `sync_check.py`; update `sources.json`,
   the catalog, `STATE.md`, `CHANGELOG.md`.
6. **Gate + record:** `quality-review` + an update record with `human_review_required: true`.

## Cadence
Run before a new school year and when a source announces revisions (e.g., Florida's standalone CS
standards). The standards *content* changes rarely; assessment fact sheets/schedules change yearly —
the live FLDOE/CPALMS pages always hold the newest.

## Failure handling (`protocols/failure-recovery.md`)
If a source is unreachable, JS-gated, or robots-disallowed: **report it and stop** for that source —
do not bypass. Fall back to the static downloads page / CDN, or a human pull. Never fabricate a
"latest" version.
