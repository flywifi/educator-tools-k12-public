# metadata-schema.md
## Metadata Schema Protocol
Version: 1.0 (reconstructed from the Quality Gates references; approved)
Derived from: QG §3.3 (Quality Gates depend on metadata), §39 & §93 (decision records),
§92 (traceability), §12.2 (metadata compliance).

> **Status note.** Reconstructed from the Quality Gates references (§2.1, §39, §93) and approved for
> use (v1.0). Amend if an original surfaces.

---

## 1. Purpose

Every artifact the ecosystem produces carries a **metadata block** so that decisions are
traceable, auditable, and reconstructable (QG Invariants §96: "history remains traceable",
"quality decisions remain auditable"). Metadata is an input to Quality Gates, not an afterthought.

## 2. The artifact metadata block

Appended as a trailer (or front-matter) on every generated artifact. Two parts: the **quality
decision record** (from QG §93) and the **education trailer** (TOS-specific).

```yaml
# --- Quality decision record (QG §93) ---
decision_id:            # unique id for this evaluation
artifact_id:            # unique id for the artifact
reviewer:               # "quality-review" skill, or named human reviewer
date:                   # ISO-8601
decision:               # Approved | Conditionally Approved | Remediation Required | Rejected
evidence:               # what was checked; links/excerpts supporting the decision
rationale:              # why this decision
score_summary:          # per-dimension 0–5 scores + weighted composite (optional but recommended)
risk_summary:           # notable risks (optional)
audit_reference:        # pointer to ledger entry (optional)
remediation_reference:  # pointer to remediation record, if any (optional)

# --- Education trailer (TOS) ---
artifact_type:          # e.g., lesson-plan, rubric, slide-deck
persona:                # requesting persona (see shared/personas/personas.md)
grade_band:             # e.g., K-2, 3-5, 6-8, 9-12
subject:                # e.g., Math, ELA, Science
standards_set:          # framework + version, e.g., "CCSS-Math 2010"
standards_cited:        # list of standard codes referenced
differentiation:        # UDL / tiering / EL / IEP supports applied
human_review_required:  # true (always — artifacts are decision support, not final determinations)
assumptions:            # list of assumptions made (see assumptions-protocol.md)
```

## 3. Rules

- **`human_review_required` is always `true`.** Every artifact is decision support; a professional
  must validate it (Charter V3 §12; SECURITY_AND_SAFETY.md). The drift guard checks this flag.
- **No real student data.** Any student reference uses placeholders ("Student A"). PII in metadata
  is an Integrity/Safety automatic failure (QG §37; SECURITY_AND_SAFETY.md).
- **Standards must be cited with framework + version** so they are verifiable
  (standards-verification.md).
- **Immutability.** Once an artifact is finalized, its decision record is recorded in the Quality
  Ledger (QG §94) and is not edited; corrections create a new record.

## 4. Validation

`tools/sync_check.py` asserts that each `SKILL.md` references this schema and emits the
`human-review-required` flag. Field-level validation of emitted artifacts is added with the
`quality-review` skill in Phase A.
