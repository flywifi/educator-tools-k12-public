# Example evaluation — a Grade 3 fractions lesson

Worked `quality-review` output for the gold lesson in
`skills/lesson-planner/examples/grade3-fractions-lesson.md`. Shows the expected shape of a decision
record: per-dimension scores with **evidence**, the script-computed composite, and the verdict.

---

## Per-dimension scores (gate order)

| # | Dimension | Score | Evidence |
|---|---|---|---|
| 1 | Integrity | 5 | Assumptions section discloses the 45-min/whole-class assumption; no fabricated content. |
| 2 | Safety | 5 | Uses "Student A/B"; no real PII; human-review flag present. |
| 3 | Governance | 4 | Metadata block complete; standard cited with framework + version. |
| 4 | Accuracy | 4 | `CCSS.MATH.CONTENT.3.NF.A.1` is real, grade-3, correctly coded; statements correct. |
| 5 | Alignment | 4 | Objective (partition wholes into b equal parts) ↔ exit ticket item match. |
| 6 | Educational Quality | 4 | I-do/we-do/you-do progression; concrete→representational; tiered tasks; CFU present. |
| 7 | Accessibility | 4 | Grade-3 reading level; visual fraction models; sentence frames for ELs. |
| 8 | Professional Quality | 4 | Clean, consistent template; clear sections. |
| 9 | User Intent | 5 | Delivered exactly the requested artifact: a 3rd-grade fractions lesson. |

## Composite (script-computed)
```
$ python3 scripts/score.py '{"integrity":5,"safety":5,"governance":4,"accuracy":4,"alignment":4,"educational_quality":4,"accessibility":4,"professional_quality":4,"user_intent":5}'
composite: 4.34   decision: Approved   critical_override: false
```

## Decision record (emitted)
```yaml
decision_id: qr-2026-0001
artifact_id: lp-grade3-fractions-001
reviewer: quality-review
date: 2026-06-20
decision: Approved
evidence: see per-dimension table above (each score quotes the artifact)
rationale: composite 4.34 ≥ 4.0; no critical-failure conditions present
score_summary: I5 Sa5 G4 Ac4 Al4 EQ4 Ax4 PQ4 UI5 -> composite 4.34
human_review_required: true
```

---

## Contrast: what a Rejected verdict looks like
If the same lesson had cited a **made-up standard** (`CCSS.MATH.CONTENT.3.NF.A.9` — does not exist),
Accuracy → 0, which is an automatic **Rejected** regardless of the 3.04 composite:
```
$ python3 scripts/score.py '{"integrity":3,"safety":5,"governance":4,"accuracy":0,"alignment":4,"educational_quality":4,"accessibility":4,"professional_quality":4,"user_intent":5}'
composite: 3.04   decision: Rejected   critical_override: true
```
Remediation: replace the fabricated code with a verified one
(`protocols/standards-verification.md`) and re-evaluate.
