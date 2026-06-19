# failure-recovery.md
## Failure Recovery Protocol
Version: 0.1 (DRAFTED from Quality Gates references — pending your review)
Derived from: QG §§76–77 (quality system recovery), §91 (recovery procedures), §46–50
(remediation), §13 (safety gates), §37 (automatic failures).

> **Status note.** Listed as "complete" in QG §2.1 but not delivered. Faithful reconstruction.

---

## 1. Purpose

When something goes wrong — a generation fails, a gate detects a critical failure, an input is
missing or malformed, or a tool/skill errors — the ecosystem should **degrade gracefully, tell the
user the truth, and recover in a documented, auditable way** rather than emitting a broken or
misleading artifact. This is the operational complement to Quality Gates' recovery framework
(QG §§76–77, §91).

## 2. Recovery workflow (QG §§77, 91)

```
Detection → Classification → Investigation → Containment → Remediation → Validation → Closure
```

- **Detection** — a failure or deficiency is identified (by a skill, a gate, or the user).
- **Classification** — by severity (QG §18: Informational→Critical) and type (integrity, safety,
  governance, accuracy, process).
- **Investigation** — identify cause and affected outputs.
- **Containment** — stop the bad artifact from advancing (a critical failure blocks approval,
  Invariant §96.5).
- **Remediation** — correct the root cause (remediation framework, QG §46–50).
- **Validation** — re-run the applicable gates; completion ≠ success (QG §49).
- **Closure** — record outcome in the Quality Ledger (QG §94).

## 3. Graceful degradation rules

- **Never fabricate to recover.** Inventing a citation/standard/result to paper over a failure is
  an automatic critical failure (QG §37) — strictly worse than reporting the failure.
- **Partial is better than wrong.** If only part of a request can be met safely, deliver that part
  and clearly state what is missing and why.
- **Be explicit.** Tell the user what failed, what you did, and what they should check.
- **Preserve traceability.** Even failed attempts get a decision record (metadata-schema.md).

## 4. Failure type → response

| Failure | Response |
|---|---|
| Missing required input | Log assumption + safest default, or escalate (assumptions-protocol.md) |
| Unverifiable standard | Do not ship it; correct or escalate (standards-verification.md) |
| Critical safety/integrity failure | Contain → Reject → escalate; never override (QG §37, §36.4) |
| Tool/skill error | Report honestly; retry if transient; degrade to partial output |
| Conflicting requirements | Apply conflict-protocol.md hierarchy; escalate if high-stakes |

## 5. Validation

Phase A wires this into every skill's pipeline (steps 4–6) and the `quality-review` gate so that a
failed evaluation produces a truthful, recorded outcome rather than a silent bad artifact.
