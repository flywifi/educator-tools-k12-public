---
name: document-intelligence
description: "Transform documents (PDF, DOCX, HTML, TXT, scans) into GOVERNED, reusable knowledge assets — a parser-independent, artifact-centric document-understanding pipeline (ingestion → recovery/OCR → structure/tables/reading-order → governance → knowledge → artifact). Use this whenever someone needs to read, parse, extract, OCR, or structure a document WITH provenance/lineage/confidence and human-reviewable artifacts — e.g. 'read this PDF properly', 'extract the tables', 'ingest these standards docs into structured data', 'OCR this scan', 'build a knowledge artifact from this report', or 'improve how we parse the Florida corpus'. Produces: processed-document-record, udom-document, recovery-report, structure-map, governance-record, knowledge-artifact, consumer-artifact. It emits the metadata block (protocols/metadata-schema.md) with human_review_required: true and is gated by quality-review. Do NOT use it to author NEW instructional content (use lesson-planner/assessment-designer/etc.), to crawl or fetch documents from the web (that is standards-updater), or as a search engine / vector database. It never fabricates content: unrecovered regions are reported with low confidence, never invented."
---

# document-intelligence

Turns documents into **governed knowledge assets** — structured, provenance-tracked, machine- and
human-consumable artifacts — so the rest of the ecosystem consumes *artifacts*, not raw source files.
It is **parser-independent** (parsers/OCR engines are swappable plugins) and **artifact-centric**
(artifacts are the durable product). Canonical engine: `shared/docintel/` (the source of truth).

**Five principles** (do not violate): Knowledge-First · Governance-First · Evidence-First ·
Parser-Independence · Artifact-Centric. See `references/docintel-architecture.md`.

> **Boundaries (read first).** This skill *reads and structures* documents you already have; it does
> **not** fetch them from the web — discovery/crawling is `standards-updater`. It **never fabricates**
> content: anything that cannot be recovered (e.g., a scan with no OCR engine installed) is reported
> with low/zero confidence and a capability-gap note, never guessed. Outputs are decision support.

## What this skill does
Runs the document-processing pipeline and emits governed artifacts:
```
Ingestion → Recovery (text/OCR) → Structure (reading-order/layout/tables)
          → Governance → Knowledge Construction → Artifact Generation → Consumer Delivery
```
Governance metadata (provenance, lineage, confidence, evidence) survives every stage; raw extraction
never bypasses governance; artifacts are the only consumer-facing outputs.

## How it works — the unified pipeline
Follow the shared pipeline in `references/method.md`. The domain work runs through the docintel
engine (`shared/docintel/`):
```bash
python3 tools/docintel_run.py --check                      # list parsers + availability (offline)
python3 tools/docintel_run.py <file> --out artifact.json --udom udom.json
```
- **Recovery** — the orchestrator selects a parser by *capability*, not by name
  (`shared/docintel/parser-orchestration.md`). Stdlib-only by default (.txt/.md/.html/.docx); PDF
  support activates automatically when PyMuPDF is installed; add Docling/Surya/Camelot/etc. as new
  plugins with **no consumer changes**.
- **Structure** — reading order, headings, and tables into the UDOM
  (`shared/docintel/udom.md` + `udom.schema.json`).
- **Governance** — provenance/lineage/confidence/evidence on every object
  (`shared/docintel/governance-contract.md`); ties to `protocols/metadata-schema.md`.
- **Validation** — accuracy/governance/reusability metrics (`shared/docintel/validation-framework.md`);
  staged metrics are reported honestly as `staged`, never faked.
- **Quality** — self-check against `references/quality-gates.md`, then hand to `quality-review`.

## Experimental features & feature flags
Experimental pipeline stages default **OFF** and are opt-in via `PipelineConfig.flags`
(see `shared/docintel/orchestration.py`). This keeps new/experimental recovery modes isolated until
validated — flip a flag per run/environment without affecting the default governed path. Required
recovery capabilities are likewise configurable via `PipelineConfig.required_capabilities`.

## Artifacts
See `references/artifact-types.md`: `processed-document-record`, `udom-document`, `recovery-report`,
`structure-map`, `governance-record`, `knowledge-artifact`, `consumer-artifact`.

## Output: always emit the metadata block
Every artifact ends with the metadata block from `protocols/metadata-schema.md`, including the
validation `score_summary` and `human_review_required: true` — outputs are decision support, not
final professional or legal determinations, and nothing is "certified" until it passes the Quality
Gates via `quality-review`. Use placeholders only; never real student data or PII.
