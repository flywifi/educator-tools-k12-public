# Changelog
All notable changes to the Teacher Operating System (TOS) ecosystem. Format follows
[Keep a Changelog]; this project uses [Semantic Versioning](https://semver.org/) — see
`CHANGE_MANAGEMENT.md` for the versioning policy.

## [Unreleased]
### Added
- **Offline document reader: scanned-PDF OCR + Florida pipeline on docintel + currency-brief example.**
  (1) **PDF OCR** — `TesseractEngine` now reads **scanned PDFs** by rasterizing each page locally with
  PyMuPDF and OCRing with Tesseract; **fully offline** (no network at run time), activates when the
  optional engines are installed (`tools/requirements-docintel.txt`), and reports an honest gap when
  not. (2) **Florida standards pipeline re-based on docintel** — `tools/parse_fl_standards.py` now
  reads each source through the governed engine (structure + table cells + provenance/retrieval-state),
  and a smarter extractor captures access points that live in table cells; output is **6,583 codes,
  byte-for-byte identical** to the prior reader (no regression), now with a `reader`/`retrieval_state`
  on each subject. (3) **Worked `currency-brief` example** added under `standards-updater/examples/`.
  Hardened optional engines' `available()` against broken-install panics.
- **docintel retrieval-state ladder** (harvested "visibility ≠ extraction" pattern) — every processed
  document now carries a four-step `retrieval_state` (`referenced → metadata_only → content_ingested →
  local_artifact_saved`) in diagnostics, the artifact governance block, and the validation report, so
  a shallow hit is never mistaken for real content (e.g. an image with no OCR engine is
  `metadata_only` + an `ocr` gap, not "recovered"). (`orchestration.retrieval_state`,
  `governance-contract.md`.)
- **`standards-updater` change intelligence** (harvested from a regulatory-intelligence pattern) —
  `sources.json` gains a `monitoring_policy` (PRIMARY-vs-discovery source classes, a
  verify-on-primary rule, a dual recency window incl. **forward-looking effective dates**, a
  confidence model, and impact dimensions). The method now triages detected changes → verifies on a
  primary source → scores confidence → emits a **currency brief** (new artifact type) that says *why
  it matters* per impact dimension, with unconfirmed/conflicting items kept in gaps. (`SKILL.md`,
  `references/updater-method.md`, `references/artifact-types.md`.)
- **Crawler hardening** (`tools/standards_refresh.py`) — honors the server's own backoff
  (`Retry-After` / `RateLimit-Reset`) with bounded retries, a **resumable checkpoint**
  (`--checkpoint`/`--resume`), and a **saturation/stop rule** (`--saturation N`) so a long crawl stays
  under limits and never re-hammers a source. (Also fixed a latent missing `import re`.)
- **Drift-guard skill-health checks** (`tools/sync_check.py`) — harvested (reimplemented stdlib-only)
  from prior skill-tooling: every `SKILL.md` is now validated as an installable Claude Skill —
  frontmatter has only allowed keys, `name` is clean hyphen-case == folder name and ≤64 chars,
  `description` is present, ≤1024 chars, and free of angle brackets — plus **resource integrity**:
  every backticked repo path (with a known extension) referenced in a `SKILL.md` must resolve to a
  real file under the skill dir or repo root. Fixed 3 descriptions that exceeded the 1024-char spec
  (`standards-updater`, `document-intelligence`, `special-education-support`).
- **Google Workspace document types** for `document-intelligence` — read Google Docs/Sheets/Slides
  with **stdlib only**. `shared/docintel/google.py` adds `GoogleDocsParser`, which parses the native
  Google Docs API JSON (`documents.get`: title, headings via `namedStyleType`, paragraphs, tables)
  into UDOM, content-sniffed so non-Docs JSON isn't mis-parsed; plus the Drive `files.export` MIME
  map. `shared/docintel/parsers/workspace_parsers.py` adds the export-format parsers: `OdtParser`
  (`.odt`, incl. merged cells), `CsvParser` (`.csv`/`.tsv`), `XlsxParser` (`.xlsx`, resolves
  sharedStrings, one table per sheet), `PptxParser` (`.pptx`, one page per slide). Media types wired
  in `guess_media_type`; canonical doc `google-workspace.md`. Boundary: no Drive/OAuth fetching —
  bring the exported file or the API JSON. `.ods`/`.odp` + Sheets/Slides API JSON are staged.
- **OCR & image handling (V02_S04)** for `document-intelligence` — image inputs
  (`png/jpeg/gif/bmp/tiff/webp`) are recognized and analyzed with **stdlib only** (format +
  dimensions via `shared/docintel/images.py` + `parsers/image_parser.py`), and a new **targeted OCR
  stage** (`shared/docintel/ocr.py` + `ocr-architecture.md`) recovers confidence-aware text only when
  native extraction is insufficient (image inputs, text-less/scanned pages). OCR engines are swappable
  behind an `OcrEngine` contract; `TesseractEngine` activates when `pytesseract`/`Pillow` are installed.
  When OCR is needed but no engine is available the pipeline reports `capability_gaps: ["ocr"]` and
  **never fabricates text**; PDF OCR (rasterize + OCR) is staged via `StageNotImplemented`. Stage is
  feature-flaggable (`flags["ocr"]`).
- **Table Intelligence (V02_S06)** for `document-intelligence` — a dedicated, swappable table stage
  (`shared/docintel/tables.py` + `table-intelligence.md`). Detects/reconstructs/normalizes tables into
  UDOM `Table`/`Cell`: rows, columns, **header rows**, and **merged cells** (HTML colspan/rowspan,
  DOCX `gridSpan`/`vMerge`) via occupancy-aware placement, with **table- and cell-level confidence**
  (new `Confidence.level` values `table`/`cell`) and conflict handling (ragged/merge). Engines are
  swappable behind a `TableExtractor` contract: `StdlibTableExtractor` (docx/html/markdown, always on)
  and `PdfPlumberTableExtractor` (PDF, activates when `pdfplumber` is installed). The text parser now
  skips table regions so content isn't double-counted; validation computes `A-003` table recovery.
- **`document-intelligence` skill + `shared/docintel/` engine** — a TOS-native Document Intelligence
  Platform (built from the uploaded V01–V09 architecture): documents in → **governed knowledge
  assets** out. Parser-**independent** (swappable plugins behind one `Parser` contract) and
  artifact-centric. Full-framework skeleton, runs end to end: **UDOM** (`udom.md` +
  `udom.schema.json` + `udom.py`), **Parser Orchestration** (`parser-orchestration.md` +
  `orchestration.py` + `parsers/`), **Governance** (`governance-contract.md` + `governance.py`:
  provenance/lineage/confidence/evidence), **Artifacts** (`artifact-framework.md` + `artifact.py`),
  **Validation** (`validation-framework.md` + `validation.py`: A/G/R metrics), and **Change Control**
  (`change.py`, from V03_S07: classify → evaluate impact → approve-with-evidence → trace; constraints
  enforced by `validate_change`). CLI:
  `tools/docintel_run.py` (`--check`, `<file> --out art.json --udom udom.json`). Stdlib-only by
  default (.txt/.md/.html/.docx); PDF activates when PyMuPDF is installed. Ties to
  `protocols/metadata-schema.md` + `quality-gates.md` (every artifact `human_review_required: true`,
  not certified until `quality-review`); registered in `shared/ontology/artifact-types.json` (7 new
  artifact types). Never fabricates — unrecovered regions are reported with low confidence and a
  capability-gap note. Experimental stages are feature-flagged OFF by default. Staged next: OCR,
  deep table/layout intelligence, parallel recovery, reference-set accuracy metrics, and re-basing
  `parse_fl_standards.py` on docintel.
- **`standards-updater` skill + upgraded crawler** — `tools/standards_refresh.py` now respects
  robots.txt, crawls politely (randomized delays, one honest User-Agent), detects JS-required pages
  (e.g., the CPALMS search SPA) and **backs off rather than bypassing**, and writes a timestamped JSON
  report. `skills/standards-updater/` orchestrates detect → crawl → verify-on-CPALMS → apply
  (human-in-the-loop, no auto-apply); `tools/requirements-scraper.txt` lists optional deps. Adapted
  compliantly (no evasion) from a robots-respecting scraper design. **Watches all Florida change
  vectors** (standards, courses/curriculum incl. CTE, pacing/guidance/TAPs, instructional materials,
  assessment, graduation, legislation Title XLVIII, State Board rules FAC 6A) via `coverage` +
  `crawl_seeds` + `watch_pages` in `sources.json`, with content-change detection on watched pages.
- **Florida B.E.S.T. + NGSSS standards** wired into the engine: `shared/standards/florida-best.md`
  (coding schemes verified against the official docs — Math `MA.*`, ELA `ELA.*`, Science `SC.*`,
  CS `SC.K12.CTR.*`, ELD `ELD.K12.ELL.*` — plus Access Points for SpEd) and a resource catalog
  `shared/standards/resources/florida-2025-26.md` (FAST/B.E.S.T./EOC/FCLE specs, ALDs, writing
  rubrics, accommodations, WIDA) that points to **CPALMS/FLDOE/WIDA as the live, current sources**.
- **National standards overlay** (`shared/standards/state-standards-map.md` + `states.json`): an
  approximate 50-state + DC map of CCSS (Math/ELA) vs. NGSS/NGSS-based vs. independent science, with
  named state sets and each state's DOE as the live authority. Florida stays the deep, fully-supported
  state; **every other state is an explicit `stub`** with fillable per-subject slots
  (`status`, `subjects[*]`, `adapter`, `resources_dir`) + a populate checklist — room to add states
  later without redesign.
- **Florida standards fully enumerated** — `tools/parse_fl_standards.py` extracts all **6,583** FL
  standards + access points (Math 1,127 · ELA 719 · Science 1,450 · CS 569 · Social Studies 2,713 ·
  ELD 5) from the stored documents into queryable JSON (`resources/florida/data/`), with
  `tools/fl_lookup.py` to query by subject/grade/keyword.
- **Florida verified current for 2026–2027** (June 2026): B.E.S.T. (Math/ELA) + NGSSS (Science/SS)
  confirmed as the adopted standards; `florida-best.md` adds the FAST/B.E.S.T./EOC assessment program
  and a CS-standards-update note; `sources.json` authorities/seeds refreshed to the verified
  CPALMS/FLDOE 2026–27 pages (incl. the 2026–27 assessment schedule).
- **Florida resource corpus stored** (`shared/standards/resources/florida/`, 104 files ~108 MB) with a
  `sources.json` manifest (per-file sha256 + official CPALMS/FLDOE/WIDA source), and
  `tools/standards_refresh.py` — a recursive crawler that checks the canonical sources for newer
  documents and reports/downloads updates.
- Worked examples for `curriculum-mapping`, `family-communication`, and `professional-learning`.

## [1.0.0] — 2026-06-20
First complete release of the TOS SKILL.md ecosystem.

### Added — Foundations (Phase 0)
- Repository scaffolding; `CLAUDE.md`, `README.md`, `STATE.md`.
- Governance docs: `ARCHITECTURE.md`, `QUALITY_MODEL.md`, `SECURITY_AND_SAFETY.md`,
  `ROUTING_MODEL.md`, `CHANGE_MANAGEMENT.md`.
- Shared governed core (`shared/`): unified pipeline, personas, ontology, the standards engine
  (state-agnostic K-12 adapter + CCSS/NGSS/state model), the differentiation engine
  (UDL/tiering/EL/accommodations), and the quality engine.
- `tools/`: `sync_check.py` drift guard (enforces the 8 Quality Gates repository invariants +
  per-skill reference sync), `new_skill.py` scaffolder, skill template.
- `skills/teacher-core` — the hub/orchestrator.

### Added — Governance (Phase B)
- Protocol layer (`protocols/`): `quality-gates.md` canonicalized from sections 001–100, plus
  `metadata-schema`, `assumptions-protocol`, `standards-verification`, `conflict-protocol`,
  `failure-recovery` (all v1.0).
- Quality Ledger (`ledger/`) — append-only decision log.

### Added — Skills (Phases A & C)
- `quality-review` (Quality-Gates executor + `scripts/score.py`), `lesson-planner` (reference),
  `assessment-designer`, `presentation-builder`, `curriculum-mapping`, `special-education-support`,
  `intervention-mtss`, `family-communication`, `professional-learning`, `school-administration`.
- Cross-skill orchestration (`teacher-core/references/workflows.md`) + the Example Library.

### Added — Hardening (Phase D)
- `tools/package_skill.py` (installable `.skill` bundles); hardened CI; `skills/README.md` catalog;
  `SECURITY_REVIEW.md`; `BENCHMARK.md` (with-skill vs. baseline).

### Added — Advanced (Phase E)
- `tools/metrics.py` + `METRICS.md` (success-metric dashboard over the ledger + registry);
  `shared/ontology/artifact-types.json` registry; `DEPLOYMENT.md`; AI-systems documentation.

### Notes
- No real student data anywhere — placeholders only. Every artifact is decision support
  (`human_review_required: true`), not a final professional/legal determination.
