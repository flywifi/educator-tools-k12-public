# artifact-types.md
## Artifacts produced by document-intelligence

All artifacts are parser-independent, carry full governance (provenance/lineage/confidence/evidence),
and end with the metadata block from `protocols/metadata-schema.md` (`human_review_required: true`).
Specs live in the canonical engine `shared/docintel/` (kept in sync with
`shared/ontology/artifact-types.json`).

### processed-document-record
- Purpose: the ingestion record for a source document (identity + status).
- Required elements: `document_id`, source `{filename, media_type, sha256, byte_length}`, ingestion
  lineage event, status.
- Standards: n/a (infrastructure artifact).
- Validation: source hashed; ingestion lineage present (`shared/docintel/governance-contract.md`).

### udom-document
- Purpose: the Unified Document Object Model instance — the structured, parser-independent core.
- Required elements: pages → blocks (type, bbox, text/table) with provenance + confidence; explicit
  per-page reading order; document-level confidence; append-only lineage.
- Standards: conforms to `shared/docintel/udom.schema.json`.
- Validation: schema conformance; every block governed; reading order is a permutation of block ids
  (A-002); see `shared/docintel/validation-framework.md`.

### recovery-report
- Purpose: what each parser/OCR engine recovered, with confidence and **capability gaps**.
- Required elements: parser name/version, extraction method, per-page/block counts, confidence,
  `capability_gaps` (e.g., `ocr` unavailable), diagnostics.
- Validation: gaps reported honestly; nothing fabricated for unrecovered regions.

### structure-map
- Purpose: the document's sections, headings, reading order, and table inventory.
- Required elements: heading hierarchy/levels, per-page reading order, table list with shape.
- Validation: reading-order and structure metrics (A-002/A-005).

### governance-record
- Purpose: the consolidated provenance + lineage + confidence + evidence for a document.
- Required elements: provenance per object, append-only lineage for every stage, confidence rollup,
  evidence map for any derived facts.
- Validation: G-001/G-002/G-004/G-005 coverage (provenance, lineage, confidence, audit).

### knowledge-artifact
- Purpose: the governed, normalized, consumer-ready knowledge asset (UDOM + governance + metadata).
- Required elements: `artifact_id`, `schema_version`, payload (UDOM), governance block, metadata
  block, readiness level.
- Validation: artifact completeness (R-001); not "certified" until it passes `quality-review`.

### consumer-artifact
- Purpose: a consumer-specific projection (e.g., a standards-extraction view for the FL pipeline).
- Required elements: `derived_from` (the knowledge artifact id), the projection payload, inherited
  governance, metadata block.
- Standards: when projecting standards data, cite framework + code per
  `protocols/standards-verification.md`; never invent a code.
- Validation: derivable without the source file (R-003 consumer independence).
