# QUALITY_MODEL.md
## Teacher Operating System (TOS) — Quality Model
Governance document (Quality Gates §2.1). Operational summary of the Quality Gates Protocol.
**Authoritative spec:** `protocols/quality-gates.md`. **Executor:** the `quality-review` skill.

---

## 1. Quality as an engineering discipline
Quality is defined, observable, measurable, repeatable, auditable, and traceable. No artifact is
"Final" until it passes the gates. Integrity precedes performance — a polished but untrustworthy
artifact is rejected.

## 2. The 9 dimensions and weights (authoritative — QG §33.1)
Integrity 25% · Accuracy 20% · Alignment 15% · Educational Quality 15% · Governance 10% ·
User Intent 7% · Accessibility 3% · Professional Quality 3% · Safety 2%. Each scored 0–5.
(An earlier condensed edition used 8 dimensions; the 9-dimension model is authoritative.)

## 3. Decisions
`Composite = Σ(score × weight)`. Approved ≥4.0 · Conditionally Approved 3.0–3.99 · Remediation
Required 2.0–2.99 · Rejected <2.0. **Critical failures (fabrication, real PII, unsafe output,
approval-without-evidence) force Rejected regardless of composite and may never be overridden.**

## 4. Gate order (early-terminate on critical failure)
Integrity → Safety → Governance → Accuracy → Alignment → Educational Quality → Accessibility →
Professional Quality → User Intent.

## 5. Decision records, certification, release readiness
Every decision is recorded (`protocols/metadata-schema.md`) and logged in the Quality Ledger.
Certification levels: Development → Review → Production → Governance Certified → Repository Certified.
Release readiness (a higher bar than approval) checks Quality · Governance · Documentation · Audit ·
Remediation · Certification.

## 6. Anti-patterns we guard against
Approval Without Evidence · Metric Worship · Documentation Theater · Audit Evasion · Gate Shopping.

---

## 7. Repository Invariants (QG §96) — enforced by `tools/sync_check.py`

1. Integrity precedes approval.
2. Evidence precedes certification.
3. Validation precedes release.
4. Audits remain independent.
5. Critical failures block approval.
6. Repository history remains traceable.
7. Quality decisions remain auditable.
8. Certification requires evidence.
