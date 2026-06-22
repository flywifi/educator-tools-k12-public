# Parser Orchestration Framework (canonical)

Makes parsers, OCR engines, and structure models **swappable implementation details** behind one
stable contract (Principle 4). No consumer or artifact ever names a parser. Implemented in
`orchestration.py` + `parsers/`.

## The Parser contract
Every parser (a wrapper around PyMuPDF, Docling, Marker, Surya, Camelot, …) implements:

```
class Parser:
    name: str
    version: str
    capabilities: set[str]      # subset of CAPABILITIES below
    def available(self) -> bool # are this parser's deps importable?
    def supports(self, media_type: str) -> bool
    def parse(self, data: bytes, media_type: str, source) -> RecoveryResult
```

`RecoveryResult` = `{blocks[], diagnostics, confidence, extraction_method}` in UDOM terms.

### Capabilities vocabulary
`text` · `ocr` · `tables` · `layout` · `reading_order` · `figures` · `formulas`. A parser declares
what it can do; the orchestrator selects by **required capabilities ∩ availability**, not by name.

## Selection & fallback
1. Filter the registry to parsers where `available()` and `supports(media_type)`.
2. Rank by how many **required** capabilities they cover, then by registry priority.
3. If no parser covers a required capability (e.g. `ocr` with no OCR engine installed), the stage
   **reports the gap** (`capability_unavailable`) and continues with what was recovered — it never
   fabricates the missing content, and it never bypasses governance.

This is the same "detect → degrade gracefully → report, don't fake" stance as
`tools/standards_refresh.py` (e.g., a scanned-PDF page with no OCR engine is reported, not guessed).

## Reference parsers shipped in the skeleton
| Parser | Deps | Capabilities | Notes |
|---|---|---|---|
| `PlainTextParser` | none (stdlib) | `text`, `reading_order` | `.txt`, `.md`, and `.docx` (via `zipfile`/XML). Always available. |
| `PyMuPDFParser` | `pymupdf` (optional) | `text`, `layout`, `reading_order`, `figures` | PDFs; registered only when `fitz` imports. |

## Parser tiers to wrap next (Volume 01 §S08)
- **Tier 1:** Docling (layout+reading order+markdown), PyMuPDF (fast native text), Marker (PDF→md).
- **Tier 2:** Surya (OCR+layout), Camelot / pdfplumber (tables), PDFium (rendering).
- **Tier 3:** LayoutParser (DL layout), GROBID (scholarly), OCRmyPDF (OCR pre-pass).

Each is added as a new `Parser` subclass in `parsers/` and registered — **no other code changes**,
which is the whole point of the contract (parser replaceability is an acceptance metric, V01 §S04).

## Execution models (V02 §S04)
`single` (one parser) · `parallel` (run several, reconcile by confidence) · `targeted` (OCR only the
pages/regions native extraction missed). The skeleton implements `single`; `parallel`/`targeted`
reconciliation are staged behind `RecoveryResult.confidence` and raise a clear error until filled in.
