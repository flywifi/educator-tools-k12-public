# assumptions-protocol.md
## Assumptions Protocol
Version: 1.0 (reconstructed from the Quality Gates references; approved)
Derived from: QG §4.1 Principle 8 (integrity before performance), §11.3 (disclosure),
§5.2 Integrity ("Were assumptions documented?"), §20 Constraints/Assumptions (Charter V3 §20).

> **Status note.** Reconstructed from the Quality Gates references and approved for use (v1.0).

---

## 1. Purpose

Educational requests are frequently underspecified (grade band, standard, time available, student
profile). Rather than silently guessing, the ecosystem **makes assumptions explicit, surfaces them
in the output, and escalates when an assumption is too risky to make alone.** This is an integrity
requirement: QG treats undisclosed assumptions as an integrity weakness (§5.2, §11.3).

## 2. When to log an assumption

Log an assumption whenever generation requires a fact the request did not supply, e.g.:
- grade band / reading level not stated → assume from context, log it;
- standard not specified → select the most likely standard, log the choice + why;
- pacing/time, class size, available materials, or student supports unspecified.

## 3. How to handle each assumption

1. **State it** in the artifact's metadata `assumptions:` list (metadata-schema.md).
2. **Surface the high-impact ones** visibly in the artifact body (e.g., a short "Assumptions"
   note), so the educator can correct them.
3. **Prefer the safest reasonable default** consistent with the persona + grade band.
4. **Escalate instead of assuming** when the assumption carries legal/safety weight — see §4.

## 4. Escalation (do not assume — ask or flag)

Escalate to the user (or hard-flag for human review) rather than assume when the assumption touches:
- a specific student's **IEP/504 plan** or eligibility (special-education-support);
- **safety**, medical, or legal determinations;
- anything that would require **real student data** to resolve (never request PII).

These map to QG critical-failure territory (§37, Safety/Integrity) — guessing here is prohibited.

## 5. Interaction with Quality Gates

The Integrity gate (§11) checks that assumptions were disclosed; the Accuracy gate (§9) checks that
assumed standards are still valid and verifiable. Undisclosed material assumptions reduce the
Integrity score and can trigger Remediation.

## 6. Validation

Phase A wires assumption-logging into each skill's pipeline step 2 (Protocol Enforcement) and the
`quality-review` Integrity check.
