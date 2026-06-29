# Format error catalog — OOXML / PDF / ODF / fonts (spec-grounded)

Concrete, recognizable failure classes for the documents this ecosystem reads and produces, drawn from
the authorities' own public material. Each entry: **what it looks like → why → fix → who detects it.**
`tools/validate_document.py` catches the *structural* (container) classes with **zero dependencies**;
the *deep* classes need the named tool and are honest follow-ups, never assumed.

## Hard rule (from the Open XML SDK docs)
**Structural/SDK validity ≠ openability.** Microsoft's own guidance notes an invalid DOCX that Word
refuses to open can still be reported "valid" by the Open XML SDK validator — and vice-versa. So we
report layers separately: *container OK* (we check) → *schema-valid* (Open XML SDK) → *opens in the app*
(only the app proves it). Never claim a file "opens" from a structural pass alone.

## OOXML — .docx / .pptx / .xlsx  (ECMA-376 / OPC; Open XML SDK)
| Class | Looks like | Fix | Detector |
|---|---|---|---|
| `ooxml_missing_content_types` | "problems with contents" on open; no `[Content_Types].xml` | re-export from the source app; never hand-edit the zip | validate_document (stdlib) |
| `ooxml_missing_root_rels` | parts present but `_rels/.rels` missing | re-save; the OPC relationships are required | validate_document |
| `ooxml_missing_main_part` | empty/zero-slide deck; no `word/document.xml`/`ppt/presentation.xml`/`xl/workbook.xml` | file truncated — regenerate | validate_document |
| `zip_crc_error` | partial download; a zip entry fails CRC | re-acquire the file | validate_document (`ZipFile.testzip`) |
| attribute value invalid | e.g. `rsidR` not 4-byte `hexBinary` | fix the attribute / regenerate via python-pptx-docx | **Open XML SDK** `OpenXmlValidator` |
| missing reference | `footnoteReference@id` / `r:embed` points at a part that doesn't exist | add the part or drop the reference | **Open XML SDK** |
| schema ordering | child elements added out of the schema's required order (common when hand-building runs) | emit elements in spec order (let python-docx/pptx order them) | **Open XML SDK** |

## PDF — .pdf  (ISO 32000; veraPDF for PDF/A·PDF/UA)
| Class | Looks like | Fix | Detector |
|---|---|---|---|
| `pdf_missing_header` | not a PDF / wrong bytes; no `%PDF-` | re-acquire; wrong file served | validate_document (stdlib) |
| `pdf_missing_eof` | truncated download; no `%%EOF` trailer | re-download/re-export | validate_document |
| `pdf_missing_xref` | no `startxref`/`xref`/XRef stream | repair with `qpdf --linearize` or re-export | validate_document (warns) |
| missing `StructTreeRoot` | not tagged; fails accessibility/PDF-UA | re-export as Tagged PDF | **veraPDF** (PDF/UA) |
| `MarkInfo`/`Marked` absent or false | screen readers can't navigate | set Marked true on export | **veraPDF** |
| role-map gap | non-standard structure types not mapped to standard types | add a role map | **veraPDF** |
| font not embedded | text reflows/substitutes on another machine | embed fonts on export | **veraPDF** (PDF/A) |

## ODF — .odt / .ods / .odp  (OASIS ODF)
| Class | Looks like | Fix | Detector |
|---|---|---|---|
| `odf_missing_content` | no `content.xml` in the package | re-export from LibreOffice | validate_document |
| missing `mimetype` | some readers misdetect the type | re-save as ODF | validate_document (info) |

## Fonts — rendering fidelity  (Google Noto; metric-compatible MS substitutes)
| Class | Looks like | Fix | Detector |
|---|---|---|---|
| tofu / □ boxes | glyphs missing for a script (CJK/Arabic/Hebrew/emoji) | install **Noto** (core + CJK + emoji); Noto covers 162/168 Unicode scripts | `health.py --capabilities` font coverage |
| MS-font substitution | Calibri/Cambria reflow because the real (proprietary) font is absent | install metric-compatible **Carlito** (Calibri) + **Caladea** (Cambria) + **Liberation** (Arial/Times/Courier) | capabilities preflight |
| silent substitution | layout shifts with no warning | prefer reporting the missing script as a gap over silently substituting | capabilities preflight |

## Sources
- Open XML SDK validation + the "valid-per-SDK ≠ opens" caveat — https://learn.microsoft.com/en-us/office/open-xml/word/how-to-validate-a-word-processing-document ; https://github.com/dotnet/Open-XML-SDK
- veraPDF validation profiles (PDF/A, PDF/UA rules) — https://github.com/veraPDF/veraPDF-validation-profiles
- Noto fonts (no-tofu; script coverage) — https://github.com/notofonts/noto-fonts ; CJK https://github.com/notofonts/noto-cjk ; emoji https://github.com/googlefonts/noto-emoji
- microsoft/markitdown (read any file → markdown; optional reader booster) — https://github.com/microsoft/markitdown
