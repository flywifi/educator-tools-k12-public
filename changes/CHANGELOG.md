# Changelog
All notable changes to the Teacher Operating System (TOS) ecosystem. Format follows
[Keep a Changelog]; this project uses [Semantic Versioning](https://semver.org/) — see
`CHANGE_MANAGEMENT.md` for the versioning policy.

## [Unreleased]
### Fixed — parser hardening (2026-08-11)
- **The card parser now slices per card, so markup cannot cross a card boundary.** The old pattern
  matched over the whole fragment with `.*?`/`re.S`: one card with unexpected markup made it walk
  into the next, **deleting the first card and stapling its CPALMS id onto the second card's code
  and statement** — a provenance URL resolving to a different standard than it claimed. Dates had
  the same shape of bug from the other side: collected globally and zipped by index, so a card
  without a date **inverted** dates rather than shifting them. Both are now structurally impossible.
  Markup is stripped before entity-unescaping, so tags can no longer reach `statement_verified`
  (the §6 origin form). Conflicting duplicate cards under one code become `ambiguous` instead of
  resolving by document order. `--no-include-practices` now exists.
- **Two consequences mattered more than the defects.** (1) If the exact code is absent **and** any
  card failed to parse, the row is `fetch_failed`, never `not_on_cpalms` — "we could not read the
  response" is not "this standard does not exist", and `not_on_cpalms` is the blocking state that
  reads as fabricated (D-K). (2) Skipping malformed cards would have **re-created D-H**: the census
  loop stopped on "no parsed cards", so unparseable markup would have ended a sweep early and
  reported every unreached code as absent from CPALMS. Paging now stops only on a page with no card
  markers, and a census with any unparseable card writes no `census_diff`.
- **All four defects were latent** — 0 occurrences across 788 live cards (both endpoints, four
  subjects, five grade levels) and 0 across the 1,913 shipped entries. Shipped `date_revised` values
  were correct *by luck*: every real card carried a date, so the positional zip happened to align.
  The new parser is **byte-identical** to the old one on all five committed fixtures and all 788
  live cards; `--reclassify` reports **0 changed**. 54 offline probes, now running in CI.

### Fixed — verification correctness (2026-08-11)
- **`confirmed` now means the text matches, not "within 3%".** An adversarial audit refuted the
  predicate and the refutation reproduced exactly: `confirmed` was decided by a 0.97 similarity
  ratio — about three characters of slack on a median 91-character statement. Measured against real
  FL statements, a single-token mutation still classified as `confirmed` in **100%** of changed
  numeric bounds (`within 20` → `within 10`), **93.9%** of *deleted* negations, 86.8% of `and`→`or`
  and 80% of `greater`→`less`. Three further holes: an **empty** corpus statement prefix-matched any
  text at all including hostile text; a short statement matched a longer different benchmark; and
  server-side truncation **without** an ellipsis matched and was not flagged, putting a severed
  fragment into the overlay as the §6 origin form. `confirmed` now requires normalized equality or a
  true prefix, an untruncated card, and ≥40 normalized characters; the fuzzy band became a new
  **`near_match`** state — a review signal, never a verification.
- **All 1,913 shipped entries re-judged** offline against their recorded CPALMS text
  (`--reclassify`, demote-only, idempotent): **117 demoted to `near_match`, 0 found wrong.** Verified
  coverage is now stated as **1,795 verified + 118 needing review**, not 1,913 verified. README,
  STATE.md, METRICS and the launch audit all corrected; the audit carries a second dated note.
- **The overlay records every disposition**, not only successes. A code that came back
  `not_on_cpalms`, `ambiguous` or `near_match` had no overlay representation, and since both the work
  list and the manifest are set differences over the overlay, those codes were re-fetched from CPALMS
  **on every run, forever**. They are now recorded with `needs_review: true`; transients
  (`fetch_failed`, `skipped_robots`) are deliberately excluded so they are still retried. The manifest
  reports `verified / needs_review / remaining` under an asserted sum identity.
- **The census can now express corpus grade bands.** `912`/`68`/`612`/`K12` are not CPALMS filter
  labels, so a band census failed discovery, recorded an error, and **still wrote a diff declaring
  every code in scope absent from CPALMS** — 2,716 of the 4,670 remaining codes, 58% of the job.
  Bands now expand for the sweep while scope is computed from the band value; a census that errors
  writes `census_meta` for diagnosis but no `census_diff`; a zero-size scope aborts.
- **A `cpalms_addition` can no longer overwrite a real verification** (the merge above it guarded on
  `checked_at`; this block assigned unconditionally). Overlay and manifest writes are now atomic
  (tmp+rename), so a crash mid-write can no longer leave a truncated file that every reader refuses.
  `--include-additions` previews its additions in the dry-run, where the block was unreachable — the
  human gate could not see what it was approving. Transient rows are reported rather than silently
  omitted from the review queue. Overlay `coverage` counts verified in-corpus codes only.
- **`tools/cpalms_verify.py --self-test` now runs in CI.** It never did, despite being cited as
  evidence in two audits. It is also offline by construction rather than by luck — the suite blocks
  `_fetch`, so an accidental network call fails loudly instead of crawling CPALMS. 42 probes.
- **Withdrew the in-flight report convention** introduced hours earlier. It existed only because the
  overlay could not record non-successes; making the overlay total removes the pending-file
  bookkeeping, the retention problem, and a livelock in which unresolved rows were re-sliced and
  re-fetched on every firing. Reports are scratch again. The scheduled Routine is **paused**.

### Added
- **The standards sweep now resumes across sessions.** The verification job spans sessions, but its
  only resume state was a report file whose path embeds a session UUID — so a fresh session found no
  report, took the "first run" branch, and silently re-fetched every already-verified code
  (~1.8 h of redundant load on a public education site). Phase V now derives its work list from the
  **committed overlay**, which is the durable record: already-verified codes are skipped
  (`--ignore-overlay` opts out for a currency refresh), an unreadable overlay aborts rather than
  degrading to "verify everything", and a fully-verified scope exits before the robots fetch.
  `--require-resume` turns a missing report into a loud abort naming the cause instead of a restart
  that looks healthy in the log.
- **`--manifest` → `ledger/cpalms-run-manifest.json`** (generated, offline, ~1 s): verified vs
  remaining per subject *and per grade*, by set difference over committed state, anchored to a
  commit and to per-corpus hashes so staleness is detectable. It is authoritative over any standards
  count written in prose.
- **`docs/RUNBOOK-cpalms.md`** — what a session with no prior context needs to continue the sweep:
  the decided list, six non-obvious constraints each cited to the commit that discovered it
  (per-grade census sweeps, access-point endpoint routing, unapplyable `--codes` reports, `--resume`
  not re-deriving scope, `skipped_robots` poisoning a resume file, `Z`-form timestamps), the
  copy-paste chunk block, and the done-chain through the human gate to CI. Referenced from
  `CLAUDE.md` so it surfaces at session start. This knowingly breaks the repo convention that
  handoff files are gitignored; the rationale is stated in the file.

### Fixed
- **Three shipped coverage counts were wrong** (v1.2.0), all from typing counts instead of computing
  them: `STATE.md` said 3,096 codes remained across grades 6-12 (true: **4,096** for those four
  subjects, **4,670** overall); computer science (569, of which **189 are K-5**) and ELD (5) were
  omitted from the deferred follow-ups entirely; and `docs/METRICS.md` claimed "elementary (K-5)
  complete" while computer science K-5 was — and remains — unverified with no overlay. `metrics.py`
  now computes K-5 completeness per subject and names the gap, and counts verified codes by
  intersection with the corpus so census additions are not folded into coverage. `STATE.md` and
  `README.md` cite the generated manifest instead of restating figures. The launch audit carries a
  **dated correction note** (§6) rather than a silent rewrite — it records what was believed on its
  date — stating the wrong figure, the true figures, the cause, and the fix.

## [1.2.0] — 2026-08-10
### Added
- **Elementary Florida standards verified against CPALMS — 1,913 codes, 100% of K-5.** Every
  elementary code in math (393), reading/ELA (355), science (636), and social studies (529) —
  benchmarks *and* access points — was checked code-by-code against CPALMS in both directions
  (forward per-code classification + a reverse census that finds codes CPALMS has and the corpus
  lacks). Result: **1,912 confirmed**, 1 stale-wording finding, 3 missing access points recovered,
  **0 unexplained census deltas**. Findings are recorded in provenance-stamped overlays
  (`data/overlays/*.cpalms.json`, each entry carrying the CPALMS statement, id, URL, revision date,
  and check timestamp); **the parsed corpus is never mutated**.
  Real defects fixed along the way: two science access points (`SC.1.E.5.In.1`, `SC.5.L.14.In.2`)
  that resolved as **blocking `not_found`** — TOS was calling real SpEd standards fabricated;
  `SS.4.E.1.1`'s superseded wording; `SS.4.A.7.AP.3`'s absence; 503 access-point provenance URLs
  pointing at the benchmark preview path; a **silently truncating multi-grade census** that had
  reported 182 phantom "retirements" (censuses now sweep one grade at a time and union).
  **Launch-readiness audit** (`docs/audits/2026-08-10-launch-readiness-audit.md`): A1 28/28
  controls rejected · A2 22/22 cross-endpoint · A3 6/6 mutations + 0/16 false positives ·
  A4 zero unexplained deltas · A5 resume determinism · A6 parser/injection hostility ·
  A7 politeness · **A9 (new)** re-examined all 1,913 verified pairs with the strict §6 comparator.
  Closes with one OPEN finding and seven named residual risks — grades 6-12 remain unverified and
  social studies stays low-confidence by design.
- **CPALMS verification loop** (`tools/cpalms_verify.py` + overlay-aware resolver): verifies the
  FL corpus against CPALMS's free, keyless search-fragment endpoint (discovered + probed
  2026-08-09; registered as `cpalms-search-fragment-endpoint`, superseding the recorded
  "NO API access" limitation for verification purposes). Stdlib-only, robots-checked at runtime,
  honest UA, polite delays, checkpoint/resume; states `confirmed / statement_differs / renumbered
  / not_on_cpalms / ambiguous / fetch_failed`; `--apply` is dry-run and validates every row —
  `--write` (human-approved) records an overlay without ever mutating the parse corpus.
  `verify_standards.py` consumes overlays: verified stamps + CPALMS statement as the §6 origin
  form, `superseded_by` resolution for renumbered codes, and **computed** low-confidence — a
  subject exits advisory treatment at ≥98% overlay coverage, making its absences blocking again.
  Live smoke: real code confirmed (id 15307), fabricated code cleanly absent; the corpus already
  carries post-2021 `SS.7.CG.*` civics codes (renumbering-drift hypothesis disproven and
  documented rather than assumed).
- **`tools/verify_standards.py` — offline standards-code resolver** (delivers the
  standards-verification §5 promise; closes the gap where a fabricated-but-plausible code passed
  CI). Resolves cited codes against the committed FL corpus (6,583 enumerated codes with
  statement text) and validates CCSS/NGSS coding schemes offline. Honest-degradation states:
  `not_found` blocks only where the corpus is authoritative; best-effort corpora (Social Studies
  `.doc` parse, partial ELD) degrade to advisory — a parser gap can never manufacture a
  fabricated-standard verdict. Grade-band matching (K12/912/68/612 spans), case-canonical check,
  near-miss suggestions, `set_mismatch` flag, and the registry `statement` returned as the §6
  citation-mutation origin form. Wired in as `validate_outputs.py` `unresolvable_standard`
  (blocking) + `standard_advisory` (warning) with labeled skip on missing corpus; new
  `examples/known-bad/fabricated-standard.known-bad.json` enforced by check 1b (probe run both
  ways); CI runs the resolver's `--self-test` (28 probes + a shape audit over every committed
  corpus code; `--self-test-invert` proves the test can fail). quality-review §3 + rubric now
  require mechanical resolution before scoring Accuracy.
- **Governance-honesty wave** (7 bounded concepts adapted from an external research-provenance
  methodology review; nothing installed wholesale — full disposition in the review session):
  - **Citation-mutation check** (`standards-verification.md` §6): six enumerable mutations of a
    *real* standard's text (value drift, unit swap, caveat stripping, hedge removal, scope
    broadening, attribution laundering) + the **origin-form rule** — restate mutated standards in
    the registry's form. Wired into the universal validation checklist + quality-review Accuracy
    rubric.
  - **Decision-record honesty fields** (`quality-gates.md` §14 / §93.3): `checked` (explicit list,
    required whenever a dimension reports no issues) and `residual_risk` (review limits, required
    even on Approved); "error-free" claims barred. Mirrored in the synced operational rubric
    (62 copies) and quality-review.
  - **`human_review_focus`** (`metadata-schema.md`): optional list of the 2-3 highest-risk spots a
    human should check first, derived from the lowest-scoring dimensions — prioritizes review,
    never narrows it.
  - **Trigger evals** (skill template + quality-review seed set): ≥10 positive / ≥5 negative
    routing prompts per skill, pass bar ≥80%/≤20%, activation = actual invocation only, 2+
    negative activations = DETECTOR SUSPECT.
  - **Findings-log status vocabulary** (`docs/MACOS.md`, `CHANGE_MANAGEMENT.md`):
    RESOLVED / OPEN / **UNTESTED** (landed ≠ validated, per QG §49) + `Catchable:` field; existing
    rows retro-tagged (E1 is UNTESTED).
  - **Data-not-instructions at point of use**: the SECURITY_AND_SAFETY §6 rule now appears
    in-context in feed-curator, document-intelligence, and standards-updater (SKILL.md + deep
    references).
  - **Negative-control fixtures** (`examples/known-bad/` + `validate_examples.py` check 1b):
    deliberately invalid artifacts that MUST fail validation — a known-bad that passes now fails
    the build (gates proven to gate; probe run both ways).

## [1.1.0] — 2026-07-16
### Added
- **macOS / cross-platform hardening wave** (adversarially audited, 34 probes, all findings
  remediated): LibreOffice discovery via the canonical `_find_soffice()` everywhere (a normally
  installed `/Applications/LibreOffice.app` is found; PATH-only discovery removed from docintel);
  all internal child processes spawn `sys.executable` (never a bare `python3` — a macOS venv can
  otherwise split-brain onto the Xcode CLT stub); explicit `encoding="utf-8"` on every text
  open/read/write (locale-proof); **office render honesty** — soffice exits 0 even on a failed
  conversion (upstream tdf#148275), so `convert()` verifies the output file exists and the legacy
  parser reports `convert_failed` instead of a silent empty parse.
- **Managed-venv capability installer (PEP 668-proof):** `python3 tools/deps_preflight.py
  --install <capability|requirements.txt> | --install-all` installs optional capabilities into the
  isolated `.harvest-venv` (wheels-only; never system/Homebrew Python), dedupes shared requirements
  files, exits nonzero on a failed install, and `--python-path` prints the venv interpreter for a
  Claude Desktop MCP `command`/GUI launch. Requirements headers + docs point at it.
- **Doc-integrity + provenance guards (sync_check checks 15–20):** repo-wide dead path/link guard
  (fence-aware), METRICS freshness, component-doc coverage, `last_reviewed` freshness, **mac-lint**
  (`tools/mac_audit.py`: bare-interpreter spawns incl. variable-held argvs, encoding-less text opens
  incl. `io.open`), and **doc-source provenance** — an external URL cited in a maintainer-class doc
  must be registered in a source registry (exact-page matching per RFC 3986).
- **macOS source registry** (`canonical-sources/registries/macos-sources.json`, 41 entries): every
  authoritative source behind the macOS findings (Apple, Python/PEPs, Homebrew, Git, Claude docs,
  BSD/GNU, LibreOffice tdf#148275, RFC 3986), freshness-tracked by `source_currency.py`; naive
  `last_checked` dates now parse as UTC midnight instead of crashing the engine. `docs/MACOS.md`
  carries the findings log + maintainer notes.
### Fixed
- Supply-chain gate: pip-audit no longer audits the CI scanners' own toolbox (external CVE drift in
  dev-only deps reddened the branch); scanner stdout/stderr split so real CVEs are named, not opaque.
- `scrape_feed` capability pointed at a requirements file that never existed — repointed to
  `tools/requirements-scraper.txt`.
### Added (pre-wave)
- **Teaching-context & SOP layer** (`shared/context/`) — new architecture so the ecosystem adapts to a
  teacher's school/district context and **teacher-uploaded SOP files** (operating-reference pattern,
  harvested from a control-plane/route-plan skill). Adds: a **log of all 67 Florida county districts**
  (`florida-districts.json`, fillable stubs; Orange/OCPS populated incl. its own OCVS virtual school);
  a school-type taxonomy with **exception rule-sets** (`school-types.json`:
  traditional/magnet/charter/district-virtual/FLVS/home-education/private-scholarship — each declares
  how it overrides the traditional-public baseline); a **context contract** (`context.schema.json` +
  `context.py`: district/school_type/program/instructional_model/mandates/SOPs/authority_precedence/
  overrides) resolved first and validated; the **SOP upload model** (`sop-model.md`, read offline via
  docintel). Threaded into the contracts: `protocols/metadata-schema.md` gains a `context` envelope and
  `teacher-core` resolves context first and carries it across handoffs. School type governs standards
  applicability (home-ed/private contexts do not inherit the B.E.S.T./NGSSS mandate). District
  rules/norms + most school-type specifics are explicit stubs to fill per source over time.
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
