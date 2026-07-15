<!-- last_reviewed: 2026-07-15 | owner: office-engine-maintainer -->
# shared/office — real Office + Google authoring (capability-gated)

Produces **actual editable files** (`.pptx` / `.docx` / `.xlsx`) and Google Docs/Sheets/Slides
outputs from a structured spec — the "above baseline" deliverable, not a description of a document.
Consumed by content skills such as `presentation-builder` (deck → `.pptx`) and
`family-communication` (letter → `.docx`).

## What's here
- `office_authoring.py` — `build_pptx` / `build_docx` / `build_xlsx` + `convert` (PDF/PNG). Uses
  `python-pptx` / `python-docx` / `openpyxl` **when installed** (`tools/requirements-office.txt`).
- `google_bridge.py` — `to_google`: emits the Office file (Google imports it losslessly) **plus** a
  generated Apps Script (`.gs`) for native SlidesApp/DocumentApp/SpreadsheetApp automation. Live
  creation is done by the host AI's native Google integration or a deployment-provided clasp runner —
  this module never ships an OAuth client.
- `__init__.py` — re-exports the builders + `to_google`.

## Non-negotiable invariants
- **Never emit a fake/empty binary.** If a required library is absent, write the spec-JSON sidecar and
  return an **honest capability gap** — the caller surfaces it, it is not silently a "success".
- The document `author` is the **directing teacher**, never "AI" or a library name.
- The caller (the skill) adds the governed metadata block + `human_review_required` — the spec itself
  is decision support, not a finished, approved artifact.

## Maintainer gotchas (learned the hard way)
- **`soffice`/LibreOffice discovery is PATH **plus** standard install dirs — do NOT revert to
  PATH-only.** On Windows/macOS `soffice` is not on `PATH` by default; `_find_soffice()` falls back to
  the standard install locations (`C:\Program Files\LibreOffice\…`, `/Applications/LibreOffice.app/…`).
  Without this, PDF/PNG render silently "isn't available" on a teacher's desktop. If LibreOffice is
  genuinely absent the document is still produced — only the PDF/PNG QA render is skipped, with a note.
- **Capability gating is layered:** `.pptx`/`.docx`/`.xlsx` need the matching Python lib; PDF/PNG
  additionally needs LibreOffice. Report each missing capability honestly and independently.
- Cross-surface details live in `docs/DEPLOYMENT_SURFACES.md` ("Cross-platform notes"); keep them in
  sync with this file.
