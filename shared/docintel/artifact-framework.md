# Artifact Framework (canonical)

Artifacts are the **durable products** of the platform (Principle 5; V02 §S08/§S09). Consumers read
artifacts, not source documents and not parser output. Implemented in `artifact.py`.

## Two artifact classes
- **Knowledge Artifact** — the governed, normalized representation of the document's content: the UDOM
  plus derived structure (sections, tables, reading order) with full governance. Machine-first.
- **Consumer Artifact** — a projection shaped for a specific consumer (a TOS skill, a human reviewer,
  an analytics job). Derived from the knowledge artifact; never re-derives from source.

Both are parser-independent and carry the metadata block from `protocols/metadata-schema.md`.

## Required elements (every artifact)
1. `artifact_id`, `artifact_type`, `schema_version`.
2. Content payload (UDOM for knowledge artifacts; a defined projection for consumer artifacts).
3. **Governance**: provenance summary, lineage reference, document-level confidence, evidence map.
4. The TOS **metadata block** with `human_review_required: true`.
5. Readiness level (below).

## Artifact contract stability
A consumer that reads `schema_version` N keeps working when parsers change underneath. Parser swaps
are **never** allowed to change the artifact contract — that is the core acceptance guarantee
(V01 §S04: parser replaceability). Breaking the contract is a **controlled change** (below).

## Change control (V03_S07)
Any modification to an approved artifact contract, the UDOM schema (`udom.schema.json`), or a
governed artifact is **classified, evaluated, approved with evidence, and traceable** — *controlled
change preserves integrity; uncontrolled change creates uncertainty*. Implemented in `change.py`
(`ChangeRecord`, `build_change_record`, `validate_change`).

- **Classify** (`ChangeClass`): `administrative` · `planning` · `governance` · `acceptance`.
  This supersedes the older Clarification/Enhancement/Scope-Expansion shorthand (V01 §S09).
- **Evaluate** every change for impact on all four dimensions before adoption:
  `scope` · `architecture` · `acceptance` · `governance` (V03_S07 §6).
- **Approve with evidence** — an approval carries a description, impact assessment, decision, and
  **approval evidence** + at least one approval reference (§7); recorded in the Quality Ledger.
- **Trace** — every change keeps an id, status, rationale, and approval references (§8); artifacts
  are immutable, so corrections create a **new** record, never an in-place edit
  (`protocols/metadata-schema.md` §3).
- **Constraints** (§9, enforced by `validate_change`): a change may **not** bypass governance, bypass
  review (no jump from proposed → approved), reduce traceability, or reduce planning integrity.

## Readiness levels (V01 §S06 — Definition of Done)
`Draft → Reviewed → Validated → Production-Ready → Reference-Standard`. An artifact is only
`Validated`+ after it passes `validation-framework.md` thresholds **and** `quality-review`. Readiness
is recorded in the metadata block and the Quality Ledger.

## Artifact types registered for the `document-intelligence` skill
(kept in sync with `shared/ontology/artifact-types.json` and the skill's `references/artifact-types.md`)
- `processed-document-record` — ingestion record: source identity, media type, hashes, status.
- `udom-document` — the Unified Document Object Model instance (the knowledge artifact core).
- `recovery-report` — what each parser/OCR recovered, with confidence + diagnostics.
- `structure-map` — sections, headings, reading order, table inventory.
- `governance-record` — provenance + lineage + confidence + evidence for the document.
- `knowledge-artifact` — the governed, consumer-ready knowledge asset.
- `consumer-artifact` — a consumer-specific projection (e.g., standards-extraction for the FL pipeline).
