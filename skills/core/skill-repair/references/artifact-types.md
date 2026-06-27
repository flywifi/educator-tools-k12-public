# artifact-types.md
## Artifacts produced by skill-repair

Governance records only (end with the metadata block + `human_review_required: true`; placeholders only).

### Proposed-changes summary (pre-approval)
- **Purpose:** the plain-language patch proposal a human approves.
- **Required elements:** one-paragraph overview; intended edits tagged mechanical|judgment; intentionally
  unchanged list; validation plan. Template: `references/approval-summary-template.md`.

### Applied-repair record (post-approval)
- **Purpose:** what was actually changed after approval.
- **Required elements:** checks passed / checks not run / remaining watch items; finalization status;
  archive-updated flag. Mechanical fixes only auto-apply; judgment items remain listed for the human.

### Validation results
- **Purpose:** evidence the repair held — from `references/validation-checklist.md` (sync_check, health
  re-scan, output-validator on samples). A patch is never "complete" if risky parts went untested.
