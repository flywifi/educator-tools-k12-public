# docintel-architecture.md
## Architecture overview + map to the source design

This skill implements a **TOS-native Document Intelligence Platform**: documents in → governed
knowledge assets out. The canonical engine and full specs live in `shared/docintel/`; this file is
the skill-side map and the build status.

## The five principles
1. **Knowledge-First** — documents are inputs; governed knowledge assets are the product.
2. **Governance-First** — provenance, lineage, confidence, evidence travel with every object.
3. **Evidence-First** — every extracted fact traces to a source location.
4. **Parser-Independence** — no parser/OCR engine is a dependency; all are swappable plugins.
5. **Artifact-Centric** — artifacts are durable products; parsers are implementation details.

## Frameworks (canonical files)
| Framework | Canonical file | Code |
|---|---|---|
| UDOM (object model) | `shared/docintel/udom.md` + `udom.schema.json` | `shared/docintel/udom.py` |
| Parser Orchestration | `shared/docintel/parser-orchestration.md` | `shared/docintel/orchestration.py`, `parsers/` |
| Table Intelligence | `shared/docintel/table-intelligence.md` | `shared/docintel/tables.py`, `parsers/pdf_table_parser.py` |
| OCR & Images | `shared/docintel/ocr-architecture.md` | `shared/docintel/ocr.py`, `images.py`, `parsers/image_parser.py`, `parsers/tesseract_ocr.py` |
| Governance | `shared/docintel/governance-contract.md` | `shared/docintel/governance.py` |
| Artifacts | `shared/docintel/artifact-framework.md` | `shared/docintel/artifact.py` |
| Validation | `shared/docintel/validation-framework.md` | `shared/docintel/validation.py` |
| Change Control | `shared/docintel/artifact-framework.md` (Change control) | `shared/docintel/change.py` |

## How it maps to the source volumes
- **V01** (project definition, stakeholders, current-state, metrics, scope, deliverables,
  sequencing, repo research, handoff) → the principles, the `validation-framework.md` metrics
  (A/G/R), the build sequence below, and the parser tiers.
- **V02** (reference architecture, processing pipeline, parser orchestration, OCR, structure
  recovery, table intelligence, governance, artifacts, consumer interface, acceptance criteria) →
  the pipeline stages, `orchestration.py`, `udom.*`, `tables.py`, `ocr.py`/`images.py`,
  `governance-contract.md`, `artifact.py`.
- **V03** (implementation planning, work packages, dependencies, validation/readiness/governance,
  **change control (S07)**, risk, acceptance) → the build sequence, the drift-guard / quality-gate
  wiring, and the artifact **change-control** model (`change.py`; artifact-framework.md "Change control").

## Build sequence (dependency order — V01 S07)
Governance → UDOM → Artifacts → Parser Evaluation → Parser Orchestration → TOS Integration →
Validation → Optimization.

## Build status (skeleton)
- **Done (runs end to end):** ingestion, native text recovery (.txt/.md/.html/.docx; PDF via
  PyMuPDF when installed), **image ingestion + stdlib image analysis** (format/dimensions for
  png/jpeg/gif/bmp), **targeted OCR stage** (confidence-aware text via Tesseract when installed;
  honest `ocr` capability-gap when not — never fabricated), **table intelligence for docx/html/markdown**
  (rows/cols/headers/merged cells via colspan + gridSpan/vMerge, table/cell confidence + conflict
  handling), reading-order structure, governance stamping, knowledge normalization, knowledge-artifact
  generation, computable validation metrics (incl. A-003 table recovery), schema conformance, and
  artifact **change-control** records (classify → evaluate → approve-with-evidence → trace, V03_S07).
- **Staged (interfaces defined; fill in next):** **PDF OCR** (rasterize + OCR via PyMuPDF/pdf2image —
  reported via `StageNotImplemented`, never faked), additional OCR engines (Surya/OCRmyPDF), **PDF
  table recovery** (pdfplumber/Camelot — activates when installed), DL layout (Docling/LayoutParser/
  Marker), parallel multi-parser reconciliation, reference-set accuracy metrics (A-001/A-005),
  consumer-interface projections. Each plugs in behind the existing contracts with no consumer changes.

## Parser tiers to wrap (reuse, don't reinvent — V01 S08)
- **Tier 1:** Docling, PyMuPDF, Marker.
- **Tier 2:** Surya, Camelot, pdfplumber, PDFium.
- **Tier 3:** LayoutParser, GROBID, OCRmyPDF.

Optional dependencies are isolated; the engine is stdlib-only by default. Add a parser by subclassing
`Parser` in `shared/docintel/parsers/` and registering it — that is the whole integration surface.

## TOS integration
- Governance ties to `protocols/metadata-schema.md`; gates via `protocols/quality-gates.md` +
  `quality-review`; artifacts register in `shared/ontology/artifact-types.json`.
- First consumer: the Florida pipeline — re-implement `tools/parse_fl_standards.py` to consume
  `knowledge-artifact` / `consumer-artifact` output so the corpus is read with structure + tables +
  provenance instead of regex-on-XML.
