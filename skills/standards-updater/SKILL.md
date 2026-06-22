---
name: standards-updater
description: "Keep the stored Florida education corpus current by politely crawling the official sources for ANY change to what we cover — standards, courses/curriculum (incl. CTE frameworks), pacing, guidance documents (TAPs/memos), additional resources, instructional materials, assessment, graduation requirements, legislation (Florida Statutes Title XLVIII), and State Board rules (Florida Administrative Code 6A). Use this whenever someone wants to update, refresh, re-check, or 'pull the latest' for any of those — e.g. 'check CPALMS/FLDOE for new Florida standards', 'did the legislature or State Board change anything?', 'are our pacing/guidance docs current?', 'is our B.E.S.T. data up to date for the new school year?', or 'set up the standards updater'. It runs the polite, robots-respecting crawler (tools/standards_refresh.py) against the canonical sources in sources.json, reports NEW/CHANGED documents AND content changes on watched pages (legislation, rules, guidance, graduation) vs. stored sha256 hashes, and walks a human through verifying on CPALMS and applying updates (re-enumerate with tools/parse_fl_standards.py). Make sure to use this for standards/curriculum/policy maintenance & currency. Do NOT use it to generate lessons/assessments (use the capability skills), and it is NOT a general or evasive web scraper — it only crawls public official sources, respects robots.txt, and backs off rather than bypassing protections."
---

# standards-updater

Maintains the currency of everything we cover for Florida (and any state via the same pattern). It is
a **polite, transparent, compliant crawler of public official sources** — never an evasion tool.

**Coverage — watches all Florida change vectors** (see `resources/florida/sources.json` → `coverage`):
standards (CPALMS B.E.S.T./NGSSS) · courses & curriculum (CTE frameworks, course descriptions) ·
pacing & guidance (Technical Assistance Papers, DPS memos) · instructional materials · assessment
(FAST/B.E.S.T./EOC/FCLE) · graduation requirements · **legislation** (Florida Statutes Title XLVIII,
ch.1000–1013) · **State Board rules** (Florida Administrative Code 6A) · English learners (WIDA/ELD) ·
additional resources.

> **Ethics & boundaries (read first).** Only crawl the **public official sources** recorded in a
> state's `resources/<state>/sources.json` (`crawl_seeds`): CPALMS, FLDOE, WIDA, state DOEs.
> **Respect robots.txt**, use one honest identifying User-Agent (no browser-impersonation/rotation),
> crawl politely (randomized delays), and **back off — never bypass** — on robots disallow, rate
> limits (429), CAPTCHA, or JS-required pages. No CAPTCHA bypass, no aggressive testing. **Standards
> changes are never auto-applied:** a human verifies each change on CPALMS and approves it.

## Pipeline (`references/method.md`)
1. **Analysis** — which state/subject to refresh (default Florida). Log assumptions.
2. **Detect & crawl** — run the updater, which reads the seeds and reports findings:
   ```bash
   python3 tools/standards_refresh.py --crawl --report /tmp/fl_update_report.json
   # add --download /tmp/updates/ to fetch the new/changed docs
   ```
   It respects robots.txt, detects **JS-required** pages (e.g., the CPALMS *search* SPA) and reports
   them instead of faking a scrape, and notes rate-limited/skipped URLs. For JS pages, use the static
   **downloads** page / CDN, or a browser-rendered fetch (Selenium/Playwright — see
   `tools/requirements-scraper.txt`). It also **hashes `watch_pages`** (statutes, FAC 6A rules,
   guidance, graduation, CTE frameworks) to catch *content* changes (legislation/rule/policy edits),
   not just new files — run with `--update-hashes` to save baselines.
3. **Review** the report (NEW / CHANGED / js_required / skipped_robots / errors).
4. **Verify on CPALMS** — the live authority (`https://www.cpalms.org/search/Standard`). Never trust
   a crawled change without confirming it (`protocols/standards-verification.md`). Never invent codes.
5. **Apply (human-approved)** — drop accepted files into `resources/<state>/<category>/`, then
   re-enumerate and refresh hashes:
   ```bash
   python3 tools/parse_fl_standards.py     # re-extract the queryable standards JSON
   python3 tools/sync_check.py             # drift guard
   ```
   Update `sources.json` (hashes/date), the catalog, `STATE.md`, and `CHANGELOG.md`.
6. **Quality gate** — self-check against `references/quality-gates.md`, then hand to `quality-review`.

## Output: always emit the metadata/update record
Produce an **update record** per `protocols/metadata-schema.md`: what was crawled, NEW/CHANGED found,
what was verified on CPALMS, what was applied, and `human_review_required: true`. Placeholder/public
data only — no PII.

Artifact types: `references/artifact-types.md`. Detailed workflow + the borrowed crawler design:
`references/updater-method.md`.
