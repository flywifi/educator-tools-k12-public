# shared/render — resilient render prongs for hard-to-scrape public pages

Fallback prongs are **not limited to JS-required pages**. They activate whenever there is *any
obstacle* (HTTP error, bot gate, encoding issue, rate-limit, empty/garbled body) OR when retrieval
**confidence falls below 0.95**. Multiple prongs run and their results are **aggregated** into a
single high-confidence handoff contract. Discrepancies between prongs go to the **minority report**
and `ledger/render-discrepancy-log.json` for auditing.

After aggregation, the **Wayback Machine CDX API** is queried (when network is available) to compare
the current page content against the most recent archived snapshot — confirming whether the page
genuinely changed, was removed, or whether the current fetch is unreliable.

| # | Prong | What it does | Capability gate | Offline? |
|---|---|---|---|---|
| 1 | `http_static` | stdlib/`requests` fetch (the existing polite path) | builtin | n/a (network) |
| 2 | `local_render` | LOCAL Playwright Chromium runs the page's **own JS**, returns rendered HTML | `local_render` (playwright; Chromium pre-installed at `/opt/pw-browsers`) | render needs net; parse is local |
| 3 | `offline_docintel` | persist the best HTML (or a downloaded full page/site + linked docs) and structure it through `shared/docintel` | builtin (`pdf_hifi`/`read_any_markitdown` improve it) | ✅ fully offline |
| 4 | `screenshot_ocr` | Playwright full-page screenshot → docintel OCR (tesseract) | `local_render` + `ocr` | ✅ parse offline |
| 5 | `cloud_render` | firecrawl managed render — **off by default**, opt-in + configured | `cloud_web_crawl` (FIRECRAWL_*) | ✗ cloud |
| post | `web_archive` | Wayback Machine CDX comparison — confirms change vs. archived snapshot | `web_archive` (waybackpy optional; urllib fallback) | ✗ network to archive.org |

## Trigger conditions (NOT only js_required)

The fallback chain escalates on **any** of these:

| Trigger | Condition |
|---|---|
| `js_required` | noscript tag / "enable javascript" text / body < 500 bytes |
| `http_error` | HTTP 4xx / 5xx response |
| `low_confidence` | `_score_confidence()` < threshold (default 0.95): empty body, garbled encoding, no headings, tiny byte count |
| `obstacle` | bot gate, "access denied", maintenance mode, 401/403/503 |
| `rate_limited` | HTTP 429 / Retry-After — back off and re-run after wait |
| `parse_failure` | HTML parser returns no extractable text or malformed structure |

## Aggregation and minority report

When multiple prongs succeed, `_aggregate_results()` compares their text content (token overlap).
If two prongs return meaningfully different content (overlap < 0.70):

- `minority_report: true` is set in the handoff contract
- The discrepancy is appended to `ledger/render-discrepancy-log.json`
  (`{ts, url, field, prong_a, prong_b, value_snippets, overlap_ratio}`)

When prongs **agree** (overlap ≥ 0.80), a confidence bonus (+0.20) is applied to the merged result.

## Web archive comparison

`_wayback_compare(url, current_html)` calls the archive.org CDX API (free, no auth) after the
prong chain completes. It returns:

- `archived_at` — timestamp of the most recent snapshot
- `overlap_score` — word-set overlap between current and archived content
- `page_removed` — True if current fetch is empty but archive has content
- `changed` — True if overlap < 0.70
- `stable` — True if overlap ≥ 0.85

This lets the caller distinguish **genuine page change** from a transient fetch failure.
Degrades gracefully when network is unavailable (returns `available: false`).

## Ethics — render, not evasion
Every prong sends the **same single honest, identifying User-Agent** and **respects robots.txt**.
The browser prongs simply run the site's own JavaScript the way a browser is meant to. There is
deliberately **no** User-Agent rotation, **no** browser impersonation, and **no** CAPTCHA /
rate-limit bypass — a detected CAPTCHA wall **stops** the chain and is reported honestly, never
defeated. This mirrors the design table in `skills/standards-updater/references/updater-method.md`.

## Capability-gated, honest gaps
A prong whose dependencies are absent is **skipped and recorded as a `capability_gap`**, never
faked. With nothing installed, the chain still recovers static HTML and runs the offline docintel
parse; with Playwright it adds local render + screenshots; with tesseract it adds OCR. Output always
carries `human_review_required: true`.

```bash
python3 tools/render_fetch.py --check                 # list prongs + availability (offline)
python3 tools/render_fetch.py <url> --out out/        # run the chain; save artifacts
python3 tools/render_fetch.py <url> --all             # run every available prong (redundancy)
```

Install the local render prong with `tools/requirements-render.txt` (do **not** run
`playwright install` — Chromium is already at `/opt/pw-browsers`). OCR comes from the existing `ocr`
capability (`tools/requirements-docintel.txt`). Crawl/archive tools from `tools/requirements-crawl.txt`.

## Programmatic use
```python
import sys; sys.path.insert(0, "shared")
import render
rep = render.resilient_fetch("https://www.cpalms.org/...", out_dir="out/",
                              confidence_threshold=0.95)
print(rep["prong_succeeded"], rep["confidence"], rep["minority_report"])
print(rep["wayback_compare"])   # archive comparison result
```

The crawler calls this automatically for pages that trigger any obstacle or low confidence;
disable with `tools/standards_refresh.py --no-render-fallback`.
