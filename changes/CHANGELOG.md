# Changelog
All notable changes to the Teacher Operating System (TOS) ecosystem. Format follows
[Keep a Changelog]; this project uses [Semantic Versioning](https://semver.org/) — see
`CHANGE_MANAGEMENT.md` for the versioning policy.

## [Unreleased]
### Fixed — the hosted `/mcp` endpoint had never worked, and nine gates could not fail (2026-08-16)
- **`/mcp` returned HTTP 500 to every request** from the hosted leg's first commit until now. It is
  the address a claude.ai custom connector and a ChatGPT Developer-mode server both point at, so
  Door 3 has never functioned. Cause: `build_app()` mounted the SDK's app with `Mount()`, and
  Starlette does not run a mounted sub-application's lifespan — the lifespan that creates the
  session manager's task group. Found by starting the server on a real network port, which no test
  in this repo had ever done: the self-test used an in-memory transport that bypasses ASGI, and
  yesterday's ASGI probes assert refusals that happen *before* the mount. Fixed by passing the
  sub-app's lifespan to the parent, and covered by a real-socket `initialize`/`tools/list`/
  `tools/call` probe plus a twin that rebuilds the broken mount and must still fail.
- **Nine of twenty-four drift checks disarmed themselves.** Checks 12–20 ended in
  `except Exception: print("[note] … skipped")`, so a guard that CRASHED was indistinguishable from
  a guard that found nothing and CI stayed green. All nine now fail. The only remaining skips are
  check 23's optional SDK and one explicit escape hatch (`TOS_SYNC_SKIP`) that is refused whenever
  `CI` is set. The sibling-freshness advisory — 84 of 85 notes on every run — collapses to one
  summary line so a loud message now has somewhere to land.
- **The supply-chain gate could pass having scanned nothing**: `security_scan` computed
  `status: "no_scanners"`, printed it, and never consulted it. It now returns a tri-state (0 clean /
  1 findings / **2 could not scan**), CI installs the scanners from the pinned file dependabot
  updates, and `repair_loop`'s exit 2 — the health engine itself broken, gated nowhere else — is no
  longer swallowed by `|| true`.
- **`plugin-autobump` ran 7 of ~25 checks and no security scan** before pushing a release to main.
  It now calls `ci.yml` itself (`workflow_call`), so the release path and the review path cannot
  drift. Still dormant; enabling it remains an owner decision.
- **`doctor_env` reported "not installed" for a correctly installed SDK** — it probed its own
  interpreter, while the isolated capability puts the SDK in `.harvest-venv-mcp_server`. It now
  probes that interpreter, names which one answered, reports all six `TOS_MCP_*` knobs, and checks
  index *freshness* rather than mere existence.
- **New `tools/mcp_smoke.py`**: one command that resolves what each launcher would spawn on the
  machine it runs on, checks the index, and holds a real stdio conversation with the server —
  printing a PASS/FAIL block to paste back. It is the only evidence obtainable for the UNTESTED Mac
  and Windows entries in `docs/MACOS.md`, and it runs in CI so the script itself is tested.
- Also: an unparseable first-party Python file is now a mac-lint **finding** rather than a note (it
  hid a real SyntaxError during this round); `cpalms_verify --self-test` no longer risks leaving a
  lock file in the production overlay directory; `mcpb pack` was run for real (1.8 MB bundle) and
  `mcpb validate` recorded as schema-only — it passes the broken twin, so the repo-side probes
  remain the guard.

### Fixed — MCP hardening: every finding of the cross-domain audit, remediated (2026-08-16)
An adversarial audit of the MCP arc above (attacks executed, not code read) found 22 defects — all
in transport, validation, packaging or documentation; the tool logic audited clean. Each fix ships
with a broken twin that reproduces the finding first.
- **Process death (C-1/C-2/C-3).** A corrupt `offline.db` raised `sqlite3.DatabaseError` past
  `call_tool`'s three-type except clause and **killed the stdio server mid-session** (reproduced:
  zero frames written, a queued `ping` never answered). Guards now sit at four boundaries —
  `_index_status`, the `call_tool` chokepoint, `handle_frame` (which is the only one that can
  catch a `json.dumps` TypeError on a non-serializable handler return), and the `serve()` loop,
  which also moved to `readline()` and survives a dead stdout. `SystemExit`/`KeyboardInterrupt`
  are never swallowed, and a probe asserts that.
- **Advertised schemas are now enforced (H-1) and identical on both platforms (H-2).** A bogus
  `subject` enum was accepted and answered `count: 0` — a silent false negative in an
  anti-fabrication system; 60 codes sailed past `maxItems: 25`. A stdlib validator in the registry
  now runs on every leg (explicit `null` on an optional property means absent — without that rule
  validation would have 400'd all hosted traffic). The SDK-derived Claude schema had dropped every
  enum and bound the ChatGPT schema carried; the wrappers now hold the constraints in their type
  annotations, and **sync_check check 23** compares the two semantically (skips only when the SDK
  is absent — parity is also asserted in the hosted self-test CI runs).
- **The security gate was decorative (H-3).** Rate limiting and `TOS_MCP_TOKEN` ran only on
  `/v1/*`; `/mcp` — the path every connector uses — was ungated and unthrottled, while
  `SECURITY_REVIEW.md` and `deploy/mcp/README.md` said otherwise. Now ASGI middleware ahead of
  routing (`/healthz` + `/openapi.json` token-exempt but rate-limited, so probes and ChatGPT's
  import still work), `hmac.compare_digest`, and an eviction policy that never resets the caller
  being throttled. Both documents carry dated **retractions**.
- **Launchers that exist on the teacher's machine (H-4).** All three shipped configs spawned
  `python3` — absent on Windows, absent from a macOS GUI PATH. `.mcpb` moves to manifest 0.3 with
  a `win32` override; `.mcp.json` uses `${TOS_PYTHON:-python3}` + `${CLAUDE_PROJECT_DIR:-.}`;
  `plugin.json` cannot be fixed (no per-OS command, no default substitution) so the Windows gap
  and its `claude mcp add --scope user` workaround are documented. `mac_audit` now lints JSON
  launchers, exempting the plugin **only while that workaround stays documented**.
- **Hosted-leg reality (M-1/M-2/L-10):** stateless by default (in-process sessions break
  scale-to-zero hosts), DNS-rebinding protection stated explicitly as off (enabling it naively
  rejects every request behind a load balancer), `TOS_MCP_PUBLIC_URL` + `forwarded_allow_ips`
  (without which the rate limiter degraded to one global bucket and ChatGPT rejected the import),
  `/healthz` echoes the computed URL, and a bad `TOS_MCP_PORT` refuses to start instead of
  crash-looping.
- **Dependency honesty (H-5):** semgrep pins `mcp<2` and silently downgraded the SDK in the shared
  venv; the diagnostic said "not installed" about a package that was installed. `mcp_server` is now
  an isolated capability, and the message names the version, the cause, and a fix that works.
- **Coverage the gates lacked (M-3/M-4/L-11):** the bundle builder and Actions generator self-tests
  now run in CI; `index_unavailable` returns HTTP 200 so ChatGPT relays the fix text instead of
  reporting a failed action; the export twin stages both artifacts in a tempdir instead of reading
  the production tree.

### Added — the MCP tool surface: verified lookups as callable tools on Claude AND ChatGPT (2026-08-15)
- **`tools/mcp_tooldefs.py`** — 8 read-only tools defined once (verified-standards search with
  the token-budget detail-strip, course/school lookup, CPALMS resources, fabrication-blocking
  code verification, citation-mutation check, by-value artifact validation, index honesty);
  governance rules served as instructions and per-description; excluded surface documented by
  name. 15 probes incl. leak/clamp twins.
- **`tools/mcp_server.py`** — stdlib-only stdio server (any Python ≥3.10, zero installs; stdout
  purity twin-proven) with `--print-config`; ships in the plugin (`plugin.json` `mcpServers`,
  mechanism verified against live docs) and via root `.mcp.json`; `tools/build_mcpb.py` stages
  the one-click Claude Desktop `.mcpb` (~9 MB, prebuilt index, staged-tree stdio probe).
- **`tools/mcp_http_server.py`** — hosted leg on the official `mcp` 2.x SDK, dormant until a
  human deploys `deploy/mcp/` (stateless, standards-data-only, no-auth by design, rate-limited);
  one app serves /mcp + REST + the generated Actions OpenAPI
  (`tools/export_actions_schema.py`, freshness = sync_check check 22) so ChatGPT teachers have
  a door whether or not Developer mode is enabled for them.
- Docs: `implementation/mcp/README.md` (four doors, "connect my tools" trigger asserted across
  the Claude README, the teacher-profile reference, and the web-wizard sibling), MAINTAINER
  with empirical checkpoints (Claude-for-Teachers connectors; ChatGPT Plus dev-mode) gating doc
  claims only; DEPLOYMENT_SURFACES MCP section; MACOS entries born UNTESTED; SECURITY_REVIEW
  hosted-endpoint threat model; dependency-policy records the stdlib-vs-SDK call both ways.
  Bugfix: system-prompt.md's phantom `atom_*` tool names aligned to tools.json.


## [1.3.0] — 2026-08-15
### Added — plugin metadata is generated-and-gated; releases are one command (2026-08-14)
- **`tools/export_plugin_manifest.py`** (new): plugin.json (version+description),
  marketplace.json (both version fields + listing description), and the skills/README.md catalog
  block are rendered from live facts — skills counted on disk (62), engines counted from
  versions.json's curated roster (16; shared/ dirs are not all engines and are never enumerated),
  verified standards from the CPALMS manifest (6,574). Identity fields pass through untouched.
  The marketplace's "15 governed K-12 teacher skills" (stale since 2026-06-27, survived two
  releases) is dead; the 11-of-62 catalog is a generated 62-row table. 12 self-test probes.
- **sync_check check 21** (fail-closed): committed manifests + catalog must equal a fresh render
  on every CI run; an ImportError in the generator is a failure, not a skipped note. The
  plugin-manifest hash left the registry-currency watchlist (generator + gate is strictly
  stronger).
- **`tools/version.py`**: `--release <patch|minor|major|X.Y.Z>` — one command bumps the whole
  chain (incl. the never-before-written `versions.json.updated` and both marketplace fields),
  regenerates all generated metadata, and rolls `[Unreleased]` into a dated section (refusing an
  empty one). check() now flags missing files instead of silently passing, gates both
  marketplace versions, rejects malformed semver, and errors on unknown bump targets (was a
  silent exit-0). 18 self-test probes; CI-wired.
- **`.github/workflows/plugin-autobump.yml`** (new, DORMANT): when the owner uncomments its push
  trigger (a reviewable commit), every merge to main auto-cuts a patch release so installed
  plugins — which update on version bumps, not pushes — track main with zero human steps. Two
  loop-prevention layers; full gate set in-job before the cut.
- Docs: DEPLOYMENT.md rewritten (wrong-repo reference fixed with a never-confuse note; plugin
  channel first; the bumps-not-pushes update truth + the 2026-06-29 reversal recorded; stamped
  and gated at last); CHANGE_MANAGEMENT §7 rewritten to whole-ecosystem rollback (the
  per-component advice contradicted the implementation and is retracted); STATE.md live counts
  removed in favor of generated sources; export_chatgpt's skill count computed at emit.

### Changed — weekly cadence enabled for the currency re-check (2026-08-14, owner decision)
- The `schedule:` block in `.github/workflows/currency-recheck.yml` is uncommented at
  `23 9 * * 1` (Mondays 09:23 UTC) after the first live dispatch from `main` returned zero
  drift in 11 minutes (200 oldest math codes re-confirmed; census spot-check clean;
  GitHub-runner egress to CPALMS proven viable). The owner also deleted the retired platform
  Routine from the claude.ai panel the same day — no out-of-repo state remains.

### Changed — the currency re-check is repo code; the platform Routine is retired (2026-08-14)
- **`tools/currency_recheck.py`** (new): drift detection over the ~200 oldest-`checked_at`
  in-corpus codes of the single oldest subject (`--ignore-overlay`; robots/politeness/checkpoint
  inherited from `cpalms_verify`), plus one per-grade census spot-check of the least-recently-
  censused scope (stateless rotation via `scopes[].generated_at`). Detect-only: no `--apply`, no
  `--write`, reports land outside the repo. Tri-state exits — 0 zero-drift (the deliverable),
  1 drift, 2 preflight red (`audit_overlays` gates every run), 3 environment blocked (robots,
  >10% transients, or a census that could not conclude) — so a throttled runner can never
  masquerade as a verdict. 14 self-test probes, each demonstrated to fail against a broken twin.
- **`.github/workflows/currency-recheck.yml`** (new): manual dispatch only; the daily
  `schedule:` ships commented out — uncommenting it is the human enable act, made as a
  reviewable commit. `contents: read`, single-flight concurrency, 90-day report artifacts.
- **Why retired, not repaired:** the Routine's prompt was mutable state on a third-party control
  plane, reachable only through a tool that may not be connected (proven twice in one session)
  and invisible to every repo gate. Everything the re-check needs now lives in the repo. The
  dormant Routine `trig_01Bd…` awaits a one-click deletion from the Routines panel, held
  meanwhile by two locks: paused, and its own prompt's do-no-work-at-0-remaining rule.
- CI: driver self-test + live-tree selection dry run added as hard gates; RUNBOOK §7 rewritten
  to the repo-code mechanism (the embedded-prompt drift-detector hack deleted with the Routine).

### Fixed — residual remediation: the debris field of the sweep, closed (2026-08-14)
- **`tools/cpalms_verify.py`** (C1): the D-H malformed-cards guard revived — per-grade
  `{kind}_malformed_cards` are now aggregated flat where the census abort and `_census_problem`
  actually read them (they had been stranded per-grade, so the guard was silently always-zero);
  `_merge_entry` preserves overlay archaeology on re-verification (`reclassified_*`,
  `url_repaired` carried by whitelist; retirement evidence nested as `prior_retirement` on
  un-retire — never blanket-carried); `OVERLAY_STATES` layered so `cpalms_addition` is legal in a
  committed overlay but still forbidden in a report row; dead `_SENTENCE_END` removed; module
  docstring rewritten to the real predicate and state list. 13 new self-test probes, each
  demonstrated to fail against the pre-fix code.
- **`tools/audit_overlays.py`** (C2, new): the 6,588-entry overlay record gets a standing CI
  integrity gate — ten checks (state legality, offline re-proof of every `confirmed` label, URL
  routing, id-bleed, extras/retired completeness, manifest identity + sha256, coverage floats,
  scope shapes, timestamp shape, unknown keys), with a `--self-test` that mutates a fixture once
  per check and requires each mutation caught. P8's transcript-only probes, mechanized.
  `standards_refresh.py --check` now verifies every manifest path exists and rejects duplicate
  records (one stale duplicate CS record removed from `sources.json`). `mac_audit` added to CI.
- **Resolver probes** (C3): `retired` (SC.K.PE.1.2 — withdrawn is a warning, never a fabrication)
  and `cpalms_addition` (SC.1.E.5.In.1) covered in `verify_standards.py --self-test` (30 probes);
  docstring rewritten to the post-flip truth.
- **Generators before outputs** (C4): `metrics.py` no longer hardcodes coverage status (computed
  from the overlays); `parse_fl_standards.py` index note + docstrings post-best-effort;
  `export_chatgpt.py` computes the FL count at export time; `export_reference_pack.py` drops the
  stale SS caveat; `data/index.json` regenerated under the 0-changed `parse_diff` gate;
  `implementation/gpt/` re-exported (stale reference pack incl. 9 retired CS codes cleared).
- **Prose sweep** (C5): every remaining stale count (6,583→6,574, CS 569→560) and "best-effort"
  claim corrected or dated across README, ARCHITECTURE, florida-best.md (+ new **Corpus entry
  schema** section, cross-referenced from `protocol-layer/metadata-schema.md`), states.json,
  RUNBOOK (`confirmed` definition aligned with §2.11; `anchor_commit` one-commit-lag note),
  STATE.md (incl. the false "4,670 remain"), cache/index docs, walkthrough transcript, and
  the quality-review rubric. `protocol-layer/standards-verification.md` gains the `retired`
  state (§3a/§4/§5), the `standard_retired` warning rule, and `near_match`/`cpalms_addition`
  in the state list; `not_found_low_confidence` reframed as the currently-inert safety net.

### Added — the full-corpus CPALMS sweep is COMPLETE (2026-08-13)
- **All 6,574 Florida codes verified against CPALMS's official text** — math 1,127 · ELA 719 ·
  science 1,450 · computer science 560 · social studies 2,713 · ELD 5. Manifest:
  `verified 6,574 / needs_review 0 / remaining 0`. Under strict equality: no similarity band, no
  prefix rule, no length floor.
- Two census additions admitted at the human gate with full provenance (`SC.912.L.15.In.6`,
  `SS.8.E.2.AP.3` — real on CPALMS, absent from the source documents; each confirmed by two
  independent sweeps). The first had been resolving as a **blocking "fabricated standard"** — a
  live D-K false positive, now ended.
### Changed — SS and ELD absences now BLOCK (threshold crossings)
- Both subjects crossed `OVERLAY_TRUST_COVERAGE` (0.98) and left `LOW_CONFIDENCE`: an absent
  `SS.*` or `ELD.K12.ELL.*` code is a blocking `not_found`. Verified with
  fabricated/verified/addition probes before and after each write; WIDA-scheme descriptors stay
  advisory (`unknown_framework`). Shipped probes that encoded the old advisory behaviour now
  assert the new one, with the reason inline.
### Fixed — four defects the live sweep caught that offline gates could not (2026-08-13)
- **600-char statement truncation** (`_sentence_trim` on the doc path) — a truncated statement is
  still a valid prefix, so `parse_diff` passes it by construction; caught as `statement_differs`
  on `SC.K12.CTR.7.1`. Guard removed + probe.
- **Trailing colon stripped** from `MA.912.C.4.6` by `_trim_edges` — the only such statement in
  the corpus, measured before fixing.
- **Duplicate CPALMS ids over-blocked**: identical text under two ids read as a conflict; now only
  differing *statements* are `ambiguous`, the lowest id is kept deterministically, and
  `duplicate_cpalms_ids` is preserved through `run_apply`.
- **D-H recurrence through grade-span expansion**: a span token ("912") joined four grades into
  one query — the exact multi-grade request D-H proved truncates. Invisible while spans were small
  (math 912 reconciled at 504); SS 912 at 1,599 returned 1,584 and called 15 real access points
  absent. Census now sweeps each expanded grade separately; two probes fail against the old code.
### Audited — before the coverage claim was written (2026-08-13)
- `docs/audits/2026-08-13-sweep-completion-audit.md`: every `confirmed` label re-proven **offline
  from stored texts** (6,574/6,574 equal); 84/84 mutations of real shipped pairs rejected; 9/9
  end-to-end gate cases correct; manifest identity + per-subject sha256s verified. One finding
  (S1): **69 SS access-point URLs still carried the pre-fix `PreviewStandard` path** — written
  before the A2-prior routing fix, never revisited because overlay-as-resume skips verified codes.
  Repaired from stored ids under the overlay lock, one spot-checked live. Lesson recorded: a fix
  to a writer does not repair what it already wrote.

### Fixed — corpus parse root cause, and the tolerances it forced (2026-08-13)
- **One defect explains the chain.** `tools/parse_fl_standards.py` emitted an entire document table
  row as a single `statement`, so **3,425 of 6,583 statements (52.0 %) carried document furniture** —
  `Clarifications`, `Date Adopted or Revised`, `Content Complexity`, `BENCHMARK CODE` headers, and
  in Social Studies the **next section's heading**. `SS.K.A.3.AP.2` ("Recognize a calendar.")
  carried "AFRICAN AMERICAN HISTORY Standard 1: Positive influences and contributions by African
  Americans", so searching that phrase returned a calendar benchmark. Separately the SS document —
  UTF-8, decoded as latin-1 then stripped of non-ASCII — lost 324 apostrophes, 147 smart quotes and
  6 dashes, with zero survivors. That superset is why the verification comparator could not test
  equality, why it accepted a prefix, and why the prefix widened into a 0.97 similarity band that
  passed **100 % of changed numeric bounds**.
- **The parse now extracts fields**: `statement` plus `clarifications`, `examples`, `remarks`,
  `complexity`, `date_adopted`, `related_access_points`. Characters are preserved, not folded.
- **Case-sensitivity is load-bearing** and cost two self-inflicted bugs before it was measured:
  `Examples:` is a table label (552 occurrences) but `for example:` is prose (6), and `BENCHMARK` is
  a header while `benchmark` is an ordinary word used 204 times inside real statements. Matched
  case-insensitively they truncated `SC.912.N.1.1` by 1,729 characters and `MA.1.M.1.AP.1b` at
  "mental measurement benchmark". Both are pinned with `(?-i:…)` and covered by CI probes — a
  truncation is invisible to the regeneration gate, because a truncated statement is still a prefix.
- **`tools/parse_diff.py` (new)** gates every regeneration: abort if the code set moves, or if a new
  statement is neither a prefix of the old one nor **present verbatim in the source document**.
  The escalation is stronger than the prefix rule, not a loosening of it, and fails closed.
- **Regeneration result:** 6,583 codes, **+0/−0 per subject**, furniture **3,425 → 0**, characters
  restored, 3,426 statements changed, one non-prefix (`SS.912.AA.2.16`, `Adams-On s` → `Adams-Onís`)
  proven verbatim in the source.
### Changed — the matcher collapsed to equality (2026-08-13)
- Deleted the bidirectional prefix rule, the 0.97 similarity band, and `MIN_CONFIRM_CHARS`.
  Measured over all 1,913 committed entries: **1,899 (99.3 %) already equal, 0 relying on prefix
  containment**, 6 differing only by whitespace CPALMS drops when rendering, and **2 genuinely
  divergent**. A character floor guards a *prefix* claim; against equality it was demoting 36 rows
  whose text is character-for-character identical, "Identify rhyme in a poem." among them.
- `renumbered` likewise requires exact text plus uniqueness, replacing a 0.92 similarity on a
  prefix. A close-but-inexact candidate becomes `ambiguous` with the candidate named.
- Overlay re-judgement (offline, deterministic): **116 `near_match` → `confirmed`**, 1 →
  `statement_differs`, 0 demotions from `confirmed`. `needs_review` **117 → 2**, and both survivors
  are real CPALMS revisions (`SS.4.E.1.1`, `SS.5.G.2.1`) rather than artifacts of our own parse.
### Fixed — `needs_review` now reaches the gate (N1) (2026-08-13)
- An overlay entry proves the **code exists**, not that our text matches. Every entry nonetheless
  got a bare `verified={}`, so a row CPALMS disagrees with was indistinguishable from a confirmed
  one — to a reader and to CI. `verified.state` is now carried, `needs_review` is **derived from
  state** rather than read from a flag (four committed entries had an unverified state and no flag),
  renumbered/addition rows are covered too, and `validate_outputs.py` emits `standard_needs_review`
  as a **warning** — the code is real and CPALMS's text is served, so blocking would fail a build
  over something the author cannot fix. Fabricated codes still block.
### Fixed — §6 mutation blind spot (R6) (2026-08-13)
- The tail-strip matched the bare word `example(s)` case-insensitively, cutting genuine prose:
  `ELA.4.R.3.AP.1` was compared as the single word "Identify". Label form only, applied before
  lowercasing. Text hidden from the comparator: **52.0 % of statements → 0.03 %**.
### Added — standing guards (2026-08-13)
- `cpalms_verify --scan-parse-defects` (in CI): fails if any statement carries document furniture.
  Validated both ways — 0 on the current corpus, 3,430/6,583 on the pre-fix baseline.
- `parse_fl_standards --self-test` (in CI): label-vs-prose splitter probes.
- **Overlay write lock** (`O_CREAT|O_EXCL`) held across the read-modify-write. Atomic writes prevent
  a torn file but not a **lost update**; a second writer is refused and told the holding pid, and a
  stale lock is reported with the command to clear it, never auto-broken.
- Both FTS indexes gained a searched-but-not-returned `detail` column, so moving clarifications out
  of `statement` did not silently cost ~39 % of the corpus's searchable word-instances.
### Fixed — two false claims corrected (2026-08-13)
- The launch audit's **"two-source corroboration" (§4.1) was false**: `sources.json` records all
  five FL standards documents as downloaded from cpalms.org. Agreement proves **parse fidelity**,
  not independent corroboration. Corrected in audit §10.1 and in the README.
- **`SS.5.G.2.1` was misdiagnosed** as a parse loss (§5.2). The source document has no `e.g.,`;
  CPALMS revised the benchmark. Corrected in §10.3.

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
