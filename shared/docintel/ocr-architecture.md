# OCR & Image Handling (canonical) — V02_S04

*"OCR is a recovery capability used when information cannot be recovered through native extraction
alone."* Images and scanned PDFs get a dedicated, **replaceable** OCR stage that produces
**confidence-aware** text — and, critically, **reports a gap rather than fabricating text** when no
OCR engine is installed. Implemented in `ocr.py` + `images.py` + `parsers/image_parser.py` +
`parsers/tesseract_ocr.py`.

## Two halves: image analysis (stdlib) + text recovery (OCR)
- **Image analysis** — `images.py` reads format + pixel dimensions from the file header
  (PNG/JPEG/GIF/BMP) with **no dependencies**. `ImageParser` ingests an image as a `figure` block and
  records its properties. This always runs.
- **Text recovery (OCR)** — there is no stdlib OCR, so OCR engines activate only when their deps are
  installed. When OCR is needed but unavailable, the pipeline records
  `capability_gaps: ["ocr"]` and `ocr.status = "capability_unavailable"` — honest, never invented.

## The OCR stage (runs after Recovery, before Table Intelligence)
Pipeline order: `Ingestion → Recovery → OCR → Table Intelligence → Structure → Governance → …`.
Feature-flaggable: `PipelineConfig.flags["ocr"] = False` disables it.

**When does it run? (targeted execution, V02_S04 S5)**
- the input is an `image/*`, **or**
- native recovery produced **no text** (e.g., a scanned PDF with no text layer), **or**
- specific pages have no text (image-only pages) → OCR is **targeted** to just those pages.

If none of these hold, OCR is skipped (`status: not_needed`) — native text is preferred over OCR.

## Confidence (S6) & diagnostics (S8)
OCR text blocks carry `extraction_method = "ocr"` and text-level confidence (Tesseract's mean
per-word confidence, 0–1). The OCR stage records an `ocr` diagnostic (`ok` / `not_needed` /
`capability_unavailable` / `staged` / `disabled`) and a lineage event.

## Independence & replacement (S9/S10) — the `OcrEngine` contract
```
class OcrEngine:
    name; version
    def available(self) -> bool
    def supports(self, media_type) -> bool
    def recognize(self, data, media_type, source, pages=None) -> list[Block]   # method="ocr"
```
Engines are chosen from an `OcrRegistry` by availability + media type — never by name — so an engine
can be introduced/removed/replaced without changing the artifact contract.

| Engine | Deps | Scope | Status |
|---|---|---|---|
| `TesseractEngine` — images | `pytesseract` + `Pillow` | images | implemented; activates when installed |
| `TesseractEngine` — **scanned PDFs** | `pytesseract` + `Pillow` + **PyMuPDF** | rasterizes each page locally, then OCRs | **implemented, fully offline**; activates when installed (else reported via `StageNotImplemented`, never faked) |
| Surya / OCRmyPDF | optional | images + PDFs | plug in behind the same contract |

> **Offline:** rasterization (PyMuPDF) and OCR (Tesseract) both run locally — **no network at run
> time**. Install once via `tools/requirements-docintel.txt` (+ the system `tesseract-ocr` binary).

## Media types
`guess_media_type` maps `.png/.jpg/.jpeg/.gif/.bmp/.tif/.tiff/.webp → image/*`. PDFs use PyMuPDF for
native text (when installed); scanned PDFs route to the OCR stage.

## Why this is safe
Recovered content is governed and confidence-scored; unrecovered content is **surfaced, not
guessed**. A scanned page with no available OCR engine yields a `figure` block + an explicit `ocr`
capability gap, so a human (or a later run with an engine installed) can complete it — consistent with
the Governance contract and Quality Gates.
