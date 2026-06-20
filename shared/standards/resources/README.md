# Standards resources

External standards/assessment resources the ecosystem draws on, **stored as canonical references**
alongside their source information.

## Layout
- `florida/` — the Florida snapshot (104 files: standards, assessment specs, writing rubrics,
  accommodations, WIDA/ELD, civics, admin), organized by category subfolder.
- `florida/sources.json` — the **manifest**: per file → category, size, **sha256**, and its
  **official source** (CPALMS / FLDOE / WIDA), plus `crawl_seeds` and `authorities`.
- `florida-2025-26.md` — the human-readable catalog. Adapter: `../florida-best.md`.

## Snapshot vs. live (staying current)
The stored files are a **dated 2025–26 snapshot**. The **live authority** is the source recorded in
the manifest — **CPALMS (`cpalms.org`)** for standards, **FLDOE (`fldoe.org`)** for assessments,
**WIDA (`wida.wisc.edu`)** for ELD. Always prefer the live source when verifying a code or pulling a
newer document (`protocols/standards-verification.md`).

## Refreshing (crawl the sources for updates)
`tools/standards_refresh.py` reads `sources.json` and recursively crawls the canonical sources for
newer documents, comparing against the stored sha256 hashes:

```bash
python3 tools/standards_refresh.py --check                 # offline: validate + show the crawl plan
python3 tools/standards_refresh.py --crawl                 # report NEW / CHANGED docs (needs network)
python3 tools/standards_refresh.py --crawl --download out/ # fetch the updates into out/
```
After downloading updates: drop them into the right `florida/<category>/` folder, re-run the import to
refresh `sources.json` (hashes), bump the snapshot date in the catalog, and re-verify any cited codes
on CPALMS.

## Adding another state
Mirror this folder (`<state>/` + `sources.json` + a catalog) and a `<state>-best`-style adapter,
following `../state-standards-model.md`. Florida is the template.

## Size note
This corpus is ~108 MB of public Florida DOE/CPALMS/WIDA documents, stored deliberately as offline
references. If repo size becomes a concern, migrate `florida/` to git-LFS or Release assets — the
manifest + refresher work unchanged.
