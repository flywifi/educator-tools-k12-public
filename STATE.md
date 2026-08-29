<!-- last_reviewed: 2026-08-16 | owner: repo-maintainer -->
# STATE.md
## Teacher Operating System — Live Status & Recovery
Update at every phase boundary and after each skill ships. Recovery package = the charters + Quality
Gates 001–100 + `TOS_ECOSYSTEM_BUILD_OUTLINE.md` + this file.

## Context-First expansion (RFC-F001 V2) — F1–F6 shipped
A six-phase build (plan: approved RFC-F001 V2) adding currency, a school/program index, a per-teacher SOP
skill, a gated staff directory, always-on web crawl, and a light context spine — stdlib-first, gated,
governed. (Skill/engine counts are GENERATED — see `docs/METRICS.md` and `versions.json`; the counts current when this phase shipped are in the changelog.) All phases verified (drift guard + `version --check` +
`registry_currency` clean) and committed on `claude/fervent-hawking-nyrzy5`; each is a durable
commit-anchored snapshot in `ledger/snapshots.json` (`tools/rollback.py --list`).
- **F1 — Firecrawl always-on + RSS + whole-ecosystem rollback.** `shared/traversal/parallel_search.py`
  auto-detects `FIRECRAWL_API_KEY`/`FIRECRAWL_BASE_URL` and prefers Firecrawl (else polite `requests`);
  `rss_fetcher` (`feed` seeds, `feedparser`/stdlib). Rollback is whole-tree to a known-good **commit**
  (tags can't be pushed here — egress policy 403), recorded in `ledger/snapshots.json`.
- **F2 — Source-currency + staleness engine.** `tools/source_currency.py` + `canonical-sources/registries/<domain>.json`:
  states `current/changed/superseded/removed_404/stale_age/unreachable/uncertain` via conditional GET +
  content sha256 + supersession keywords + recency + 404 sweep; offline-graceful, advisory + human-verified.
- **F3 — OCPS schools + programs index.** `canonical-sources/schools/` (+ `ocps/` seed) keyed on FLDOE MSID;
  open/close + program changes watched by F2 (`canonical-sources/registries/ocps-schools.json`). Public, non-PII only.
- **F4 — `teacher-profile` skill (18th) + setup wizard.** Roles, duties, role-based handoff map, prefs →
  gitignored `teacher.local.json` + context `sop_refs`/`overrides`; teacher-stated outranks crawled.
- **F5 — Staff/role directory (gated).** `shared/staff/` OFF by default (`STAFF_INGEST_AUTHORIZED`),
  authorized-first, gitignored, `staff-data-policy.md`; resolves handoff roles → people with honest gaps.
- **F6 — Context-confirmation spine (light).** `shared/graph/spine.py` composes profile+schools+staff into
  a snapshot + relationship graph + a confirm-what's-inferred checklist. Full knowledge-graph deferred.

**Last updated:** Phases 0–E delivered + Florida complete; **`document-intelligence` skill +
`shared/docintel/` engine added** (full-framework skeleton: UDOM, parser-orchestration, governance,
artifact, validation — runs end to end). Then 17 skills; 6 protocols, ledger, benchmark, packaging,
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
**Active branch:** `claude/educator-tools-k12-plan-f49yju`
**Resume here:** maintenance mode. **Florida is complete & current for 2026–27** — adapter
(`florida-best.md`), stored corpus + refresher, and **all standards enumerated to queryable (6,583 at the time; 6,574 today after 9 CS retirements)
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

## Skill status (historical table — 17 skills at the time of writing)
*Live counts live in `docs/METRICS.md` (generated, gated by check 16). Counts are deliberately
not restated in this file.*
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
standards pipeline now reads via docintel** (`tools/parse_fl_standards.py`; 6,583 codes at the time — 6,574 today, identical to
the prior reader). Built from the uploaded V01–V09 architecture. Staged next: more OCR engines
(Surya/OCRmyPDF), DL layout, parallel recovery, reference-set accuracy metrics, `.ods`/`.odp` +
Sheets/Slides API JSON.

## Context & SOP layer (`shared/context/`)
Adapts the ecosystem to *where/how* a teacher works (operating-reference pattern). **All 67 FL county
districts logged** (`florida-districts.json`, fillable stubs; Orange/OCPS populated incl. OCVS).
School-type **exception rule-sets** (`school-types.json`):
traditional/magnet/charter/district-virtual/FLVS/home-ed/private-scholarship/private-independent. **Context contract**
(`context.schema.json` + `context.py`) — state/district/school_type/program/instructional_model/
mandates/SOPs/authority_precedence/overrides — resolved first by teacher-core and carried into the
metadata block + handoffs (`protocol-layer/metadata-schema.md` gains a `context` envelope). Teachers upload
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
`python3 tools/sync_check.py` → **PASS — 62 skills, 8 invariants, 2 synced refs; frontmatter +
resource integrity validated; `MAINTAINER.md` present in all skills; all 25 numbered checks (0–24)
enforced, and since 2026-08-16 a guard that CRASHES is a failure rather than a `[note]`.**
(2026-08-16)
`quality-review/scripts/score.py` verified (normal / critical-override / threshold cases).

## 2026-08-17 — the guard that could not see, and the evals that had never run (round 4)

Two things Round 3 named and did not fix.

**`protocols/`.** The directory was renamed to `protocol-layer/` on 2026-06-28 (a git R100 rename)
and 877 references went stale that day, invisible to check 15 because an anchor list is a whitelist
and an unknown prefix reads as "not a path". 90% of it was 13 lines in two canonical files
replicated into 62 skills. Swept in three commits; the dead prefix now stays in both anchor tuples
as a tripwire, with a twin proving that removing it reopens the hole.

**The evals.** They had never been executed — not once, by any machine. The proof was a committed
assertion that was false: `skill-health` expected `readiness_band: "strong"` while its own recorded
command returned `"not_ready"`. The CI step named "Validate eval files" ran `json.load()`. Six case
shapes existed across the repo. Now: one schema, a runner, and **0 → 133 executed cases, all
passing**, with skips and unrunnable cases counted rather than hidden.

Running things found more than reading them did. `health.py` was flagging all 43 atoms as
"not referenced in routing.json" while all 43 were registered — a 43-instance false negative that
also floored the readiness score. `validate_outputs` let an artifact omitting `human_review_required`
pass. Three atoms declared `confidence` as a float against a string enum. All 43 cited a
`references/metadata-schema.md` no atom has. And check 24 — which I shipped last round — was wrong
under a shallow clone, producing six false CI failures the first time the calendar moved past the
day the manifests were stamped.

Three mistakes of mine are in the commits: the atom-contract checker's first version read the wrong
schema key and silently skipped a rule (its twins caught it, and fixing it surfaced two more real
violations); a blanket sweep corrupted `sync_check.py`'s own anchor tuple; and I recorded the
readiness score here as "saturated by design" when it was reporting a real bug.

**What is NOT closed.** The 133 are CONTRACT cases — routing, output shapes, schema conformance.
**65 model-facing cases remain unexecuted**, including every refusal case for the nine skills that
received boundary language in v1.5.0. And quality-review's trigger evals fail their own bar (1 of 10
positives route to it, against ≥0.8): the keyword router scores the artifact noun above the review
verb. Measured and recorded, deliberately not fixed — that is a product behaviour change.

## 2026-08-16 — false claims corrected, and the guards that could not see them (round 3)

A verification-and-correction round. It makes the repo look **worse before it looks better**:
a downgraded security table, a newly-failing date check, feeds confirmed dead. That is the intended
direction — an honest red beats a decorative green — but the next reader will see more open items
than last week, and that is stated here rather than discovered.

What was corrected:
- **42 of 43 atom MAINTAINERs** claimed a `match_method` mechanism only `standards-match` has; 33 of
  them also documented a superseded minority-report mechanism. Both had survived a 2026-07-15 doc
  audit that edited all 43 files.
- **`security/SECURITY_REVIEW.md`** was written 2026-06-20 for 11 skills and had described an
  ecosystem of 62 since 2026-06-29. Rebuilt from executed commands with per-row scope and class.
  Three claims were false at real scope and carry dated corrections.
- **Nine sensitive skills** had no boundary language; they now do, including the disciplinary-output
  requirement policy mandates and no skill carried.
- **The feed catalog's stated reason** for being unverified (an egress-restricted environment) had
  expired; all 14 were fetched and 2 verified with proof items.
- **Seven "GUESSED" OCPS URLs** became dated observations. 2 verified, 5 held back because the host
  answers unknown paths with a generic landing page.

What was gated for the first time:
- **check 24** — a hand-typed `updated` older than its own file's last commit. 5 of 7 manifests were
  stale; one generator wrote a hardcoded date on every run.
- **`shared/health/binaries.py`** — one resolver replacing four PATH-only probes and one inlined
  duplicate. `health` and `office` had **contradicted each other about `soffice` on any Mac**.
  macOS **E2: OPEN → UNTESTED**.
- **`never_checked`** in `source_currency` — 69 of 124 registry sources could never age out and were
  invisible inside `uncertain`.

Two mistakes of mine, recorded because the commits are the record: the binary-resolver self-test
asserted that LibreOffice was installed, so CI failed twice on an environment fact rather than a
code property; the URL promotion table would have upgraded a URL its own note calls FABRICATED,
because it read a blanket 403 as proof of existence. Both fixed with twins in both directions.

Still open, named not implied: **44 of 62 skills have zero eval cases**, including every high-risk
atom, so the boundary language is unverified rather than verified-and-minor; the health readiness
score read 0/100 for a reason that was NOT saturation (see below); and **877 dead `protocols/` doc references** were
structurally invisible to check 15, because a renamed directory falls out of its anchor list.

## 2026-07-16 — adversarial audit of the 24h window (34 probes) + full remediation
Audit-only pass over everything landed in the prior 24h (doc guards 15–18, supply-chain fix, macOS
fixes + mac-lint/check 19, deps_preflight Option 1, macos-sources + check 20): 34 probes across 6
surfaces, findings logged without action, then all 10 approved items remediated in 4 commits:
- **Office honesty (Major):** soffice exits 0 on failed headless conversion (upstream tdf#148275) —
  `convert()` now verifies the output file exists (the old fake-"ok" had even fooled the audit's own
  E2E probe: this container has no Impress/Writer, so no conversion ever succeeded here); the legacy
  parser returns `convert_failed` diagnostics instead of an empty "native" result.
- **check 20 (Major):** exact-page URL matching per RFC 3986 (three proven prefix-match bypasses
  killed) + IGNORECASE + a [note] naming an unreadable registry.
- **deps_preflight:** failed installs exit 1; `scrape_feed` repointed off a never-existed
  requirements file; `--install-all` dedupes shared requirements (14→9 pip batches).
- **mac-lint + source_currency:** variable-held argv + `io.open` detected; ignore-pragma spans
  multi-line calls; unparseable files noted; naive dates parse as UTC midnight (one bad date no
  longer crashes the whole freshness engine). Sources registered: tdf#148275, ask.libreoffice 49388,
  RFC 3986 (macos-sources.json, 41 entries). Findings log delivered + annotated.

## 2026-07-15 — maintainer/README audit (fix drift + fill doc gaps + 4 durable doc-drift guards)
Systematic audit of every component (skills/atoms/shared engines/canonical buckets) against its
maintainer/README files. Fixed the proven discrepancies, filled the doc-coverage gaps, and installed
four hard-gate guards so this drift class becomes a red build, not a silent default.
- **Fixed:** regenerated `docs/METRICS.md` (was stale at 29 skills → 62); repointed **8** dead
  un-grouped `skills/<name>/…` paths to their grouped homes (7 found by audit + 1 the new guard
  caught); corrected the live "Current" success-metrics block (62 skills, 62/62 human_review);
  fixed a broken overlays model/schema cross-reference.
- **Filled:** added docs for the zero-doc components — `shared/office/`, `shared/routing/`,
  `shared/atoms/`, `canonical-sources/references/`, `canonical-sources/overlays/`, plus
  `tools/README.md` and a top-level `canonical-sources/README.md` (root FL district + school-type
  JSON). Folded the session's cross-platform gotchas (soffice PATH fallback, etc.) into the office doc.
- **Guarded (`tools/sync_check.py` checks 15-18, `DOC_GUARDS_ENFORCE=True`):** (15) dead repo-relative
  doc-path detector; (16) `METRICS.md` regenerate-and-compare freshness (via a new pure
  `metrics.render()`); (17) component-doc coverage (every `shared/`/`canonical-sources/` dir carries a
  doc); (18) `last_reviewed` freshness stamps on every README/MAINTAINER (missing/ >365d hard-fail; a
  sibling changed after the stamp is an advisory re-review reminder). Grounded in SWE-at-Google Ch.10,
  Diátaxis, and the repo's own committed-fingerprint pattern (offline-index manifest). Each guard was
  proven to fire on injected drift and pass clean after.
- **Confirmed (not changed):** the "27-case set" (matches `docs/BENCHMARK.md`, distinct from the 75
  skill eval cases). **Flagged only:** the roadmap "104 files" line (now 112 on disk; original
  counting basis ambiguous — left as-is per no-fabrication rule).

## 2026-07-15 — cross-surface adversarial audit (desktop offline ↔ Claude app on Windows/Mac)
Audited atoms/skills/canonical files through the lens of multi-step workflows that pass data between
the offline desktop tools and the Claude/ChatGPT app. Canonical JSON integrity clean (0 malformed).
Findings + fixes:
- **CRITICAL — CRLF broke my own freshness guard on Windows.** A `core.autocrlf=true` checkout gives
  the LF-committed sources CRLF, so their sha256 no longer matched the LF manifest → false "stale"
  for the whole clone (and rebuilding there breaks Linux/CI). Fixed: `offline_index._sha256` +
  `registry_currency._sha256` normalize CRLF→LF before hashing (no-op on LF, proven zero churn);
  `.gitattributes` pins text sources to `eol=lf`. Verified a CRLF copy now hashes identically.
- **HIGH — profile didn't round-trip.** Desktop kept `teacher.local.json`, apps use
  `my-teacher-profile.md`, nothing bridged them. Added `profile_wizard.py --export-md/--import-md`
  (human-readable + embedded exact JSON; lossless through a Notepad BOM + CRLF). Documented in
  `wizard.md` + `DEPLOYMENT_SURFACES.md`.
- **MEDIUM — LibreOffice PATH-only discovery** reported a false capability gap on Win/Mac (soffice
  isn't on PATH there). `office_authoring.convert()` now falls back to the standard per-OS install
  locations; the document is still produced regardless.
- **Documented gotchas:** `python3` vs `py`/`python` on Windows; the Notepad `.txt`/"All Files"
  trap; line-ending safety — all in `DEPLOYMENT_SURFACES.md` "Cross-platform notes" + the gpt/web
  README save step. Minor open note: `--demo` needs `teacher.example.json` (gitignored) present.

## 2026-07-15 — offline-index freshness guard (committed manifest + auto-rebuild)
The gitignored `canonical-sources/index/offline.db` silently went stale when the D3 fix regenerated
the standards JSON without a rebuild, and nothing detected it. Fixed structurally:
- `offline_index.py` gains a single `source_files()` enumerator (so the fingerprint can't diverge
  from what `build()` indexes) and, on `--build`, writes a **committed**
  `canonical-sources/index/index-manifest.json` = sha256 + bytes of every source (no timestamp/engine,
  so it's byte-stable — a diff means the inputs changed). New `drift_report()`/`--verify` (exit 1 if
  stale); `--stats` shows freshness. The db stays gitignored.
- `sync_check.py` check 14 (**hard gate**, runs in CI via the existing step) fails if the committed
  sources no longer match the committed manifest — reads only committed files, so it fires on a fresh
  clone and in CI, naming the changed files + the rebuild remedy.
- **Producers self-heal:** `parse_fl_standards.py` (the culprit), `msid_lookup.py --apply`, and the
  harvest orchestrators rebuild the index after writing a source (non-fatal, `--no-index` escape);
  `local_harvest.py`/`harvest_all.py --push` now also stage the refreshed manifest.
- Rebuilding also resolved the actual staleness: the index no longer serves pre-D3 statement text.
- **Closes** the prior follow-up "rebuild offline.db before any statement-text benchmark" — the guard
  now enforces freshness. Residual: `--no-index` + force-past-red-CI can still commit a stale manifest
  (deliberate act, not the silent default).

## 2026-07-15 — governed document benchmark (generation track shipped; ingestion track scaffolded)
A reproducible, honesty-gated benchmark for "is TOS above and beyond the AI alone for document
work." Lives under `benchmarks/` + `tools/run_benchmark.py`; report `docs/BENCHMARK_COMPETITIVE.md`
(generated, `human_review_required`), landscape `docs/COMPETITIVE_LANDSCAPE.md` (dated/cited).
- **7 axes** (grounding · governance · generation · differentiation · format · cost · ingestion)
  with a per-axis **win-bar** — "above and beyond" is a number with a stated margin, not an
  adjective. Five arms: native Claude / ChatGPT / Gemini, consumer ed-tools, OSS parsers
  (ingestion track).
- **Honesty gate:** `run_benchmark.py --check` fails the build on any scored row lacking an evidence
  receipt; a result with no evidence stays `unrun`, never a fabricated number (a fabricated result
  is itself QG §37). Report is generated from scorecards, never hand-edited.
- **Headless TOS arm** reuses the repo's own tools as objective graders — `offline_index.py`
  (grounding-or-empty), `score.py` (the gated verdict), `validate_document.py` (binary validity).
  Live results: impossible standards asks return empty; the fabricated `3.NF.A.9` case → Rejected
  via critical-failure override; the Office engine reports an honest capability gap (no python-pptx
  here) rather than a fake binary. Subjective generation quality (axis 3) is blind-judged for ALL
  arms equally — no scripted edge for TOS.
- **Honest scoping** (approved decision): TOS leads on grounding/governance/generation and proves
  it now (generation track); raw PDF parsing is a fight vs Docling/Marker/Unstructured, so the
  ingestion track targets parity + a retrieval_state honesty edge, possibly by wrapping a
  best-in-class engine as a docintel parser tier. The **loss→new-eval loop**
  (`validate_outputs.py --promote`) is the engine that keeps TOS ahead.
- **Follow-ups:** execute the hosted arms (evidence-backed) to fill competitor cells; synthesize the
  ingestion-track adversarial corpus (CJK/nested-container/merged-cell — the docintel fixture gap).
  (The prior "rebuild offline.db before a statement-text benchmark" caveat is resolved — see the
  freshness-guard entry above; the index is rebuilt and the drift guard now enforces it.)

## 2026-07-11 — onboarding parity, Reference Pack, scenario-test defect fixes
Shipped on `claude/educator-tools-k12-plan-f49yju` (source: Monarch Learning Academy scenario test):
- **Onboarding:** `implementation/claude/README.md` (teacher-voice, Claude Code/Cowork + claude.ai
  doors; naming resolved — one plugin bundle, both surfaces); root README "How you use it" now has
  the two platform doors; `wizard.md` step 8 defines the **requirements map** (per-row source +
  external-authority citations, DRAFT footer) once for all platforms.
- **Reference Pack:** `tools/export_reference_pack.py` → `implementation/gpt/web/reference-pack/`
  (11 curated files ≈3.3MB: 6 FL standards files w/ full statements, course codes, districts,
  school types, consolidated teaching-frameworks, generated MANIFEST receipts; build fails on any
  uncited file; `--check` = sha256 drift guard + ≤15-file cap). TOS-skills.md HEADER: standards
  corpus ✅-with-pack, "Two ways to set up", requirements-map section. Florida-only honesty line.
- **Defects fixed:** stale paths repo-wide (old un-grouped `skills/<name>/`, `shared/schools/` →
  `canonical-sources/schools/`); NCES PSS grade codes decoded in the private-schools index
  (verified 1–17 map; raw kept as `*_code`; e.g. Monarch = PK–8 not "2–13"); FL standard
  statements no longer truncated at 300/200 chars (full text regenerated, all codes unchanged — 6,583 at the time);
  `private_independent` school type added; ChatGPT profile persistence (`web_note` → "On ChatGPT"
  blocks) + export generator fixes (inline trigger-phrase parsing, sentence-complete do-not-use,
  no-PyYAML fallback description bug).
- **Follow-ups:** decode `religious`/`level` PSS fields once the NCES codebook is verifiable
  (nces.ed.gov blocked from the build env — no guessed labels); index decoded private-school grade
  fields in `offline_index.py` at the next db-schema change; requirements-map as a first-class skill.

## 2026-07-11 (later) — web→desktop audit fixes: explaining wizard + honest data contract + distribution
Source: 11-finding audit of the "ChatGPT chat → desktop app" teacher scenario. Shipped:
- **Web Setup Wizard** (`implementation/gpt/api/web-wizard.md`, embedded into TOS-skills.md by the
  generator): full 7-step interview with a say-it-out-loud WHY per question, plan-tier triage,
  explicit school-type step (wired to `fl-school-types.json`), and profile save-out help
  (downloadable-file offer, else exact Notepad/TextEdit steps). Canonical trigger unified to
  "set up my profile"; Claude wizard.md gains the explain-why principle + school-type sub-step
  (files name each other as siblings — keep step lists/whys aligned).
- **Honest completeness contract** (requirements map, both platforms): exact enumeration only via a
  true file read (data-analysis tool; report matched-N vs the file's `count`), otherwise labeled
  best-effort/retrieved; one subject per table (~40 rows, offer "next"); SS rows flagged the
  legacy-doc parse (flag removed 2026-08-13 — the SS parse is now faithful and CPALMS-verified).
- **Distribution:** `tos-reference-pack-onefile.json` (whole pack, one upload — fits ChatGPT Free's
  ~5-slot Projects) + byte-reproducible `reference-pack.zip`; both rebuild-and-compare guarded in
  `export_reference_pack.py --check`. Plan limits stated honestly ("trust the upload screen").
  Generated docs are self-locating: repo URL in TOS-skills HEADER/FOOTER + MANIFEST (URL declared
  in `tools/url-provenance.json`, enforced by the drift guard).
- **Docs:** desktop-app/device-switch section (Projects follow the account; no Custom GPT needed),
  privacy note (personal-plan training toggle, dated wording; Team/Edu default), profile-save
  wording aligned with the wizard's real flow.
- **Follow-up:** consider single-sourcing the two wizard scripts (web-wizard.md / wizard.md).

## Validation note
Every skill ships `evals/evals.json` (prompts + assertions) and worked examples. The eval
**benchmark ran** on a representative 3-case subset (with-skill vs. no-skill baseline): **with-skill
12/12 vs. baseline 8/12** — biggest uplift in governance/auditability and standards rigor; no
regressions. Details in **`BENCHMARK.md`**. Widening to the full eval set is a follow-up.

## Confirmed decisions
Full-K-12 breadth-first standards; FULL §33.1 9-dimension weighting authoritative; QG canonical
names; build on `pptx/docx/pdf` for rendered outputs; the 5 reconstructed protocols are approved.

## Local-First / Modular (L-series) — in progress on `claude/educator-tools-k12-plan-f49yju`
Offline / low-token-overhead track extending F1–F6. Shipped: L1 local SQLite/FTS5 standards cache
(`shared/cache/`), L0 reversible setup preferences + L7 feed cadence (`profile_wizard.py --preferences`),
L2 opt-in `sqlite-vec` semantic index, L3 manifest-driven sync (`tools/sync_cache.py`), **L7 feed
self-update** (`shared/feeds/` + `tools/feeds_update.py`), and **L8 seed curation** — the
**`feed-curator` skill (19th)** + `tools/seed_curator.py` (validate/discover/propose, auto-apply only
mechanically-safe repairs, audit trail in `ledger/feeds-change-log.json` with `--revert`). Real-world
scope: OCPS (public, district 48) + Monarch Learning Academy (private, Orlando). Live web fetch is gated
by network policy — feed endpoints stay `verified:false` pending discovery where network
is open.

## Standards-verification phase — v1.2.0 (2026-08-10) — SHIPPED
Elementary Florida standards are now **verified against CPALMS**, not merely parsed.
**1,913 K-5 codes** (math 393 · reading/ELA 355 · science 636 · social studies 529), benchmarks and
access points, checked code-by-code in both directions: **1,795 verified**, **118 reached and
recorded as needing review** (see the 2026-08-11 correction below), 3 missing access points
recovered, 0 unexplained census deltas. Results live in provenance-stamped overlays
(`shared/standards/resources/florida/data/overlays/`); the parsed corpus is never mutated.

**Correction (2026-08-11).** An adversarial audit of the unattended-sweep design found that the
`confirmed` state was decided by a 0.97 similarity ratio — ~3 characters of slack on a median
statement. Reproduced: 100% of changed numeric bounds and 93.9% of *deleted* negations still
classified as confirmed. `confirmed` now requires normalized equality or a true prefix, an
untruncated card, and ≥40 normalized characters; the fuzzy band became a new `near_match` state.
All 1,913 shipped entries were re-judged offline (`--reclassify`, demote-only, idempotent): **117
demoted to `near_match`, 0 found actually wrong**. The overlay now records every disposition with
`needs_review`, so codes that were reached but not verified are no longer re-fetched forever.

New machinery: `tools/verify_standards.py` (offline resolver over the FL corpus — 6,583 codes then, 6,574 today + CCSS/NGSS
scheme checks + the mechanical §6 citation-mutation comparator) and `tools/cpalms_verify.py`
(polite, robots-respecting, resumable verification loop with reverse census). The resolver gates CI
through `validate_outputs.py` (`unresolvable_standard`, blocking) with negative-control fixtures
proving the gate gates.

Audit: `docs/audits/2026-08-10-launch-readiness-audit.md` (A1-A7 + A9; one OPEN finding, seven
residual risks). Follow-ups, explicitly deferred — **[superseded 2026-08-13: 0 codes remain — the sweep completed; see the manifest]** originally: 4,670 codes remained unverified in total; the
live, generated breakdown is `ledger/cpalms-run-manifest.json` (`python3 tools/cpalms_verify.py
--manifest` to refresh), which is authoritative over any count restated in prose:
**grades 6-12 of math/ELA/science/social studies** (4,096); **computer science** (569 at the time — 560 today after 9 retirements, of which
**189 are K-5** and have no overlay yet — elementary is *not* complete for this subject);
**ELD** (5). Also:
social studies remains low-confidence (19.5% whole-corpus) so its absences stay advisory;
[SUPERSEDED 2026-08-13: SS and ELD both crossed the 0.98 coverage threshold — their absences
now BLOCK. See the behaviour-change entry below and docs/RUNBOOK-cpalms.md §5.]
CCSS/NGSS remain scheme-only; a FLDOE source-document refresh would fix the legacy `.doc` parse
artifacts recorded as finding D-J.

**Correction (2026-08-13) — the root cause, and the tolerances it forced.** Every defect above
traced to one thing: `tools/parse_fl_standards.py` emitted an entire document table row as a single
`statement`, so **52.0 % of the then-corpus (3,425 of 6,583 statements) carried document furniture** —
labelled columns, table headers, and in Social Studies the *next section's heading*. That superset
is why the comparator could not test equality, why it accepted a prefix, and why the prefix widened
into the 0.97 band. The Social Studies document was additionally UTF-8 decoded as latin-1 and then
stripped of non-ASCII, destroying 324 apostrophes and 147 smart quotes (finding D-J).

The parse now extracts labelled fields and preserves characters; the corpus was regenerated under a
new gate, `tools/parse_diff.py`, which aborts unless the code set is unchanged **and** every new
statement is either a prefix of the old one or present verbatim in the source document. Result:
**6,583 codes at the time, +0/−0 per subject, furniture 3,425 → 0**.

With the corpus clean, the tolerances were **deleted rather than retuned** — no prefix rule, no
similarity band, no `MIN_CONFIRM_CHARS`, and `renumbered` now requires exact text plus uniqueness.
Measured across all 1,913 entries: **1,899 (99.3 %) match CPALMS exactly and 0 rely on prefix
containment.** Re-judgement moved **116 `near_match` → `confirmed`** and 1 → `statement_differs`,
with **0 demotions from `confirmed`**. **`needs_review` is now 2, not 117** — and both are genuine
CPALMS revisions (`SS.4.E.1.1`, `SS.5.G.2.1`) rather than artifacts of our own parse. Verified total:
**1,911 of the then-6,583**; 4,670 remained at that point (0 today — the sweep completed).

`needs_review` also reaches consumers now (N1): it is derived from overlay state rather than read
from a flag, and `validate_outputs.py` emits `standard_needs_review` as a warning. New standing
guards in CI: `--scan-parse-defects`, the splitter's `--self-test`, and a per-subject overlay write
lock that refuses a concurrent writer instead of silently losing its entries.

Two claims were corrected rather than left standing: the audit's **"two-source corroboration" is
false** (all five FL standards documents come from cpalms.org per `sources.json`, so agreement
proves *parse fidelity*), and **`SS.5.G.2.1` was misdiagnosed** as a parse loss when CPALMS had
revised the benchmark. Full write-up: launch-readiness audit **§10**. D-J is **RESOLVED**.

**Sweep complete (2026-08-13) — every Florida code verified.** The manifest reads
**verified 6,574 / needs_review 0 / remaining 0**. All six subjects are at 100 % against CPALMS:
math 1,127 · ELA 719 · science 1,450 · computer science 560 · social studies 2,713 · ELD 5. Two
census additions were admitted at the human gate with full provenance (`SC.912.L.15.In.6`,
`SS.8.E.2.AP.3` — real on CPALMS, absent from the source documents); nine retired CS standards are
recorded as `retired`, never as fabricated.

**Behaviour change: SS and ELD absences now BLOCK.** Both crossed `OVERLAY_TRUST_COVERAGE` (0.98),
so an absent `SS.*` or `ELD.K12.ELL.*` code is a blocking `not_found` rather than an advisory. This
is the designed endpoint — absence became evidence exactly when the corpus became fully
corroborated — and was verified with fabricated/verified/addition probes before and after each
write. The sweep also found and fixed four defects live: a 600-char statement truncation, a
stripped trailing colon, duplicate-id over-strictness, and a D-H recurrence through grade-span
expansion (15 real access points briefly reported absent; the census now sweeps each expanded grade
separately). P8 (adversarial audit) precedes any coverage claim in prose.

**Residual remediation (2026-08-14):** the sweep's debris field closed — D-H malformed-cards guard
revived and probe-proven; `_merge_entry` preserves overlay archaeology across re-verification;
`tools/audit_overlays.py` (10 checks + self-test) now re-proves every `confirmed` label in CI;
`standards_refresh --check` verifies manifest paths + duplicates; generators fixed before outputs
(metrics/index-note/exports regenerated); every stale count and "best-effort" claim in prose
corrected or dated; `retired`/`standard_retired` added to the standards-verification protocol; the
standing Routine repurposed to currency re-verification (stays disabled until a human enables it).
Later that day the Routine was **retired outright**: the currency re-check became repo code
(`tools/currency_recheck.py` + `.github/workflows/currency-recheck.yml`, weekly Mondays 09:23 UTC since 2026-08-14, plus
manual dispatch; the `schedule:` block is the enable switch) after the trigger-management tools proved to be
out-of-repo state a session cannot rely on. The Routine was deleted from the panel on 2026-08-14,
after the workflow's first live dispatch returned zero drift (200 oldest math codes + census clean).

**v1.3.0 cut (2026-08-15):** plugin/marketplace metadata is now generated
(`tools/export_plugin_manifest.py`) and freshness-gated in CI (sync_check check 21, fail-closed);
releases are one command (`python3 tools/version.py --release <patch|minor|major>`); the dormant
`plugin-autobump` workflow gives full autopilot when the owner uncomments its push trigger.
Installed plugins update on version bumps, so this release ships everything since 1.2.0 — the
completed CPALMS sweep, the remediation, the currency re-check, and truthful listing metadata.

**MCP tool surface shipped (2026-08-15):** 8 read-only verified tools (standards search,
code verification, citation-mutation check, validators) defined once in `tools/mcp_tooldefs.py`
and served four ways — plugin-shipped stdio (zero-step), one-click `.mcpb` for Claude Desktop,
a dormant hosted leg for claude.ai/ChatGPT (`deploy/mcp/`), and a generated Custom GPT Actions
schema (check 22; check 23 added 2026-08-16 holds the SDK-derived Claude schema to the same
registry). The "no provider client" rule stands — this is a server. Two platform
questions stay empirically open (Claude-for-Teachers connector self-serve; ChatGPT Plus
Developer mode) and gate doc claims only.

**MCP hardening — 22 audit findings (2026-08-16):** an adversarial audit of the surface above
(attacks executed, not code read) found 22 defects, all in transport, validation, packaging or
documentation; the tool logic audited clean. Highlights: a corrupt index could KILL the stdio
server mid-session; the advertised schemas were never enforced, so a bogus subject enum was
accepted and answered `count: 0`; Claude and ChatGPT were being handed different rulebooks for the
same eight tools; the rate limit and token gated `/v1/*` but not `/mcp`, while two shipped
documents said otherwise (both now carry dated retractions); all three launchers spawned `python3`,
which does not exist on Windows. Each fix ships with a broken twin that reproduces the finding
first. `sync_check` gained **check 23** (cross-platform schema parity).

**Round 2 — the endpoint that never answered (2026-08-16):** starting the hosted server on a real
network port for the first time showed `/mcp` returning **HTTP 500 to every request** since the
day it shipped: Starlette does not run a mounted sub-app's lifespan, and that lifespan creates the
session manager's task group. Every test used an in-memory transport no real client uses. Fixed,
and now covered by a real-socket end-to-end probe plus a twin that keeps the outage from returning
quietly. The same round made nine drift checks fail-closed (a guard that crashes was printing a
note and passing), stopped `security_scan` from exiting 0 with no scanners installed, made
`plugin-autobump` run the real CI gate set before it can cut a release, taught `doctor_env` to look
for the SDK in the isolated venv where it now lives, and added `tools/mcp_smoke.py` — the
one-command PASS/FAIL script a Mac or Windows teacher runs and pastes back, which is the only
evidence available for the UNTESTED entries in `docs/MACOS.md`.

## Open items (optional follow-ups — core build complete)
1. Widen the eval benchmark to the full 27-case set (subset done — `BENCHMARK.md`).
2. Florida wired + **corpus stored** (`resources/florida/` + `sources.json`, 104 files) with
   `tools/standards_refresh.py` to crawl CPALMS/FLDOE/WIDA for updates; add other states via the same template.
3. Deepen the ontology; optional LLM-as-judge automation; tag a `v1.0.0` git release.

## Success metrics (Phase E)
Live dashboard: **`docs/METRICS.md`** (regenerate with `python3 tools/metrics.py`; freshness is
gated by sync_check check 16). The numbers are deliberately NOT mirrored here — a hand-typed
mirror of generated output is the exact drift class check 16 and check 21 exist to kill.
