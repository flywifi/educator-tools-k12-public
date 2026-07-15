# corpus/ — adversarial ingestion documents (ingestion track)

The ingestion track (axis 7, parsing) needs documents that exercise docintel's harder code paths, which the
capability inventory found are implemented but **unexercised by any committed sample**:

- **Encodings** (`shared/docintel/html_util.py:decode_bytes`): CJK, Cyrillic, Arabic, Greek,
  Shift-JIS, Windows-1252, Mac Roman — files whose foreign characters a naive
  `decode('utf-8','ignore')` would silently drop.
- **Nested containers** (`shared/docintel/recurse.py`): a `.docx`/`.pptx` with `/embeddings/`, a
  `.zip` of documents, a `.eml` with document attachments — to test recursive parsing + the
  sha256 cycle guard.
- **Messy tables** (`shared/docintel/tables.py`): merged cells (`w:gridSpan`, `w:vMerge`),
  ragged markdown rows, contiguous `<th>` header detection.

Plus the real **gold set already in the repo** — the messy government docs under
`shared/standards/resources/florida/` (legacy `.doc` + their `.doc.docx` doubles, varied-vintage
PDFs) — ideal for same-content cross-format scoring.

Scoring for this axis (see the root README win-bar): text-recovery, table-fidelity (TEDS/GriTS),
i18n-preservation, container recursion, and **retrieval_state honesty** — the differentiator that
matters even where raw extraction accuracy trails a dedicated engine: docintel reports what it
could NOT recover (capability gaps, `metadata_only` vs `content_ingested`) instead of silently
dropping content or fabricating text.

*(Empty until the ingestion track runs. Synthesize the adversarial files here with a small
generator so they're reproducible rather than opaque binaries checked in by hand.)*
