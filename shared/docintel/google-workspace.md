# Google Workspace document types (canonical)

How docintel reads **Google Docs, Sheets, and Slides**. A Google Workspace file has no portable
"document" of its own — you either **export** it (Drive `files.export`) to an open/standard format, or
read **Google Docs API JSON** (`documents.get`). docintel handles both, with **stdlib only**, into the
same governed UDOM used everywhere else.

> **Boundary (read first).** This skill *reads* documents you provide; it does **not** fetch from
> Google Drive. Drive/Docs API access needs OAuth + network and is a separate connector concern (same
> boundary as the standards crawler). Bring the exported file, or the Docs API JSON response, and
> docintel will parse it. No credentials, scopes, or network calls happen here.

## What's supported
| Workspace app | Native | Common exports (handled) |
|---|---|---|
| **Docs** | Google Docs API JSON (`GoogleDocsParser`) | `.docx` (PlainTextParser), `.odt` (OdtParser), `.html`, `.txt`, `.pdf` |
| **Sheets** | — | `.csv`/`.tsv` (CsvParser), `.xlsx` (XlsxParser) |
| **Slides** | — | `.pptx` (PptxParser), `.pdf` |

All are recovered into UDOM with provenance/lineage/confidence; tables become UDOM `Table`/`Cell`.

## Google Docs API JSON (the native path) — `google.py`
`GoogleDocsParser` reads a `documents.get` resource: the `title`, each `body.content[]`
paragraph (with `namedStyleType` → heading level: `TITLE`/`SUBTITLE`/`HEADING_1..6`), and `table`
elements (`tableRows[].tableCells[].content`) → UDOM headings/paragraphs/tables. Selected for
`application/json` and **content-sniffed** (`is_google_doc_json`): a non-Docs JSON yields an empty
recovery with a `not_google_docs_json` diagnostic rather than a wrong parse.

## Export-format parsers — `parsers/workspace_parsers.py`
- **OdtParser** (`.odt`) — ODF text: `text:h` (outline level → heading), `text:p`, and `table:table`
  with `number-columns/rows-spanned` (merged cells via the shared occupancy placement).
- **CsvParser** (`.csv`/`.tsv`) — stdlib `csv` → one normalized table.
- **XlsxParser** (`.xlsx`) — stdlib zip: resolves `sharedStrings.xml` and each `worksheets/sheetN.xml`
  (cell refs `A1` → row/col) → one table per sheet.
- **PptxParser** (`.pptx`) — stdlib zip: each `slides/slideN.xml` becomes a page; `<a:p>`/`<a:t>` runs
  become paragraph blocks.

## Drive export MIME map (reference)
`google.DRIVE_EXPORT_MIME` records the `files.export` targets, so an upstream connector knows what to
request:
- `…google-apps.document` → docx · odt · pdf · html · txt
- `…google-apps.spreadsheet` → xlsx · csv · ods
- `…google-apps.presentation` → pptx · pdf · odp

## Staged
`.ods` / `.odp` (OpenDocument spreadsheet/presentation) are recognized media types but their parsers
are not yet written — they report an honest `no_parser_available` gap (export to xlsx/csv/pptx, or add
a parser behind the `Parser` contract). Google **Sheets/Slides API JSON** parsers can be added the
same way as `GoogleDocsParser`. Slide/`.pptx` table extraction is text-first for now.
