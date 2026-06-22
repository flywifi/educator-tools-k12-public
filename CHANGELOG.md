# Changelog
All notable changes to the Teacher Operating System (TOS) ecosystem. Format follows
[Keep a Changelog]; this project uses [Semantic Versioning](https://semver.org/) — see
`CHANGE_MANAGEMENT.md` for the versioning policy.

## [Unreleased]
### Added
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
