# STATE.md
## Teacher Operating System — Live Status & Recovery
Update at every phase boundary and after each skill ships. Recovery package = the charters + Quality
Gates 001–100 + `TOS_ECOSYSTEM_BUILD_OUTLINE.md` + this file.

## Context-First expansion (RFC-F001 V2) — F1–F6 shipped
A six-phase build (plan: approved RFC-F001 V2) adding currency, a school/program index, a per-teacher SOP
skill, a gated staff directory, always-on web crawl, and a light context spine — stdlib-first, gated,
governed. **18 skills · 14 engines.** All phases verified (drift guard + `version --check` +
`registry_currency` clean) and committed on `claude/fervent-hawking-nyrzy5`; each is a durable
commit-anchored snapshot in `ledger/snapshots.json` (`tools/rollback.py --list`).
- **F1 — Firecrawl always-on + RSS + whole-ecosystem rollback.** `shared/traversal/parallel_search.py`
  auto-detects `FIRECRAWL_API_KEY`/`FIRECRAWL_BASE_URL` and prefers Firecrawl (else polite `requests`);
  `rss_fetcher` (`feed` seeds, `feedparser`/stdlib). Rollback is whole-tree to a known-good **commit**
  (tags can't be pushed here — egress policy 403), recorded in `ledger/snapshots.json`.
- **F2 — Source-currency + staleness engine.** `tools/source_currency.py` + `shared/sources/<domain>.json`:
  states `current/changed/superseded/removed_404/stale_age/unreachable/uncertain` via conditional GET +
  content sha256 + supersession keywords + recency + 404 sweep; offline-graceful, advisory + human-verified.
- **F3 — OCPS schools + programs index.** `shared/schools/` (+ `ocps/` seed) keyed on FLDOE MSID;
  open/close + program changes watched by F2 (`shared/sources/ocps-schools.json`). Public, non-PII only.
- **F4 — `teacher-profile` skill (18th) + setup wizard.** Roles, duties, role-based handoff map, prefs →
  gitignored `teacher.local.json` + context `sop_refs`/`overrides`; teacher-stated outranks crawled.
- **F5 — Staff/role directory (gated).** `shared/staff/` OFF by default (`STAFF_INGEST_AUTHORIZED`),
  authorized-first, gitignored, `staff-data-policy.md`; resolves handoff roles → people with honest gaps.
- **F6 — Context-confirmation spine (light).** `shared/graph/spine.py` composes profile+schools+staff into
  a snapshot + relationship graph + a confirm-what's-inferred checklist. Full knowledge-graph deferred.

**Last updated:** Phases 0–E delivered + Florida complete; **`document-intelligence` skill +
`shared/docintel/` engine added** (full-framework skeleton: UDOM, parser-orchestration, governance,
artifact, validation — runs end to end). 17 skills, 6 protocols, ledger, benchmark, packaging,
versioning, and the metrics dashboard. **Multi-constituency support added** (public/charter/private/
home-ed): composable context **overlays** (`shared/context/overlays/`, `overlay.schema.json`),
independent **framework registries + crosswalks** (`shared/standards/frameworks/`, `crosswalks/`,
`tools/crosswalk.py`), ordered authority precedence with individual **grade/course/course_level**, and
context-conditional Quality Gates. **Canonical source-of-truth resolver + minority report added**
(`shared/context/sot_resolver.py`, `source-roles.json`, `decision.schema.json`, `minority-report.md`,
`source-of-truth.md`; wired into `conflict-protocol.md` §4a + `metadata-schema.md` + `method.md`). Every
skill now ships **`MAINTAINER.md` update instructions** (template + `tools/skill-maintenance.md`;
enforced by the drift guard). **Latest:** grade/assessment **translation** + crosswalk `coverage` +
`department` scope (`shared/standards/grade-scales/`, `tools/crosswalk.py`); **connector** feature-flag
engine + **student** PII/ePHI engine (`shared/connectors/`, `shared/students/`); and the
**`meeting-classifier`** skill (14th) that classifies a teacher meeting from context clues and routes it
(`DEPLOYMENT_SURFACES.md` covers Claude Code / web / other-model use). **Latest update:** docintel gains
lightweight workplace-evidence parsers — `.ics` calendar invites + `.eml` email
(`shared/docintel/parsers/calendar_parser.py`, `email_parser.py`), folded into `meeting-classifier` via
`--file`; and the connector model is reframed so live connectivity is the **host AI's native
integration** (Claude/OpenAI/Gemini/…) — no provider client is built — with first-class
**district-restricted-but-active** evidence (`restricted_evidence` + reason; the resolver drops it to the
next available source and lowers confidence). **Student records:** new `shared/records/` engine — a core
baseline (incl. assessment results + curriculum) + **11 independent feature-flagged modules**
(`records_modules`) and **three interconnected
handoff packages** (skill→skill, teacher→teacher, school-transfer) so student info travels consistently
across handoffs; reuses students/context/standards/connectors + the metadata block. ePHI revised to a
**multi-source, attributed** model (district/school forms, nurse/guardian notes, sick notes; signature
optional; never fabricated). **Shared router:** new `shared/routing/` engine (`routing.json` + `router.py`)
— data-driven request→skill routing with confidence + alternates + a minority report on ties, consumed by
both `teacher-core` and `meeting-classifier` (one source instead of duplicate tables); drift guard now
verifies every route target is a real skill. **Connections:** docintel gains caption/transcript parsers
(`.vtt`/`.srt`) + a `Transcriber` engine contract (`transcribe.py`, `media_parser.py`) so audio/video are
transcribed when a host-AI/ASR engine is present and **honestly gap-reported (never faked)** when not.
**Traversal/accumulation:** new `shared/traversal/` engine — takes multiple inputs and **recursively
expands** them into an append-only, provenance-tagged evidence envelope (graph + gaps + checkpoint;
sequential, ~4-layer, saturation/depth/size stops; companion-mode, never overwrites upstream), routing
the handoff via the shared router. Adapted from the user's mature traversal-companion design; reuses the
docintel retrieval-state ladder.
**Skill-health & repair:** new `shared/health/` engine + **`skill-health` skill (15th)** — a doctor-style
readiness scan of every skill + engine, audit-trail diagnosis (Quality Ledger + saved execution traces /
minority reports), ecosystem-impact analysis for new/renamed skills, and a human-edited/approved repair
plan (nothing high-stakes auto-applies). Adapted from the prior system's doctor + observability +
regression skills. Now also `tools/skill_repair.py` (guided apply of an approved plan — safe mechanical
fixes only, dry-run by default) and `tools/validate_outputs.py` (validate a governed artifact vs its
schema + a no-fabrication / no-real-PII rule catalog before it ships; promotes failures to regressions).
**Split into small, robust skills (17th/18th — `output-validator`, `skill-repair`)** with thorough,
spec-grounded references (a stdlib `tools/validate_document.py` catches OOXML/PDF/ODF corruption classes
documented by the Open XML SDK + veraPDF; font coverage per Noto; reader booster microsoft/markitdown).
Stdlib-first so they always run regardless of what the teacher has installed.
**Versioning & rollback:** `versions.json` gives every skill + engine a semver aligned to the ecosystem
`VERSION`/plugin (`tools/version.py --check`, a CI gate); on a major failure `tools/rollback.py` restores
one component to a known-good git ref — **dry-run by default, human approval to `--apply`** (automated
`--auto` only if a deployment grants `auto_rollback`), logging the failure to `ledger/rollback-log.json`.
Policy: `CHANGE_MANAGEMENT.md` §7; each `MAINTAINER.md`/`tools/skill-maintenance.md` points to it.
**Parallelism (started):** the traversal engine gains an opt-in **parallel scheduler** (`scheduler=
"parallel"`, stdlib `ThreadPoolExecutor`) — each layer's independent fetches (file/connector/external
search) run concurrently, bounded, with a **single-threaded race-free merge**; sequential stays the
default. Each fetcher owns backoff/jitter + honors `Retry-After`; a failed fetch degrades to a gap.
Verified parallel == sequential output. Research-grounded (concurrent.futures fan-out, rate-limit
backoff, map-reduce reducers). **External parallel search:** `shared/traversal/parallel_search.py` adds a
token-bucket `RateLimiter`, a graceful `parallel_map`, a `web_fetch_fetcher` (url seeds; requests +
Retry-After/backoff, gap otherwise), and a `search_fetcher(search_fn)` that wraps an injected
host/native search into a query→results→pages fan-out — same provenance/dedup/gaps/stops. Verified
offline (rate limiting, graceful failure, query→url recursion under the parallel scheduler).
**Provisioning & currency:** the suite now ships as a **Cowork plugin** (`.claude-plugin/plugin.json` +
`marketplace.json` — install all skills in one step) and a generalized **registry-currency watcher**
(`tools/registry_currency.py` + `registry-sources.json`/`registry-baselines.json`) flags drift in every
stored registry (connectors, grade-scales, frameworks, ontology, routing, records catalogs, the plugin
manifest) and names the authority to re-verify on; standards crawling stays with `standards-updater`.
*(5-area capability roadmap — COMPLETE: shared router ✓ · anticipated connections (audio/video
transcripts) ✓ · accumulating/recursive handoff ✓ · skill-health & repair ✓ · currency watcher +
Cowork/plugin provisioning ✓.)*
**Capability/dependency layer (post-roadmap):** optional deps are now **capability-gated** via
`tools/dependencies.json` + a credentials-aware preflight (`shared/health/capabilities.py`,
`health.py --capabilities`): **local_optional** (PDF/OCR/Office-authoring/render/transcription/fonts —
on when installed, honest gap when not) and **cloud_optional** (Azure/fal/Nutrient/Firecrawl — OFF by
default, district opt-in, API keys from env only, bound by student-data-policy + connector restrictions).
A real gated `WhisperTranscriber` fills the audio/video contract. Supply chain: pinned
`requirements-*.txt` + `.github/dependabot.yml` (auto-update) + `tools/security_scan.py` (pip-audit +
bandit) as a CI gate; fonts = Noto + Liberation/Carlito/Caladea with a coverage check. Policy:
`shared/health/dependency-policy.md`.
**Authoring + universal read:** `shared/office/` produces real **.pptx/.docx/.xlsx** (python-pptx/docx/
openpyxl + LibreOffice render) — wired into `presentation-builder` — and **Google Docs/Sheets/Slides**
via `google_bridge.py` (lossless Office import + generated Apps Script; live calls go through the host's
native Google integration or a deployment Node/clasp runner, no OAuth client built). docintel now reads
**any file type**: typed parsers for known formats, legacy/ODF office via LibreOffice, and a never-fail
universal fallback (text decode, else binary metadata/strings) so every input yields at least metadata.
**Active branch:** `claude/fervent-hawking-nyrzy5`
**Resume here:** maintenance mode. **Florida is complete & current for 2026–27** — adapter
(`florida-best.md`), stored corpus + refresher, and **all 6,583 standards enumerated to queryable
JSON** (`resources/florida/data/` via `tools/parse_fl_standards.py` + `tools/fl_lookup.py`). A
**national overlay** (`state-standards-map.md` / `states.json`) stubs the other states. Optional
follow-ups: widen the eval benchmark; populate a 2nd state via the Florida template; tag `v1.0.0`.

---

## Phase status
| Phase | Scope | Status |
|---|---|---|
| 0 — Skill Architecture & Foundations | scaffold, shared core, protocols, governance docs, teacher-core, tooling | ✅ Complete |
| A — Educational Foundations | quality-review + lesson/assessment/presentation | ✅ Complete |
| B — Governance Infrastructure | 6 protocols approved; decision records emitted by every skill; Quality Ledger created | ✅ Largely complete (runtime automation later) |
| C — Operational Integration | expansion skills + teacher-core orchestration (`workflows.md`) + Example Library | ✅ Complete |
| D — Repository Hardening | packaging, CI, catalog, security review, **versioning** (`VERSION`/`CHANGELOG`) | ✅ Complete (per-skill READMEs omitted — redundant with each `SKILL.md`) |
| E — Advanced Architecture | analytics (`metrics.py`/`METRICS.md`), artifact registry, `DEPLOYMENT.md`, AI-systems doc | ✅ Largely complete (ontology can deepen later) |

## Skill status (17 built)
| Skill | Role | Status |
|---|---|---|
| `teacher-core` | hub / router | ✅ built |
| `quality-review` | Quality Gates executor (+ `scripts/score.py`) | ✅ built |
| `lesson-planner` | capability (reference skill) | ✅ built (gold example) |
| `assessment-designer` | capability | ✅ built |
| `presentation-builder` | capability (renders via `pptx`) | ✅ built |
| `curriculum-mapping` | capability | ✅ built |
| `special-education-support` | capability (high-stakes; safety-emphasized) | ✅ built (example) |
| `intervention-mtss` | capability (high-stakes) | ✅ built (example) |
| `family-communication` | capability (privacy-emphasized) | ✅ built |
| `professional-learning` | capability (non-evaluative coaching) | ✅ built |
| `school-administration` | capability (school/system level) | ✅ built |
| `standards-updater` | governance / maintenance (polite crawler; watches all FL change vectors) | ✅ built |
| `document-intelligence` | capability (document understanding; parser-independent, artifact-centric, governed) | ✅ built (skeleton) |
| `meeting-classifier` | triage/router (classifies a teacher meeting + intent from context clues; connector-aware, PII/ePHI-aware; routes) | ✅ built |
| `skill-health` | governance / maintenance (ecosystem readiness scan, audit-trail diagnosis, impact analysis, human-approved repair plan; engine `shared/health/`) | ✅ built |
| `output-validator` | governance (validate one output before it ships: artifact schema/rules + document structure; engines `tools/validate_outputs.py` + `tools/validate_document.py`) | ✅ built |
| `skill-repair` | governance (apply an approved repair plan minimally — mechanical only, judgment stays human; engine `tools/skill_repair.py`) | ✅ built |

## Document Intelligence engine (`shared/docintel/`)
TOS-native platform: documents → governed knowledge assets (provenance/lineage/confidence/evidence).
Parser-independent (swappable plugins behind one `Parser` contract), artifact-centric. Frameworks:
**UDOM** (`udom.md` + `udom.schema.json`), **Parser Orchestration** (`parser-orchestration.md`),
**Table Intelligence** (`table-intelligence.md`), **OCR & Images** (`ocr-architecture.md`), **Google
Workspace** (`google-workspace.md`), **Governance** (`governance-contract.md`), **Artifacts**
(`artifact-framework.md`), **Validation** (`validation-framework.md`), **Change Control** (`change.py`,
from V03_S07). Runnable skeleton: `python3 tools/docintel_run.py --check` / `<file> --out art.json`.
Stdlib-only by default: **table intelligence** (docx/html/md), **image analysis** (format/dimensions),
a **targeted OCR** stage (honest `ocr` capability-gap when no engine), and **Google Workspace** inputs
(Google Docs API JSON + Docs/Sheets/Slides exports .odt/.csv/.xlsx/.pptx). Every doc carries a
**retrieval-state** (`referenced/metadata_only/content_ingested/local_artifact_saved`) so visibility
≠ extraction. **Fully offline** — optional local engines (PyMuPDF, pdfplumber, Tesseract) via
`tools/requirements-docintel.txt`, **no network at run time**: PDF native text + **scanned-PDF OCR**
(PyMuPDF rasterize → Tesseract), PDF tables (pdfplumber), image OCR (pytesseract). **The Florida
standards pipeline now reads via docintel** (`tools/parse_fl_standards.py`; 6,583 codes, identical to
the prior reader). Built from the uploaded V01–V09 architecture. Staged next: more OCR engines
(Surya/OCRmyPDF), DL layout, parallel recovery, reference-set accuracy metrics, `.ods`/`.odp` +
Sheets/Slides API JSON.

## Context & SOP layer (`shared/context/`)
Adapts the ecosystem to *where/how* a teacher works (operating-reference pattern). **All 67 FL county
districts logged** (`florida-districts.json`, fillable stubs; Orange/OCPS populated incl. OCVS).
School-type **exception rule-sets** (`school-types.json`):
traditional/magnet/charter/district-virtual/FLVS/home-ed/private-scholarship. **Context contract**
(`context.schema.json` + `context.py`) — state/district/school_type/program/instructional_model/
mandates/SOPs/authority_precedence/overrides — resolved first by teacher-core and carried into the
metadata block + handoffs (`protocols/metadata-schema.md` gains a `context` envelope). Teachers upload
SOPs (`sop-model.md`), read offline via docintel; school type governs standards applicability.
**Architecture in place; district rules/norms + school-type specifics are fillable stubs.**

## Connector + Student layers (`shared/connectors/`, `shared/students/`)
**Connectors** (`connectors.json`/`.md`/`connector.schema.json`/`connectors.py`) — feature-flag
contract for workplace tools (Google Workspace/Classroom, Microsoft 365/Teams, Zoom, Canvas,
Blackboard, Salesforce, SIS; `manual_paste`+`uploaded_file` always-on). Use whatever's connected,
**degrade + converge** via alternates, flag unused off; states + resilience/override policy mirror the
source-availability contract. **Students** (`student-profile.schema.json`, `students.example.json`
placeholders, `student-data-policy.md`, `students.py`) — PII/ePHI profiles keyed by `student_id`
(guardians + signed **medical action plans**). **Repo=placeholders; runtime=real data in a
pluggable storage adapter** (`local_gitignored` | `session_ephemeral` | `uploaded_file` |
`connector_sis`), **never committed**. **SIS-first** precedence; SIS↔local conflicts escalate
(new `student_record` claim in `source-roles.json`); `identify_students_by` name|id (default name).
Surfaces (`DEPLOYMENT_SURFACES.md`): Claude Code / claude.ai web / other models — core is stdlib +
Markdown, portable. First consumer: `meeting-classifier`.

## Protocol layer (all v1.0)
| Protocol | Status |
|---|---|
| `quality-gates.md` | ✅ canonical (consolidated from provided 001–100) |
| `metadata-schema.md` | ✅ approved (reconstructed from QG) |
| `assumptions-protocol.md` | ✅ approved |
| `standards-verification.md` | ✅ approved |
| `conflict-protocol.md` | ✅ approved |
| `failure-recovery.md` | ✅ approved |

## Governance
- **Quality Ledger:** `ledger/quality-ledger.md` — append-only decision log, seeded with 5 entries
  (the worked examples; all Approved). Format/rules: `ledger/README.md`.
- Every `SKILL.md` references the pipeline + metadata schema and emits `human_review_required`
  (enforced by the drift guard).

## Last drift-guard result
`python3 tools/sync_check.py` → **PASS — 18 skills, 8 invariants, 2 synced refs; frontmatter +
resource integrity validated; `MAINTAINER.md` present in all skills.**
`quality-review/scripts/score.py` verified (normal / critical-override / threshold cases).

## Validation note
Every skill ships `evals/evals.json` (prompts + assertions) and worked examples. The eval
**benchmark ran** on a representative 3-case subset (with-skill vs. no-skill baseline): **with-skill
12/12 vs. baseline 8/12** — biggest uplift in governance/auditability and standards rigor; no
regressions. Details in **`BENCHMARK.md`**. Widening to the full eval set is a follow-up.

## Confirmed decisions
Full-K-12 breadth-first standards; FULL §33.1 9-dimension weighting authoritative; QG canonical
names; build on `pptx/docx/pdf` for rendered outputs; the 5 reconstructed protocols are approved.

## Open items (optional follow-ups — core build complete)
1. Widen the eval benchmark to the full 27-case set (subset done — `BENCHMARK.md`).
2. Florida wired + **corpus stored** (`resources/florida/` + `sources.json`, 104 files) with
   `tools/standards_refresh.py` to crawl CPALMS/FLDOE/WIDA for updates; add other states via the same template.
3. Deepen the ontology; optional LLM-as-judge automation; tag a `v1.0.0` git release.

## Success metrics (Phase E)
Live dashboard: **`METRICS.md`** (regenerate with `python3 tools/metrics.py`). Current: 18 skills ·
65 artifact types · 65 eval cases · 10 standards frameworks (incl. Florida B.E.S.T./NGSSS) · 4 differentiation engines · 6/6
protocols · 100% ledger approval (seed) · 18/18 skills emit `human_review_required`.
