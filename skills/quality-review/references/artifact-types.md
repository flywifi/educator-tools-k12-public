# artifact-types.md
## Artifacts produced by quality-review

`quality-review` does not create educational artifacts — it produces **evaluations** of them.

### Quality decision record (primary output)
- **Purpose:** the auditable verdict on one artifact.
- **Required elements:** per-dimension 0-5 scores *with quoted evidence*; composite; decision
  (Approved / Conditionally Approved / Remediation Required / Rejected); critical-failure flag;
  rationale; `human_review_required: true`. Schema: `protocols/metadata-schema.md`.
- **Computed by:** `scripts/score.py` (weights + thresholds + override).
- **Example:** `examples/example-evaluation.md`.

### Remediation list (when not Approved)
- **Purpose:** specific, actionable fixes per failed dimension.
- **Required elements:** for each gap — what's wrong (with evidence), why it matters (which gate),
  and the concrete change to make. Follows `protocols/failure-recovery.md` (never fabricate to pass)
  and `protocols/conflict-protocol.md` (authority hierarchy) where requirements conflict.

### Batch quality report (optional)
- **Purpose:** roll-up across several artifacts (e.g., a unit's lessons + assessments).
- **Required elements:** per-artifact decisions + aggregate pass rate; feeds the metrics in
  `QUALITY_MODEL.md` / Quality Ledger (QG §94).
