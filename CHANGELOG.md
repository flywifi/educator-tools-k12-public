# Changelog
All notable changes to the Teacher Operating System (TOS) ecosystem. Format follows
[Keep a Changelog]; this project uses [Semantic Versioning](https://semver.org/) — see
`CHANGE_MANAGEMENT.md` for the versioning policy.

## [Unreleased]
### Added
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
