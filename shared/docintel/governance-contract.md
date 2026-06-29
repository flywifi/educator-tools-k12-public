# Governance Contract (canonical)

Governance is **continuous, not a final review** (Principle 2; V02 §S07; V03 §S06). Every object
carries provenance + confidence; every stage appends lineage; every fact keeps its evidence. This
contract is the bridge between docintel and the existing TOS governance: `protocols/metadata-schema.md`
(the artifact metadata block) and `protocols/quality-gates.md` (the 9-dimension gates). Implemented
in `governance.py`.

## The three governance records

### 1. Provenance — *where did this come from?*
Attached to every Block / Table / cell:
`{source_id, parser, parser_version, extraction_method, page_number, bbox, timestamp}`.
`extraction_method ∈ {native, ocr, heuristic, manual}`. Provenance Coverage (G-001) = % of objects
that have it; the target is 100%.

### 2. Lineage — *what happened to it?*
An **append-only** ordered list of events on the document, one per stage that touches it:
`{event_id, stage, operation, tool, tool_version, timestamp, inputs[], outputs[]}`.
Lineage lets an auditor reconstruct the full processing history (G-002, G-005). Stages never rewrite
prior events; corrections append new ones.

### 3. Confidence — *how sure are we?*
`{value: 0–1, method, level ∈ {text, page, document}}` at the granularity it was produced. Confidence
is **explainable** (the `method` says how it was derived) and **propagates** — a paragraph's
confidence is bounded by its spans; a document's by its pages. Low confidence is surfaced, not hidden.

### Evidence — *prove it.*
Any extracted fact in a knowledge artifact keeps an `evidence` back-reference
`{page, bbox, char_range?}` to the source location. Evidence Coverage (G-003) = % of facts that can be
traced back. Evidence references must survive transformations (they are never discarded — V01 §S01).

## Tie-in to the TOS metadata block
When docintel emits an artifact, the metadata block (`protocols/metadata-schema.md`) is populated:
- `provenance` summary + `audit_reference` ← the lineage record;
- `score_summary` ← the validation metrics below + `quality-review`;
- `confidence` rolls up to the document level;
- `human_review_required: true` **always** (decision support, not a final determination);
- no real student data / PII (Integrity + Safety automatic-fail dimensions of the gates).

## Retrieval state — visibility ≠ extraction
Seeing a file is not the same as recovering its content. Every processed document carries a
**retrieval-state** on a four-step ladder (in `diagnostics.retrieval_state`, surfaced in the
artifact's governance block), so a consumer never mistakes a shallow hit for real content:
- `referenced` — only cited/linked; nothing recovered.
- `metadata_only` — lightweight facts seen (e.g. an image's format/dimensions, or an image-only page
  with no OCR engine installed) but **no content**.
- `content_ingested` — real content (text and/or a table) was recovered.
- `local_artifact_saved` — bytes/an exported artifact were saved for downstream use (a downstream
  state; the read pipeline reports up to `content_ingested`).

This pairs with the capability-gap reporting: an image with no OCR engine is `metadata_only` + an
`ocr` gap — **never** silently upgraded to "recovered." (Pattern adapted from an artifact-extractor's
evidence ladder; computed by `orchestration.retrieval_state`.)

## Governance invariants
1. No object without provenance + confidence reaches an artifact (G-001, G-004 = 100% target).
2. Lineage is append-only and complete — every stage appends exactly one event.
3. Evidence references survive every transformation (Principle 3).
4. Governance precedes performance and convenience in every conflict (Stakeholder hierarchy, V01 §S02).
5. Nothing is "certified" until it passes `quality-gates.md` (QG invariant: *Certification requires evidence*).
