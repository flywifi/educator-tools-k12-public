# artifact-types.md
## Artifacts produced by skill-health

This skill governs the **system**, not classroom artifacts, so it produces governance records, not
lessons. All outputs end with the metadata block and `human_review_required: true`; placeholders only.

### Health report
- **Purpose:** a readiness snapshot of the whole ecosystem (skills + shared engines + routing).
- **Required elements:** `readiness_score` + `readiness_band` (`strong/usable_with_warnings/partial/
  not_ready`), per-skill issues, engine importability, routing problems, `operator_readiness_state`,
  `release_gate_recommendation`, `blocking_issues`, and `human_review_required: true`.
- **Validation:** matches `shared/health/health.py --scan`; bands follow the documented thresholds.

### Diagnosis
- **Purpose:** explain, in plain language, why something is failing, from the audit trail.
- **Required elements:** findings grouped by source (`quality_ledger`, `runtime_traces`) and category
  (validation / retrieval / error), connector failure-class counts, minority-report counts, and an honest
  note that runtime traces are ephemeral unless saved.
- **Validation:** never invents a cause; cites the ledger/trace evidence it read.

### Repair plan
- **Purpose:** a concrete, ordered plan the human edits or approves.
- **Required elements:** steps tagged by `severity` (blocking/warning/info) and `mechanical` vs
  `judgment`, each naming the file/area to change; the rule that **nothing high-stakes auto-applies** and
  that approval is followed by `tools/sync_check.py` + the Quality Gates.
- **Validation:** every blocking issue in the report has a corresponding repair step.
