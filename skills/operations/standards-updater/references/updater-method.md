# updater-method.md
## The standards-update workflow + crawler design

Keeps the stored standards corpus current. The crawler design adapts a robots-respecting
**detect → polite-crawl → report** pattern, deliberately **without** the evasive parts (a standards
updater hits public `.gov` sources, so it stays transparent and compliant).

## Coverage (every Florida change vector)
From `resources/florida/sources.json` (`coverage`, `crawl_seeds`, `watch_pages`):
- **standards** (CPALMS B.E.S.T./NGSSS) · **courses & curriculum** (CTE frameworks + course descriptions)
- **pacing & guidance** (Technical Assistance Papers + DPS memos) · **instructional materials**
- **assessment** (FAST/B.E.S.T./EOC/FCLE) · **graduation requirements** (s.1003.4282 F.S.)
- **legislation** (FL Statutes Title XLVIII, ch.1000–1013) · **State Board rules** (FAC 6A)
- **English learners** (WIDA/ELD) · **additional resources** (CPALMS/FLDOE resource pages)

Two detection modes: **document discovery** (new/changed files found via `crawl_seeds`) and
**content-change monitoring** (sha256 of `watch_pages` — statute/rule/guidance/graduation/curriculum
index pages — to catch policy edits that aren't new files). `--update-hashes` saves the baselines.

## Change intelligence (triage → verify → brief)
Detection finds *what moved*; this turns it into *what matters*. The policy is config in
`sources.json → monitoring_policy` (a regulatory-intelligence pattern adapted to Florida education):

1. **Discover broadly, but verify on a PRIMARY source.** Secondary sources (news, association
   summaries, blogs) are discovery only — never a basis for inclusion. Sources are classed
   `primary` (CPALMS, FLDOE, the Legislature, FAC/flrules.org, WIDA) vs `discovery_only`. An item
   that can't be confirmed on a primary source goes to **gaps**, not results.
2. **Weigh recency two ways** (`recency_policy`): flag items published in the last **90 days**, AND
   older items whose **effective/enforcement date** falls in the **forward-looking window (≈2 years)** —
   e.g., a statute adopted now that takes effect in 2026-27 matters *now*.
3. **Score confidence** (`confidence_model`): `high` (primary source states it directly) ·
   `medium` (clear but scope needs interpretation) · `low` (partial access / ambiguity / conflict).
4. **Brief the impact.** For each confirmed change write *why it matters* against the
   `impact_dimensions` (standards · courses/curriculum · pacing/guidance · instructional materials ·
   assessment · graduation · EL · policy/compliance) — e.g. "FAC 6A rule edit → graduation pathways →
   update pacing + diploma-designation guidance." Output is a **currency brief** (see
   `references/artifact-types.md`): JSON package + a short human-readable brief. Confirmed facts stay
   separate from inference; conflicts go to gaps.

## What we borrowed (and what we did not)
| Pattern (from a scraper design) | Adopted here | Why |
|---|---|---|
| robots.txt analysis | ✅ respect + skip disallowed | compliance |
| polite crawling (random 2–4s delays) | ✅ randomized jitter delays | be a good citizen |
| any-obstacle detection (HTTP error, bot gate, low confidence, encoding issue, rate-limit — not only JS) | ✅ `_score_confidence()` + expanded `detect()` in `shared/render` | fallbacks fire on ANY obstacle or confidence < 0.95, not only when js_required is flagged |
| JS-required detection (`noscript`, "enable javascript", tiny page) | ✅ detect + **escalate** | CPALMS *search* is a JS SPA; one of many trigger conditions — escalates to the render prong chain |
| **LOCAL browser render** of a js_required or low-confidence page | ✅ `shared/render` prong 2 (Playwright + pre-installed Chromium) | run the site's OWN JavaScript the way a browser is meant to — this is rendering, not impersonation |
| **download full HTML + offline docintel parse** | ✅ `shared/render` prong 3 (reuses `shared/docintel`) | structure the page (and linked docs) fully offline; zero further requests |
| **screenshot → OCR** of the rendered page | ✅ `shared/render` prong 4 (Playwright capture + docintel/tesseract OCR) | last-resort offline recovery for canvas/image-only content |
| **managed cloud render** (firecrawl) | ✅ `shared/render` prong 5 — **off by default**, opt-in (`--render-enable-cloud`) | offline prongs are preferred; cloud only when explicitly enabled + configured |
| **multi-prong aggregation → single contract** | ✅ `_aggregate_results()` in `shared/render` | when multiple prongs succeed, results are compared and merged; the highest-agreement version is returned as the handoff contract |
| **minority report on prong discrepancy** | ✅ `ledger/render-discrepancy-log.json` + `minority_report: true` flag | when prongs disagree (token overlap < 0.70), the discrepancy is logged for audit; never suppressed |
| **Wayback Machine archive comparison** | ✅ `_wayback_compare()` in `shared/render` (archive.org CDX API, no auth) | after aggregation, compare current content against archived snapshot to confirm genuine change vs. transient failure; detect removed pages (`page_removed: true`) |
| rate-limit detection (429 / latency) | ✅ detect + **back off** | never hammer a public site |
| **honor `Retry-After` / `RateLimit-Reset`** | ✅ wait the server's own backoff (bounded retry) | use the platform's published limit, not a guess |
| **resumable checkpoint** (frontier + visited) | ✅ `--checkpoint` / `--resume` | a long crawl can pause/resume without re-hammering |
| **saturation / stop rule** | ✅ `--saturation N` (stop when no new docs appear) | don't crawl deeper than the evidence justifies |
| realistic headers | ✅ Accept/Accept-Language | basic compatibility |
| structured JSON report | ✅ timestamped report | auditable, reviewable |
| **User-Agent rotation / browser impersonation** | ❌ **not used** | one honest UA; we identify ourselves, not evade. The render prongs above use the SAME honest UA |
| **CAPTCHA bypass / rate-limit bypass** | ❌ **not used** | bypassing protections is out of scope/unethical. A detected CAPTCHA STOPS the render chain — reported, never defeated |

## The tools
- `tools/standards_refresh.py` — the crawler/reporter (`--check` offline, `--crawl`, `--download`,
  `--report`). Reads `crawl_seeds` from each state's `sources.json`. Stdlib-only; uses
  `requests`/`bs4` if installed (`tools/requirements-scraper.txt`). Hardened crawl options:
  `--max-retries` (honor `Retry-After`/`RateLimit-Reset`), `--saturation N` (stop when no new docs),
  `--checkpoint PATH` + `--resume` (resumable), `--max-wait` (cap a single backoff). When a page is
  `js_required`, the render fallback runs automatically (`--no-render-fallback` to disable,
  `--render-out DIR` to save artifacts, `--render-enable-cloud` to also allow the cloud prong).
- `shared/render/render_prongs.py` + `tools/render_fetch.py` — the resilient render prong chain for
  js_required pages: **LOCAL browser render → offline docintel parse → screenshot+OCR → optional
  cloud**, first-success-wins (or `--all` for redundancy). Capability-gated (`local_render` = Playwright,
  `ocr` = tesseract, `cloud_web_crawl` = firecrawl); honest gaps when deps are absent; same honest UA,
  robots respected, CAPTCHA never bypassed. `python3 tools/render_fetch.py --check` lists prong availability.
- `tools/docintel_run.py` + `shared/docintel/` — the offline document-ingestion pipeline the render
  prongs reuse (PDF/HTML/.docx/image+OCR → governed knowledge artifact).
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

## Staleness monitoring (`tools/source_currency.py`)
The crawler above finds NEW/CHANGED files; the source-currency engine is its complement — it watches the
authoritative *web sources* for going stale, moving, being superseded, or disappearing:
`python3 tools/source_currency.py --summary` classifies each watched source in
`canonical-sources/registries/<domain>.json` as `current · changed · superseded · removed_404 · stale_age ·
unreachable · uncertain` (conditional GET + content sha256 + supersession sentinel keywords +
recency/effective-date + a 404 sweep), and emits a stale-source list with a reason + recommended action.
It degrades to age-only triage offline and **never fabricates** a change — every standards/legal/program
change stays advisory until verified on the PRIMARY source. After a human approves, record new baselines
with `--update-baselines --domain <domain>`. (Internal drift of the source list itself is watched by
`tools/registry_currency.py`.)

## Cadence
Run before a new school year and when a source announces revisions (e.g., Florida's standalone CS
standards). The standards *content* changes rarely; assessment fact sheets/schedules change yearly —
the live FLDOE/CPALMS pages always hold the newest. Run `source_currency.py` on a regular cadence (e.g.,
monthly) to catch sources that quietly go stale or disappear between school-year refreshes.

## Failure handling (`protocols/failure-recovery.md`)
If a source is unreachable, JS-gated, or robots-disallowed: **report it and stop** for that source —
do not bypass. Fall back to the static downloads page / CDN, or a human pull. Never fabricate a
"latest" version.
