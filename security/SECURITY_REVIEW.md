# SECURITY_REVIEW.md
## Security & safety review — v1 ecosystem
Date: 2026-06-20 · Scope: all 11 skills, 6 protocols, shared core, tooling. Reviewed against
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
| **Ecosystem integrity (drift)** | ✅ Pass | `tools/sync_check.py` enforces the 8 QG repository invariants + per-skill reference sync; PASS across 11 skills; negative test confirms it catches drift. |

## Residual risks / follow-ups
- **Standards licensing (state corpora).** Bundling full state standard sets has licensing
  considerations — gated behind a licensing check before any corpus is added (`state-standards-model.md`).
- **Bias/readability are review-based, not automated.** A future check could score reading level and
  flag non-inclusive patterns programmatically.
- **PII check is token/pattern-based.** The drift guard catches obvious cases; it is not a full PII
  scanner. The primary control remains the placeholders-only design + human review.
- **Eval coverage.** The benchmark covered a 3-case subset; widening it strengthens assurance.

## Conclusion
No critical issues. The v1 ecosystem upholds the safety constraints by design (placeholders-only,
no fabrication, human-in-the-loop, legal boundaries) and by enforcement (drift guard + Quality
Gates). Residual items are improvements, not blockers.
