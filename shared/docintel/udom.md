# UDOM — Unified Document Object Model (canonical)

A **parser-independent** representation of a recovered document. Every parser, OCR engine, and
structure pass reads/writes UDOM, so consumers never depend on a specific extraction technology
(Principle 4). The machine-readable contract is `udom.schema.json`; the Python model is `udom.py`.

## Object hierarchy
```
UDOMDocument
├── source            (filename, media_type, sha256, byte_length)
├── properties        (title, author, language, page_count, …)
├── provenance        (how the document entered + was recovered)
├── lineage[]         (ordered transformation events — every stage appends)
├── confidence        (document-level recovery confidence 0–1)
├── diagnostics       (per-stage recovery/structure diagnostics)
└── pages[]
    └── Page          (page_number, width, height, unit, reading_order[block_id…])
        └── blocks[]
            └── Block (block_id, type, bbox, page_number, text, level, provenance, confidence)
                ├── spans[]   (TextSpan: text, bbox, confidence — token/line granularity)
                └── table     (Table: rows, cols, cells[] — present when type == "table")
```

## Block types
`heading` · `paragraph` · `list` · `list_item` · `table` · `figure` · `caption` · `header` ·
`footer` · `formula` · `page_number` · `other`. Unknown content is `other` (never dropped).

## Governance fields on every object (Principles 2 & 3)
- **provenance** — `{source_id, parser, parser_version, extraction_method, page_number, bbox, timestamp}`
  where `extraction_method ∈ {native, ocr, heuristic, manual}`.
- **confidence** — `{value: 0–1, method, level ∈ {text, cell, table, page, document}}`. Low-confidence
  regions are **kept and flagged**, never silently dropped or "cleaned up" by guesswork.
- **evidence** — a back-reference (`page`, `bbox`, optional `char_range`) so a downstream fact can be
  traced to the exact source location it came from.

## Reading order
Each `Page` carries an explicit `reading_order` list of `block_id`s. The default Structure stage
uses geometric document order; advanced layout models (Tier 1/3) may overwrite it. Order is data,
not an accident of extraction — consumers rely on it.

## Tables
A `Table` is `rows × cols` (plus `header_rows`) with a flat `cells[]` list; each cell has
`{row, col, rowspan, colspan, text, bbox, confidence}`. This survives merged cells and cross-page
tables (a table may reference multiple source pages via its cells' provenance). Tables are produced by
the dedicated, swappable **Table Intelligence** stage (`table-intelligence.md`, V02 §S06) — stdlib for
docx/html/markdown today; Camelot/Surya/pdfplumber plug in without changing the contract.

## Invariants (asserted by `validation.py` and the drift guard philosophy)
1. Every `Block` has non-null `provenance` and `confidence`.
2. Every `Page` lists each of its block ids exactly once in `reading_order`.
3. `lineage` is append-only and ordered; every stage that touches the document appends an event.
4. Unrecoverable content is represented (as `other`/low-confidence), never invented.
5. The UDOM serializes to and validates against `udom.schema.json` without loss.
