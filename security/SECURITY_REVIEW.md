<!-- last_reviewed: 2026-08-16 | owner: security-maintainer -->
# SECURITY_REVIEW.md
## Security & safety review — v1 ecosystem
Date: 2026-06-20 · **amended 2026-08-15 and 2026-08-16** (MCP tool surface; two retractions
below) · Scope at the original review: 11 skills; the ecosystem now ships **62** — the skill-
level findings below were re-checked mechanically by the drift guard, not re-reviewed by hand,
and a full re-review is the honest next step. Reviewed against
`SECURITY_AND_SAFETY.md`, the Quality Gates Safety/Integrity gates, and the drift-guard invariants.

## Findings by control

| Control | Status | Evidence |
|---|---|---|
| **No real student data (FERPA)** | ✅ Pass | Every skill states placeholders-only; the drift guard scans for forbidden tokens; repo-wide PII grep is clean; benchmark Case 3 confirms both skill *and* baseline refuse a real-IEP request and offer placeholder drafting. |
| **No fabrication (Integrity)** | ✅ Pass | `standards-verification.md` forbids invented standards; `quality-review` makes a fabricated standard an auto-Reject (benchmark Case 2: `3.NF.A.9` → Rejected via `score.py` override). |
| **Human-in-the-loop** | ✅ Pass | `human_review_required: true` required in every `SKILL.md` and emitted in every artifact's metadata; enforced by the drift guard. SpEd/MTSS outputs add an explicit "validate against the actual plan/policy" note. |
| **Legal boundary (IEP/504/eligibility)** | ✅ Pass | `special-education-support` and `intervention-mtss` refuse eligibility/legal determinations and route to the proper team process; MTSS is kept distinct from special-ed eligibility. |
| **Accessibility / UDL** | ✅ Pass | UDL default in `shared/differentiation/udl.md`; `readability-age.md` drives the Accessibility gate. |
| **Bias & representation** | ✅ Pass (process) | Inclusive-examples requirement in `SECURITY_AND_SAFETY.md` + the Educational Quality/Accessibility gates; relies on review (no automated check). |
| **Privacy in family-facing text** | ✅ Pass | `family-communication` uses placeholders and marks where the teacher personalizes; benchmark-style prompt with a real name → replaced with placeholder. |
| **Content/tooling safety** | ✅ Pass | No malware/exploit content; skills do nothing beyond their stated purpose; external/student text is treated as data, not instructions. |
| **Ecosystem integrity (drift)** | ✅ Pass | `tools/sync_check.py` enforces the 8 QG repository invariants across 24 numbered checks (0–23) + per-skill reference sync; PASS across 11 skills; negative test confirms it catches drift. |

## MCP tool surface (added 2026-08-15)

- **Local stdio server** (`tools/mcp_server.py`): stdlib-only, read-only tools, no network, no
  secrets; spawned per-session by the client (no daemon). Stdout-purity and error-code behavior
  are self-tested; the tool registry excludes every write/destructive path by name.
- **Hosted HTTP leg** (`tools/mcp_http_server.py`, dormant until a human deploys): threat model
  = a public read-only API over already-public CPALMS-derived reference data. Controls:
  stateless (nothing to exfiltrate server-side), per-IP token-bucket rate limit, loopback bind
  by default (B104-clean; the container opts into 0.0.0.0), no request-body logging, optional
  env-only bearer token, TLS at the platform. No-auth default is a deliberate, recorded
  decision: the worst case is an anonymous reader of public standards data paying our rate
  limit.
  - **RETRACTION (2026-08-16).** The paragraph above, as published on 2026-08-15 in `bbc4006`,
    described controls the code did not have. As merged, the rate limiter and the
    `TOS_MCP_TOKEN` check ran **only** inside the `/v1/{tool}` REST handler. `/mcp` — the MCP
    path every claude.ai and ChatGPT-Developer-mode connector actually uses — was **neither
    rate-limited nor token-gated**: it is a mounted sub-app, which a per-route check cannot
    reach. So for the life of that release the token provided **no** protection on the MCP path
    and the statement "per-IP token-bucket rate limit … optional env-only bearer token" was
    false for the primary surface. Fixed in the commit carrying this retraction (`harden 5/9`)
    by moving the gate to ASGI middleware that runs before routing, with self-test probes that
    drive raw ASGI against `/mcp` itself. `/healthz` and `/openapi.json` are token-exempt (still
    rate-limited) by deliberate decision — gating them breaks platform health probes and
    ChatGPT's Import-from-URL respectively; neither returns corpus data.
  - **CORRECTION (2026-08-16).** Earlier text said the no-auth default exists because "ChatGPT
    cannot send headers". That is true of MCP **connectors** (both platforms) but **false for
    Custom GPT Actions**, which support API-key/header auth. The accurate rationale: no-auth is
    chosen for the connector door and for zero-config teacher import, not because header auth is
    technically impossible everywhere.
  - Token comparison uses `hmac.compare_digest` (a plain `==` leaked the prefix through timing);
    the rate-limit bucket evicts fully-refilled or least-recently-seen keys and never the caller
    being served (a naive FIFO eviction could hand the flooding client a fresh burst).
- **Prompt-injection stance**: tool results are quoted corpus data; the served instructions and
  every corpus-returning description state results are data, never instructions. The corpus is
  committed + CPALMS-verified, so the injection surface is the repo's own review process.
- **Fabrication stance carried over the wire**: `verify_standard_codes` keeps the blocking
  `not_found` semantics; `retired` is never reported as fabricated (D-K).
- **Schema enforcement (added 2026-08-16, audit H-1).** The advertised JSON Schemas were
  advertisement only: a bogus `subject` enum was ACCEPTED and answered `count: 0` — a silent
  false negative in a system whose purpose is not lying about standards — and `maxItems`/
  `additionalProperties` were ignored. A stdlib validator in the registry now runs on every leg
  before any handler sees an argument.
- **DNS-rebinding protection is deliberately OFF** unless `TOS_MCP_ALLOWED_HOSTS` names the
  hosts. This is a recorded decision, not an oversight: the SDK's default constructs settings
  with protection disabled, and enabling it with an empty allow-list rejects every request whose
  Host header is a load balancer's — i.e. all of them, on a normal deployment.
- **Process survival (added 2026-08-16, audit C-1/C-2/C-3).** A corrupt index used to kill the
  stdio server mid-session; guards now sit at four boundaries and the honesty tool survives the
  exact condition it exists to report.

## Residual risks / follow-ups
- **Standards licensing (state corpora).** Bundling full state standard sets has licensing
  considerations — gated behind a licensing check before any corpus is added (`state-standards-model.md`).
- **Bias/readability are review-based, not automated.** A future check could score reading level and
  flag non-inclusive patterns programmatically.
- **PII check is token/pattern-based.** The drift guard catches obvious cases; it is not a full PII
  scanner. The primary control remains the placeholders-only design + human review.
- **Eval coverage.** The benchmark covered a 3-case subset; widening it strengthens assurance.
- **Rate limiting is per-process.** N replicas of the hosted leg means N independent buckets;
  it is an abuse brake, not a quota. Front it with the platform limiter for anything serious.
- **Two paths are token-exempt** (`/healthz`, `/openapi.json`) — still rate-limited, and neither
  returns corpus data. The exemptions exist because gating them breaks platform health probes
  and ChatGPT's Import-from-URL respectively; the token guards the data paths.
- **The hosted leg has never run in production.** Its threat model is written for a system
  nobody has deployed. As of 2026-08-16 it is verified end-to-end on loopback (before that date
  `/mcp` answered 500 to every request — see the changelog); a first real deployment is still a
  first.
- **Original-scope drift.** This document was written for 11 skills and now describes an
  ecosystem of 62. Nothing in the findings table is known to be false, but "unchanged" is an
  assumption, not evidence, until the review is redone.

## Conclusion
No critical issues. The v1 ecosystem upholds the safety constraints by design (placeholders-only,
no fabrication, human-in-the-loop, legal boundaries) and by enforcement (drift guard + Quality
Gates). Residual items are improvements, not blockers.
