# quality-gates.md
## Quality Gates Protocol
Version: 3.0.0 (canonical consolidation of sections 001–100)
Status: Authoritative — this is the spec the `quality-review` skill enforces.
Source: reconstructed from the uploaded `quality-gates_*_FULL.md` sections 001–100.

> **Authority (§99–100).** Quality Gates is the repository's final quality authority governing
> evaluation, validation, approval, rejection, remediation, certification, release readiness,
> traceability, auditing, and continuous improvement. No artifact is "Final" until it passes.

---

## 1. Purpose & Scope (§§1–2)

Quality is treated as an **engineering discipline**: defined, observable, measurable, repeatable,
auditable, and traceable. The protocol turns `Request → Generation → Output` into
`Request → Generation → Validation → Quality Evaluation → Approval Decision → Output` — a
risk-reduction layer.

**Applies to** every repository artifact: skills, protocols, governance docs, tests, schemas,
audits, and releases. *Universal applicability (§2.2):* if an artifact can influence repository
behavior, educational outputs, governance decisions, certification status, or user experience, it
is in scope. Exceptions require documented rationale + governance approval + audit traceability
(§2.3); undocumented exceptions are prohibited.

**Non-goals (§1.5):** the protocol does not exist to maximize speed, minimize documentation,
replace expert judgment, or bypass governance.

---

## 2. Architectural role (§3)

```
User Request → Routing → Protocol Enforcement → Skill Execution → Validation
            → Quality Gates → Approval → Release
```

Generation determines *what* is produced; Quality Gates determine *whether it should be approved*
(§3.2 — separation of concerns). Quality Gates consume the outputs of the other five protocols
(metadata-schema, assumptions-protocol, standards-verification, conflict-protocol,
failure-recovery) as evaluation inputs (§3.3).

**Quality Gates may never (§3.5):** fabricate evidence, bypass governance, ignore critical
failures, approve unsupported artifacts, or suppress audit findings.

---

## 3. Quality philosophy (§4) & definition (§5)

Eight principles (§4.1): quality must be **defined, observable, measurable, repeatable, auditable,
traceable**; evaluation stays **independent** of creation where feasible; and **integrity precedes
performance** (a polished artifact with fabricated information is unacceptable).

**Definition (§5.1):** quality is the degree to which an artifact *simultaneously* satisfies user
intent, educational validity, governance, safety, and integrity requirements. **Balance principle
(§5.3):** no single dimension compensates for catastrophic failure in another.

---

## 4. Gate model (§§6–8)

A **gate** is a formal, evidence-based decision point. Outcomes (§6.2): **PASS**, **FAIL**,
**REMEDIATION REQUIRED**. Every gate defines purpose, evaluation criteria, evidence requirements,
failure conditions, escalation conditions, and approval conditions (§6.4).

**Gate taxonomy (§8):** Integrity · Accuracy · Alignment · Educational Quality · Governance ·
Safety · Accessibility · Professional Quality · User Intent. All relevant gates are evaluated
before approval.

### Gate execution order, with early termination (§20, §42.2)
1. Integrity → 2. Safety → 3. Governance → 4. Accuracy → 5. Alignment →
6. Educational Quality → 7. Accessibility → 8. Professional Quality → 9. User Intent.

Critical-failure detection happens as early as possible; execution may stop on a critical failure
(§20.4). Higher-priority gates can block lower ones (§42.3).

---

## 5. Scoring framework (§§21–34)

Every dimension is scored on a **0–5 scale** (§23): 0 critical failure · 1 major · 2 significant ·
3 acceptable · 4 strong · 5 exemplary.

### Dimension weights — authoritative (§33.1)
| Dimension | Weight |
|---|---|
| Integrity | 25% |
| Accuracy | 20% |
| Alignment | 15% |
| Educational Quality | 15% |
| Governance Compliance | 10% |
| User Intent | 7% |
| Accessibility | 3% |
| Professional Quality | 3% |
| Safety | 2% |

**Constraint (§33.3):** Integrity may never be weighted below Accuracy. Weighting changes require
governance approval (§32.5).

**Context-conditional Accuracy/Alignment (§33.4, added for multi-constituency support).** Score the
Accuracy and Alignment dimensions against the **applicable** standards per the context's
`standards_applicability` (`shared/context/`): verified FL B.E.S.T./NGSSS for `best_ngsss_apply`
(public/charter/virtual); the school's framework (`shared/standards/frameworks/`) for `school_defined`
(private); and, for `parent_selected` (home education), objective↔instruction↔assessment coherence —
**the absence of state-mandated codes is not a deduction or a critical failure** where no framework is
mandated. Weighting is unchanged. *Fabricating* a code/standard/citation remains a critical failure in
every context (§37).

> Note: an earlier condensed edition listed 8 dimensions (omitting Safety; User Intent 10 /
> Accessibility 2). **This 9-dimension model (§33.1) is authoritative.**

**Composite (§34.2):** `Composite = Σ(dimension_score × weight)`. Composite scores may inform but
never override critical failures (§34.5).

---

## 6. Decision framework (§§35–38)

### Approval thresholds (§35.3)
| Composite | Decision |
|---|---|
| ≥ 4.0 | Approved |
| 3.0–3.99 | Conditionally Approved (minor remediation) |
| 2.0–2.99 | Remediation Required |
| < 2.0 | Rejected |

### Critical-failure override (§§35.4, 36.4, 37) — never overridable
Any of the following forces **Rejected regardless of composite**:
- fabricated citation, source, audit, certification, or verification result;
- critical safety violation or severe risk concealment;
- approval without evidence, undocumented exception, or falsified documentation.

Permitted threshold overrides (§36.3) are rare, documented, justified, authority-approved, and
auditable (governance / risk / certification / emergency). The prohibited list above is absolute.

---

## 7. Multi-gate interaction & conditional approval (§§41–45)

**Conflict resolution hierarchy (§43.3):** integrity > presentation · safety > convenience ·
governance > preference · evidence > opinion. **Aggregation (§44.3):** critical failures override
aggregation; "Approved" requires all required gates to pass. **Conditional approval (§45)** is
allowed only when no critical failures exist, remediation is clearly defined, and risks are
acceptable; it is prohibited where integrity/safety failures or fabricated evidence exist.

---

## 8. Remediation (§§46–50)

Structured correction of deficiencies: address **root causes, not symptoms** (§46.3). Flow:
plan → corrective action → validation → closure. Corrective-action categories (§48.3): correction,
preventive action, process improvement, governance improvement. **Validation after remediation
(§49)** re-executes applicable gates — completing an action is not proof it worked. Closure (§50)
requires completed actions + validation + documentation + recorded approval.

---

## 9. Audit framework (§§51–55)

Independent, objective, evidence-based, repeatable, traceable. Categories: reviewer audits, gate
audits, decision audits, system audits. Lifecycle: Planning → Execution → Evidence Collection →
Analysis → Reporting → Remediation → Closure.

---

## 10. Release readiness & certification (§§56–59, 81–88)

**Release readiness is a higher bar than approval (§56.1):** an artifact can pass quality and still
fail release readiness. Readiness domains (§87.2), all must pass: Quality · Governance ·
Documentation · Audit · Remediation · Certification → outcome **Ready / Conditionally Ready /
Not Ready**.

**Certification levels (§59, §83):** 1 Development · 2 Review · 3 Production · 4 Governance
Certified · 5 Repository Certified. Progression requires documented evidence; levels may be
downgraded when requirements lapse (§83.4).

---

## 11. Metrics, reliability & monitoring (§§61–72, 95)

Metric categories: integrity, accuracy, alignment, educational quality, governance, user intent,
release. Reviewer reliability is tracked (consistency, reproducibility, calibration). Statistical
monitoring (§72): mean, median, variance, standard deviation, trend slope, failure frequency.
Longitudinal monitoring (§95) tracks approval/rejection/remediation/audit/certification/recovery
trends.

---

## 12. Escalation & recovery (§§73–80, 90–91)

Escalation levels (§74): Informational · Operational · Governance · Executive · Critical.
**Recovery workflow (§§77, 91):** Detection → Classification → Investigation → Containment →
Remediation → Validation → Approval → Closure. Maturity model (§79): Initial → Managed → Defined →
Measured → Optimized. Continuous improvement cycle (§80): Plan → Implement → Measure → Analyze →
Improve → Repeat.

---

## 13. Anti-patterns (§89) & failure conditions (§90)

Actively guard against: **Approval Without Evidence · Metric Worship · Documentation Theater ·
Audit Evasion · Gate Shopping.** Critical failures (§90.2) include fabricated evidence/audits/
certifications, undocumented/falsified approvals, unresolved critical safety risks, and
bypassed gates/audits.

---

## 14. Traceability & decision records (§§92–94)

Every significant decision is reconstructable. **Decision record (required fields, §93.3):**

```yaml
decision_id:
artifact_id:
reviewer:
date:
decision:        # Approved | Conditionally Approved | Remediation Required | Rejected
evidence:
rationale:
```

Recommended (§93.4): `score_summary, risk_summary, audit_reference, remediation_reference`.
The **Repository Quality Ledger (§94)** records approvals, rejections, remediations, audits,
certifications, recoveries; entries are immutable once finalized.

---

## 15. Repository Invariants (§96) — enforced by `tools/sync_check.py`

1. Integrity precedes approval.
2. Evidence precedes certification.
3. Validation precedes release.
4. Audits remain independent.
5. Critical failures block approval.
6. Repository history remains traceable.
7. Quality decisions remain auditable.
8. Certification requires evidence.

---

## 16. Compatibility & maintenance (§§97–98)

Support future skills, governance, audit, certification, and automation systems through an
extensible, modular architecture. Review when governance, audit, certification, or architecture
changes occur; maintain version control and audit history.
