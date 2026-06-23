# method.md
## The Unified Production Pipeline
Canonical source. Synced into each skill's `references/method.md` (see `tools/sync_manifest.json`).
Do not edit per-skill copies — edit here and re-run `tools/sync_check.py`.

This merges the charter's 7-stage production model (Charter V3 §15 / V4) with the Quality Gates
governance lifecycle (QG §3.1). Every TOS skill follows it; only the domain specifics change.

---

## The pipeline

```
Request
 → 1. Routing
 → 2. Protocol Enforcement
 → 3. Generation
 → 4. Validation
 → 5. Quality Gates
 → 6. Approval / Certification
 → 7. Release  →  Final Artifact (+ metadata block)
```

### 1. Routing  *(owned by `teacher-core`)*
Classify the request: **persona × artifact type × subject × grade band** → the right capability
skill. See `ROUTING_MODEL.md`. If no spoke fits, `teacher-core` carries the pipeline itself using
the shared references.

### 2. Protocol Enforcement
Before generating, satisfy the governance protocols:
- **context** — resolve the teaching-context contract (`shared/context/`): state / district /
  school_type / program(s) / instructional_model / mandates / uploaded SOPs. Apply the school-type
  exception rule-set + authority precedence, carry it through every handoff (overrides logged), and
  default to traditional-public Florida when unstated. Context is resolved **first**.
- **assumptions** — log anything the request didn't specify (`protocols/assumptions-protocol.md`);
- **metadata** — initialize the artifact metadata block (`protocols/metadata-schema.md`);
- **standards-verification** — arm verification for any standards to be cited
  (`protocols/standards-verification.md`).

### 3. Generation  *(owned by the capability skill)*
The domain work, itself a mini-pipeline:
`Analysis → Standards Alignment → Differentiation → Generation`.
- **Analysis** — interpret intent, audience, constraints, and the **resolved context** (school type,
  instructional model, mandates, SOPs).
- **Standards Alignment** — select + cite standards (`shared/standards/`); **applicability follows
  context** (`shared/context/`): home-education / private-scholarship contexts make alignment advisory,
  not mandated, while public/charter/virtual keep B.E.S.T./NGSSS.
- **Differentiation** — apply UDL / tiering / EL / IEP supports (`shared/differentiation/`).
- **Generation** — produce the artifact from the domain template, **adapted to context**
  (`shared/context/adaptation.md`): instructional model, calendar, school-type overrides, and
  SOP-driven templates/policies.

### 4. Validation
Minimum-correctness check before the gates (QG §7.3): is the requested deliverable present, complete,
and internally consistent?

### 5. Quality Gates  *(owned by `quality-review`)*
Score the 9 dimensions in gate order, apply thresholds + critical-failure overrides
(`shared/quality/quality-gates.md`; full spec `protocols/quality-gates.md`). Outcome: Approved /
Conditionally Approved / Remediation Required / Rejected. On failure → remediate
(`protocols/failure-recovery.md`) or resolve conflicts (`protocols/conflict-protocol.md`).

### 6. Approval / Certification
Record the decision (`protocols/metadata-schema.md` decision record); assign a certification level
where applicable (QG §59).

### 7. Release
Confirm release readiness (QG §87) and emit the **Final Artifact** with its completed metadata
block. Remember: every artifact is **decision support, not a final professional/legal
determination** — `human_review_required` is always true.

---

## Why these stages are distinct

Validation (4), Quality Gates (5), and Release (7) are deliberately separate: an artifact can be
*present* (passes validation), *good* (passes the gates), and still *not ready to ship* (fails
release readiness) — QG §56.1. Keeping them apart makes failures specific and auditable.
