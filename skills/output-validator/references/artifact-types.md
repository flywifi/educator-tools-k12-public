# artifact-types.md
## Artifacts produced by output-validator

This skill validates; it does not author classroom content. Outputs are governance records (end with the
metadata block + `human_review_required: true`; placeholders only).

### Artifact validation report
- **Purpose:** pass/fail verdict for a governed JSON artifact.
- **Required elements:** `status` (pass|fail), `schema_status`, `schema_errors`, `rule_failures`
  (each with `rule`, `severity`, `guidance`), `human_review_required: true`.
- **Validation:** matches `tools/validate_outputs.py`; never edits the artifact; routes fixes onward.

### Document structural report
- **Purpose:** will this produced `.docx/.pptx/.xlsx/.pdf/.odt/.ods/.odp` open?
- **Required elements:** `kind`, `valid`, `findings` (each `severity`, `code`, `detail`, `spec`,
  `guidance`), and the honest note that structural validity ≠ openability / deep conformance.
- **Validation:** matches `tools/validate_document.py` (stdlib); cites the format authority per finding.

### Promoted regression case
- **Purpose:** a failing artifact captured as a future eval (`--promote`), so the defect can't recur.
