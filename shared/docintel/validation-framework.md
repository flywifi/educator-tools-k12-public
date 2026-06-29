# Validation Framework (canonical)

Capabilities are only valuable if they can be measured **objectively, repeatably, and comparably**
(V01 §S04). This framework defines the metrics, how the skeleton computes them, and the acceptance
thresholds. Implemented in `validation.py`; final acceptance is gated by `quality-review`.

## Metric families (V01 §S04)
### Accuracy (A)
| ID | Metric | Skeleton computes? |
|---|---|---|
| A-001 | Text Recovery Accuracy | partial (recovered chars vs. recoverable; needs a reference set) |
| A-002 | Reading-Order Accuracy | yes (every block ordered exactly once per page) |
| A-003 | Table Recovery Accuracy | staged (needs Tier-2 table parser + reference tables) |
| A-004 | Metadata Recovery Accuracy | yes (presence/shape of document properties) |
| A-005 | Structural Recovery Accuracy | partial (heading/section detection rate) |

### Governance (G)
| ID | Metric | Skeleton computes? |
|---|---|---|
| G-001 | Provenance Coverage | yes (% objects with provenance) |
| G-002 | Lineage Coverage | yes (% stages with a lineage event) |
| G-003 | Evidence Coverage | yes (% artifact facts with an evidence ref) |
| G-004 | Confidence Coverage | yes (% objects with confidence) |
| G-005 | Audit Reconstruction | yes (lineage is complete + append-only) |

### Reusability (R)
| ID | Metric | Skeleton computes? |
|---|---|---|
| R-001 | Artifact Completeness | yes (required elements present) |
| R-002 | Artifact Consistency | yes (equivalent input → equivalent output; hash-stable) |
| R-003 | Consumer Independence | yes (artifact resolvable without the source file) |
| R-004 | Reprocessing Reduction | staged (cross-run cache hit rate) |
| R-005 | Knowledge Preservation | staged (longitudinal) |

Interoperability and Maintainability (incl. **parser replaceability**) are asserted structurally by
the `Parser` contract + artifact-contract stability, and by the drift guard.

## Acceptance thresholds (initial — tune per V02 §S10)
- Governance: **G-001, G-004 = 100%** (no ungoverned object reaches an artifact); G-002/G-005 = 100%.
- Reading order (A-002): 100% of blocks ordered exactly once per page.
- Artifact completeness (R-001): 100% of required elements present.
- Accuracy A-001/A-003/A-005: measured against a labeled reference set (added during Parser Evaluation);
  must **outperform direct AI ingestion** baseline (Objective 1, V01 §S01) before `Production-Ready`.

## How validation runs
`validation.validate(udom, artifact) -> report`. Computable metrics return values; staged metrics
return `null` with a `status: "staged"` note (honest, not fabricated). The report feeds the
`score_summary` in the metadata block; `quality-review` makes the final Approved/Remediation decision
against `protocols/quality-gates.md`. **Nothing is "Final" until it passes the Quality Gates.**
