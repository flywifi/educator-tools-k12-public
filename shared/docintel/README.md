# docintel — Document Intelligence engine (canonical)

**Source of truth** for the TOS-native Document Intelligence Platform: documents in →
**governed knowledge assets** out. This engine is consumed by the `document-intelligence`
skill and (over time) by `standards-updater` / `parse_fl_standards` so the ecosystem reads
the Florida corpus with structure, tables, and provenance instead of crude text scraping.

> Skeleton status: the **interfaces and the governed happy-path run end to end today**;
> advanced recovery (OCR, deep table/layout intelligence) is staged behind capability flags
> and filled in per the build sequence below. Nothing here fabricates content — unrecovered
> regions are reported with low/zero confidence, never invented.

## The five principles (Volume 01 §S01)
1. **Knowledge-First** — documents are inputs; governed knowledge assets are the product.
2. **Governance-First** — provenance, lineage, confidence, evidence travel with every object.
3. **Evidence-First** — every extracted fact is traceable to a source location.
4. **Parser-Independence** — no parser/OCR engine is a system dependency; all are swappable.
5. **Artifact-Centric** — artifacts are durable products; parsers are implementation details.

## Pipeline (Volume 02 §S02)
```
Ingestion → Recovery (text/OCR) → Structure (reading-order/layout/tables)
          → Governance → Knowledge Construction → Artifact Generation → Consumer Delivery
```
Governance metadata must survive every transition; raw extraction never bypasses governance;
artifacts are the only consumer-facing outputs.

## Frameworks in this engine
| File | Framework | Maps to |
|---|---|---|
| `udom.md` + `udom.schema.json` | **UDOM** — Unified Document Object Model | V02 §S05/§S06 (structure, tables) |
| `parser-orchestration.md` | **Parser Orchestration** — swappable parser plugins behind one contract | V02 §S03/§S04 |
| `table-intelligence.md` | **Table Intelligence** — swappable table engines (detect/reconstruct/normalize/confidence) | V02 §S06 |
| `ocr-architecture.md` | **OCR & Images** — stdlib image analysis + swappable OCR engines (targeted, confidence-aware) | V02 §S04 |
| `google-workspace.md` | **Google Workspace** — Docs API JSON + Docs/Sheets/Slides exports (odt/csv/xlsx/pptx) | V02 §S02 (ingestion) |
| `governance-contract.md` | **Governance** — provenance/lineage/confidence/evidence | V02 §S07; `protocols/metadata-schema.md`, `protocols/quality-gates.md` |
| `artifact-framework.md` | **Artifacts** — governed knowledge + consumer artifacts, readiness levels | V02 §S08/§S09 |
| `validation-framework.md` | **Validation** — accuracy/governance/reusability metrics + acceptance | V01 §S04; V02 §S10 |

## Python package (runnable skeleton)
`udom.py` · `governance.py` · `orchestration.py` · `tables.py` · `ocr.py` · `images.py` ·
`change.py` · `artifact.py` · `validation.py` · `parsers/` (`plaintext_parser.py`, `pymupdf_parser.py`,
`pdf_table_parser.py`, `image_parser.py`, `tesseract_ocr.py`, `workspace_parsers.py`,
`calendar_parser.py` (.ics), `email_parser.py` (.eml)). Run it via `tools/docintel_run.py`.
Stdlib-only by default; uses PyMuPDF/pdfplumber/pytesseract/Docling/etc. **if installed**
(parser/table/OCR-engine independence).

## Build sequence (Volume 01 §S07 — dependency order)
Governance → UDOM → Artifacts → Parser Evaluation → Parser Orchestration → TOS Integration →
Validation → Optimization. Build foundations before optimization; validate before scaling.

## Repository research tiers (Volume 01 §S08 — reuse, don't reinvent)
- **Tier 1:** Docling, PyMuPDF, Marker.
- **Tier 2:** Surya, Camelot, pdfplumber, PDFium.
- **Tier 3:** LayoutParser, GROBID, OCRmyPDF.

Each is wrapped behind the `Parser` contract; harvest concepts/components with the least
invasive strategy, and record reuse/fork/replace decisions (V01 §S08).

## Governance & safety
Every artifact ends with the metadata block from `protocols/metadata-schema.md` and carries
`human_review_required: true`. No real student/PII data — placeholders only. Outputs are
decision support, gated by `quality-review` against `protocols/quality-gates.md`.
