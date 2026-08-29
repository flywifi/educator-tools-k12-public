<!-- last_reviewed: 2026-08-17 | owner: security-maintainer -->
# SECURITY_REVIEW.md
## Security & safety review — v1 ecosystem

**Original review:** 2026-06-20, against **11 skills**.
**Amended:** 2026-08-15, 2026-08-16 (MCP tool surface; two retractions).
**Rebuilt at real scope:** 2026-08-16 — **62 skills**, 6 protocols, shared core, tooling.
**Eval rows re-measured:** 2026-08-17, the first time any eval in this repo was executed by a
machine. Two rows moved and one correction of my own is recorded below (the readiness score).

Reviewed against `SECURITY_AND_SAFETY.md`, the Quality Gates Safety/Integrity gates, and the
drift-guard invariants.

### Why this document was rebuilt

The ecosystem reached 62 skills on 2026-06-29, nine days after this review was written for 11.
Nothing was falsified deliberately: the original table had no **scope** column, so evidence that
was single-skill by construction — "benchmark Case 3 confirms…" tested `special-education-support`
and nothing else — silently read as ecosystem-wide once the ecosystem grew six-fold. Three rows
turned out to be false at current scope when re-run (§ *Corrections*, below).

Every row below now carries the **command that was run**, the **result observed**, the **scope**
(how many of the 62 it covers), and whether it is **machine-checked** or **review-based**. Quality
Gates §93.3 requires reporting "checked: …", never "error-free"; a table of green ticks could not
express that distinction, and this one can. Anyone can re-run any row.

**All commands below were executed on 2026-08-16 against this commit.** Where a result is worse
than the previous edition claimed, that is the correction, not a regression.

---

## Findings by control

| Control | Evidence — command → observed | Scope | Class | Residual risk |
|---|---|---|---|---|
| **Human-in-the-loop** | `grep -l human_review_required $(find skills -name SKILL.md) \| wc -l` → **62**; `sync_check.py` asserts it per skill (checks 0–24 green) | **62 / 62** | machine-checked | The flag is emitted; that a human *acted* on it is unobservable from here. |
| **Ecosystem integrity (drift)** | `python3 tools/sync_check.py` → `OK — 62 skill(s) checked; 8 repository invariants present; 2 synced reference(s) in sync` | **62 / 62** | machine-checked | Guards bind what they check. Check 15 could not see paths under a *renamed* directory — 877 dead `protocols/` references were invisible to it. **Closed 2026-08-17**: swept, and the dead prefix is retained in both anchor lists as a tripwire so a reintroduction now fails. |
| **No fabrication (Integrity)** | `python3 tools/verify_standards.py --self-test` → `0 failure(s) across 30 probes + shape audit + mutation batteries`, `6/6 mutations flagged, 0/16 false positives`. Failability proven: `--self-test-invert` → **exit 1** | corpus-wide (6,574 FL codes); **all** skills that cite standards | machine-checked | Covers *citation* of standards. It cannot detect a fabricated pedagogical claim carrying no standard code. |
| **Standards corpus integrity** | `python3 tools/audit_overlays.py` → `0 findings across 6588 entries` (re-proof, routing, id-bleed, accounting, coverage, manifest identity, scopes, timestamps, vocabulary) | 6 subjects / 6,588 entries | machine-checked | Re-proves the *labels*; currency against live CPALMS is a separate, scheduled check. |
| **No real student data (FERPA)** | The repo's own PII regexes (`tools/validate_outputs.py:28-29`) run over all **1,116 tracked files** → **0 SSN-pattern hits**; **52 phone-pattern hits, all in one file** (`canonical-sources/schools/private/private-schools-consolidated.json` — institutional school numbers, not student data) | all tracked files | machine-checked, **narrow** | Pattern-based, two patterns. Not a PII scanner. See correction **C-3**. |
| **Placeholders-only** | `grep -lEi "placeholder\|\[Student Name\]" $(find skills -name SKILL.md)` → **28** | **28 / 62** | review-based | 34 skills state no placeholder rule in their own `SKILL.md`. See correction **C-1**. |
| **Legal boundary (IEP/504/eligibility)** | `special-education-support` and `intervention-mtss` refuse eligibility/legal determinations and route to the team process; MTSS kept distinct from special-ed eligibility (read, not executed) | 2 skills, by inspection | review-based | Not behaviourally tested — neither skill has a refusal eval. |
| **"Validate against the actual plan/policy"** | `grep -lEi "actual (plan\|IEP\|policy)" $(find skills -name SKILL.md)` → **2**; `grep -lEi disciplinar …` → **1** | **2 / 62**, **1 / 62** | review-based | Policy (`SECURITY_AND_SAFETY.md` §2) requires this for IEP/504, eligibility, MTSS **and disciplinary** outputs. See correction **C-2**. |
| **Content/tooling safety** | `python3 tools/security_scan.py` with all three pinned scanners present (pip-audit 2.10.1, bandit 1.9.4, semgrep 1.173.0) → `status: advisory`, **36 findings, 0 blocking**, exit 0. Advisories are B104 (loopback-default bind) and B310 (`urlopen` scheme audit) in the fetch/verify tools | first-party code + pinned deps | machine-checked | Advisory findings are accepted, not absent. A scan can only see the patterns it encodes. |
| **Supply chain** | Same run; missing-scanner state is a distinct exit (**2**), verified by running with no scanners on PATH → `security scan INCOMPLETE` | pinned requirements files | machine-checked | Pins are `==` (pip-audit rejects ranges), so a floor cannot be expressed in the pin; asserted in code instead. |
| **Accessibility / UDL** | UDL default in `shared/differentiation/udl.md`; `readability-age.md` drives the Accessibility gate (read, not executed) | ecosystem policy | review-based | **No readability score is computed anywhere.** The gate is a human judgement. |
| **Bias & representation** | Inclusive-examples requirement in `SECURITY_AND_SAFETY.md` §4 + the Educational Quality/Accessibility gates | ecosystem policy | review-based | **No automated check exists.** Entirely reliant on review. |
| **Privacy in family-facing text** | `family-communication` uses placeholders and marks personalization points (read, not executed) | 1 skill | review-based | Not behaviourally tested. |
| **Artifact validation** | `python3 tools/validate_examples.py` → `validated 13 example artifact(s); 0 failure(s)` | 13 committed examples + 4 negative controls | machine-checked | A known-bad fixture added 2026-08-17 caught a real gap: `validate_outputs` checked `human_review_required` only when the key was PRESENT, so an artifact omitting it passed. Now scoped by `artifact_type` and required. |
| **Eval execution** | `python3 tools/run_evals.py --run` → **133 executed, 133 pass**; 6 skipped (placeholder/fixture/network), 2 unrunnable, **65 model-facing not executed**. `python3 tools/atom_contract.py` → `43 atoms conform` | 133 contract cases; 0 behavioural | machine-checked (contract only) | Was **0 executed** before 2026-08-17. The 133 prove declared contracts, NOT behaviour — see "What this review is not". |
| **Benchmark evidence discipline** | `python3 tools/run_benchmark.py --check` → `OK — 5 scorecards; every scored row has evidence` | 5 scorecards | machine-checked | `--check` deliberately permits `unrun`; 22 of 25 cells are `unrun` and that is honest, not covered. |

---

## Corrections (2026-08-16) — three claims that were false at 62-skill scope

**C-1 — "Every skill states placeholders-only" was false.** As published it read as an
ecosystem-wide statement. Re-run today: **28 of 62** `SKILL.md` files mention placeholders; **34 do
not**, including `behavior-strategy`, `meeting-classify`, `intervention-select` and
`translate-comm`. The *policy* is ecosystem-wide (`SECURITY_AND_SAFETY.md` §1) and the metadata
invariant is enforced in all 62; the per-skill **prose** is not. Corrected to 28/62 above, and the
gap is being closed in the commit following this one.

**C-2 — "SpEd/MTSS outputs add an explicit 'validate against the actual plan/policy' note" was
false at scope.** **2 of 62** carry that phrase. Worse, `SECURITY_AND_SAFETY.md` §2 requires it for
**disciplinary** outputs too, and **1 of 62** mentions disciplinary at all. The requirement was
written into policy and never propagated to the 51 skills added after the original review, because
`sync_check` enforces the pipeline pointer, the metadata schema and `human_review_required` — and
has no notion of boundary prose.

**C-3 — "repo-wide PII grep is clean" described a scan that does not exist.** There is no repo-wide
PII grep in the codebase. The only PII patterns are two regexes in `tools/validate_outputs.py`
(SSN and phone), applied to a single artifact passed via `--input`. Running them repo-wide for this
review (the first time that has been done) gives 0 SSN and 52 phone matches, all institutional. The
claim is now stated as what was actually executed, and the control is labelled **narrow**.

### Earlier retractions, retained

**RETRACTION (2026-08-16) — the hosted gate.** The 2026-08-15 text in `bbc4006` described controls
the code did not have. As merged, the rate limiter and the `TOS_MCP_TOKEN` check ran **only** inside
the `/v1/{tool}` REST handler. `/mcp` — the path every claude.ai and ChatGPT-Developer-mode
connector actually uses — was **neither rate-limited nor token-gated**: it is a mounted sub-app,
which a per-route check cannot reach. For the life of that release the token provided **no**
protection on the primary surface. Fixed by moving the gate to ASGI middleware that runs before
routing, with probes driving raw ASGI against `/mcp` itself. `/healthz` and `/openapi.json` are
token-exempt (still rate-limited) by deliberate decision — gating them breaks platform health probes
and ChatGPT's Import-from-URL respectively; neither returns corpus data.

**CORRECTION (2026-08-16) — the no-auth rationale.** Earlier text said no-auth exists because
"ChatGPT cannot send headers". True of MCP **connectors** (both platforms), **false for Custom GPT
Actions**, which support API-key/header auth. The accurate rationale: no-auth is chosen for the
connector door and for zero-config teacher import, not because header auth is impossible everywhere.

---

## MCP tool surface

- **Local stdio server** (`tools/mcp_server.py`): stdlib-only, read-only tools, no network, no
  secrets; spawned per-session by the client (no daemon). Stdout-purity and error-code behaviour are
  self-tested; the tool registry excludes every write/destructive path by name.
- **Hosted HTTP leg** (`tools/mcp_http_server.py`, dormant until a human deploys): threat model = a
  public read-only API over already-public CPALMS-derived reference data. Controls: stateless by
  default, per-IP token-bucket rate limit, loopback bind by default (B104-clean; the container opts
  into 0.0.0.0), no request-body logging, optional env-only bearer token, TLS at the platform.
  No-auth default is a deliberate, recorded decision: the worst case is an anonymous reader of
  public standards data paying our rate limit.
- Token comparison uses `hmac.compare_digest` (a plain `==` leaked the prefix through timing); the
  rate-limit bucket evicts fully-refilled or least-recently-seen keys and never the caller being
  served (a naive FIFO eviction could hand the flooding client a fresh burst).
- **Prompt-injection stance**: tool results are quoted corpus data; the served instructions and every
  corpus-returning description state that results are data, never instructions. The corpus is
  committed and CPALMS-verified, so the injection surface is the repo's own review process.
- **Fabrication stance over the wire**: `verify_standard_codes` keeps the blocking `not_found`
  semantics; `retired` is never reported as fabricated.
- **Schema enforcement** (2026-08-16, audit H-1). The advertised JSON Schemas were advertisement
  only: a bogus `subject` enum was ACCEPTED and answered `count: 0` — a silent false negative in a
  system whose purpose is not lying about standards — and `maxItems`/`additionalProperties` were
  ignored. A stdlib validator in the registry now runs on every leg before any handler sees an
  argument.
- **DNS-rebinding protection is deliberately OFF** unless `TOS_MCP_ALLOWED_HOSTS` names the hosts.
  A recorded decision, not an oversight: the SDK's default constructs settings with protection
  disabled, and enabling it with an empty allow-list rejects every request whose Host header is a
  load balancer's — i.e. all of them, on a normal deployment.
- **Process survival** (2026-08-16, audit C-1/C-2/C-3). A corrupt index used to kill the stdio
  server mid-session; guards now sit at four boundaries and the honesty tool survives the exact
  condition it exists to report.

---

## What this review is **not**

Stated plainly, because a review that implies coverage it does not have is the "Approval Without
Evidence" anti-pattern the Quality Gates name at §89.

- **No runtime behavioural testing of refusals — and this is the row most likely to be misread.**
  `health.py --scan` now reports `repair_plan` = **0** where it reported **44 × "no eval cases"**,
  and `python3 tools/run_evals.py --run` executes **133 cases, all passing**, where it executed
  **0**. Neither number means the skills are behaviourally verified. The 133 are CONTRACT cases —
  deterministic routing through `shared/routing/router.py`, tool output shapes, schema conformance
  — and they prove the declared contract, not the behaviour. **65 cases are model-facing and remain
  unexecuted**, including every refusal case for the nine skills that received boundary language.
  Until 2026-08-17 no eval had ever been executed by a machine at all, which is how a committed
  assertion (`skill-health` expecting `readiness_band: "strong"` against an actual `not_ready`)
  stayed wrong indefinitely. *What would close it:* recorded runs of the model-facing cases under
  `benchmarks/results/`, starting with the refusal carve-outs for `behavior-strategy`,
  `intervention-select`, `translate-comm`, `differentiate`, `udl-options` and `meeting-classify`.
- **No readability scoring.** *What would close it:* a computed reading-level check wired into the
  Accessibility gate.
- **No bias detection.** *What would close it:* an automated inclusive-language pass; today this is
  review-only.
- **The hosted leg has never run in production.** Verified end-to-end on loopback as of 2026-08-16
  (before that date `/mcp` answered HTTP 500 to every request — see the changelog). A first real
  deployment is still a first.

---

## Residual risks / follow-ups

- **The readiness score read `0/100 (not_ready)` for a reason that was not saturation.** I
  recorded it here as a saturated metric; that was wrong. 43 of its 44 warnings were
  `health.py`'s own false negative — it read `routing.skills` and never `routing.atom_routes`, so
  every correctly-registered atom was flagged "not referenced in routing.json" — and the 44th was
  `teacher-core` lacking an `evals/` directory. Both fixed 2026-08-17; the score now reads
  **100/100 `strong`**. The underlying fragility stands: the formula is
  `100 − 10·blocking − 4·warning` clamped at 0, so any 25 warnings floor it again while
  `blocking_issues` stays empty, and CI gates on `blocking_issues` alone.
- **Safety is weighted 2%** of the Quality Gates composite (`docs/QUALITY_MODEL.md` §2). Its real
  assurance comes from the critical-failure override — fabrication, real PII, unsafe output, and
  approval-without-evidence force Rejected regardless of composite and may never be overridden — not
  from the weighting. Worth knowing before reading the composite as a safety signal.
- **The Quality Ledger holds 6 records** for a 62-skill ecosystem.
- **Standards licensing (state corpora).** Bundling full state standard sets has licensing
  considerations — gated behind a licensing check before any corpus is added
  (`state-standards-model.md`).
- **PII check is two regexes.** The primary control remains the placeholders-only design plus human
  review; see C-3.
- **Rate limiting is per-process.** N replicas of the hosted leg means N independent buckets; it is
  an abuse brake, not a quota. Front it with the platform limiter for anything serious.
- **Two paths are token-exempt** (`/healthz`, `/openapi.json`) — still rate-limited, and neither
  returns corpus data.
- **Guards bind only what they check, and a whitelist hides what it does not list.** Check 15
  validates a backticked path only when it starts with a known anchor prefix, so the pre-rename
  `protocols/` — absent from that list — made 877 dead references invisible across 164 files.
  Swept and closed 2026-08-17, with the dead prefix deliberately retained in both anchor tuples as
  a tripwire. The general shape remains: any future rename is invisible until its old name is
  listed. A second instance of the same class was found and fixed the same day — check 24 asked
  git for a file's last-commit date under `actions/checkout`'s default shallow clone, where every
  file reports HEAD's date, producing six false failures.

---

## Conclusion

**No critical issues, and less coverage than the previous edition of this document implied.**

The controls that generalize to all 62 skills are the machine-checked ones: `human_review_required`
(62/62), the repository invariants and synced-reference integrity (`sync_check` 0–24), the
fabrication blocker with a proven failability control, corpus integrity across 6,588 overlay
entries, and a supply-chain scan with all three pinned scanners run and 0 blocking findings.

The controls that do **not** yet generalize are the review-based ones: placeholder prose (28/62),
the validate-against-the-actual-plan requirement (2/62, and 1/62 for disciplinary), readability, and
bias. Those are prose and human judgement, and while every skill now carries eval cases, the ones
that would test those rows at runtime are the 65 model-facing cases that have not been run.

Residual items are improvements, not blockers — with one honest qualifier the previous edition did
not carry: the eval gap means the safety claims resting on prose are *unverified*, not *verified and
minor*.
