# artifact-types.md
## Artifacts produced by standards-updater

Maintenance artifacts (not student-facing). Each carries the metadata block + `human_review_required`.

### Update report
- **Purpose:** the result of a crawl — what's current vs. the stored snapshot.
- **Required elements:** timestamp; sources crawled; **NEW** docs; **CHANGED** docs (sha256 differs);
  `js_required` / `skipped_robots` / `rate_limited` / `errors`; a recommendation. Produced by
  `tools/standards_refresh.py --crawl --report <path>`.

### Applied-update record
- **Purpose:** the auditable record of an update that was *verified and applied*.
- **Required elements:** which files were added/replaced; **what was verified on CPALMS** (with the
  code/URL); the re-enumeration result (counts from `parse_fl_standards.py`); refreshed `sources.json`
  hashes; `human_review_required: true`. Logged like a decision record (`protocols/metadata-schema.md`).

### Currency check (read-only)
- **Purpose:** a quick "are we current for school year N?" answer without applying anything.
- **Required elements:** the `current_school_year` from `sources.json`, the crawl summary, and a
  yes/needs-update verdict.

## Validation (extends `shared/quality/verification-checklists.md`)
- Only public official sources were crawled; robots.txt respected; no bypass/evasion.
- Every applied standards change was **verified on CPALMS** (no invented codes).
- Hashes + the enumerated data (`resources/florida/data/`) were refreshed; drift guard passes.
- `human_review_required: true`; no PII.
