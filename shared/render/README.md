# shared/render — resilient render prongs for JS-required public pages

When the polite stdlib crawler (`tools/standards_refresh.py`) flags a page `js_required` (a
JavaScript Single-Page App such as the CPALMS standards search), this engine recovers the content
through a chain of **redundancy prongs**, offline-first, first-success-wins:

| # | Prong | What it does | Capability gate | Offline? |
|---|---|---|---|---|
| 1 | `http_static` | stdlib/`requests` fetch (the existing polite path) | builtin | n/a (network) |
| 2 | `local_render` | LOCAL Playwright Chromium runs the page's **own JS**, returns rendered HTML | `local_render` (playwright; Chromium pre-installed at `/opt/pw-browsers`) | render needs net; parse is local |
| 3 | `offline_docintel` | persist the best HTML (or a downloaded full page/site + linked docs) and structure it through `shared/docintel` | builtin (`pdf_hifi`/`read_any_markitdown` improve it) | ✅ fully offline |
| 4 | `screenshot_ocr` | Playwright full-page screenshot → docintel OCR (tesseract) | `local_render` + `ocr` | ✅ parse offline |
| 5 | `cloud_render` | firecrawl managed render — **off by default**, opt-in + configured | `cloud_web_crawl` (FIRECRAWL_*) | ✗ cloud |

## Ethics — render, not evasion
Every prong sends the **same single honest, identifying User-Agent** and **respects robots.txt**.
The browser prongs simply run the site's own JavaScript the way a browser is meant to. There is
deliberately **no** User-Agent rotation, **no** browser impersonation, and **no** CAPTCHA /
rate-limit bypass — a detected CAPTCHA wall **stops** the chain and is reported honestly, never
defeated. This mirrors the design table in
`skills/standards-updater/references/updater-method.md`.

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
capability (`tools/requirements-docintel.txt`).

## Programmatic use
```python
import sys; sys.path.insert(0, "shared")
import render
rep = render.resilient_fetch("https://www.cpalms.org/...", out_dir="out/")
print(rep["prong_succeeded"], rep["confidence"], len(rep["text"]))
```

The crawler calls this automatically for `js_required` pages; disable with
`tools/standards_refresh.py --no-render-fallback`.
