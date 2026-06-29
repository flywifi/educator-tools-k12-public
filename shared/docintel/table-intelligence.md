# Table Intelligence (canonical) — V02_S06

*"Tables are structures, not formatted text. Normalized table representations are platform outputs."*
Tables carry structured information that cannot be reliably represented as plain text, so they get a
**dedicated, replaceable** recovery stage. Implemented in `tables.py` (+ `parsers/pdf_table_parser.py`);
normalized output is the UDOM `Table`/`Cell` (`udom.md`).

## The stage (runs after Recovery, before Structure)
Pipeline order: `Ingestion → Recovery → Table Intelligence → Structure → Governance → Knowledge …`.
The text parser **skips table regions** so content is never double-counted; this stage owns tables.
It is feature-flaggable: `PipelineConfig.flags["tables"] = False` turns it off.

## What it does (V02_S06 §4–§9)
1. **Detection** — find tabular regions (`<w:tbl>`, `<table>`, Markdown pipe tables).
2. **Reconstruction** — recover rows, columns, **headers**, and **merged cells** (colspan/rowspan):
   HTML `colspan`/`rowspan`, DOCX `<w:gridSpan>` (colspan) + `<w:vMerge>` (rowspan), placed with an
   occupancy-aware algorithm so spans land in the right grid coordinates.
3. **Content recovery** — cell + header content, relationships preserved (`header_rows` on `Table`).
4. **Normalization** — into the platform-standard `Table` (`rows`, `cols`, `header_rows`, `cells[]`
   with `row,col,rowspan,colspan,text,confidence`).
5. **Conflict handling** (§8) — ragged Markdown rows are padded (and counted); orphan DOCX vMerge
   continuations are counted as `merge_conflicts`; conflicts lower the table confidence rather than
   being hidden.
6. **Confidence** (§9) — **table-level** and **cell-level** confidence (new `Confidence.level`
   values `table` / `cell`), e.g. docx 0.95, html 0.90, markdown 0.90 (−0.15 on conflicts),
   pdfplumber 0.80.

## Independence & replacement (§10/§11) — the `TableExtractor` contract
```
class TableExtractor:
    name; version
    def available(self) -> bool
    def supports(self, media_type) -> bool
    def extract(self, data, media_type, source) -> list[Block]   # type="table" blocks
```
Engines are selected from a `TableRegistry` by availability + media type — never by name — so a table
engine can be introduced/removed/replaced **without changing the artifact contract** (same guarantee
as parsers).

| Engine | Deps | Formats | Status |
|---|---|---|---|
| `StdlibTableExtractor` | none | `.docx`, `.html`, `.md` | available (default) |
| `PdfPlumberTableExtractor` | `pdfplumber` (optional) | `.pdf` | activates when installed |

Camelot / Surya table models plug in the same way (a new `TableExtractor` subclass + `register()`).

## Validation (`validation.py`)
`A-003_table_recovery` now reports `{tables, cells, wellformed}` when tables are present
(well-formed = every cell's `row/col + span` stays within `rows×cols`); it returns `staged` only when
a labeled reference set is needed for full accuracy scoring. Nothing is fabricated — a region that
can't be reconstructed is reported, not invented.
