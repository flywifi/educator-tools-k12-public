"""Universal fallback parsers — so docintel reads *any* file and, at minimum, understands the content.

- `RtfParser`  : strips RTF to text (stdlib).
- `UniversalFallbackParser` : the always-last resort that NEVER fails. It text-decodes anything decodable
  (utf-8/16, latin-1); for true binaries it extracts printable strings + emits file metadata, and reports
  an honest retrieval state (`metadata_only` when there's no real text) — it never fabricates content.

`UniversalFallbackParser` declares NO capabilities and `supports()` everything, so the registry's
capability-then-registration ordering always prefers a real typed parser (PDF/image/office/…) and only
falls through to this when nothing else handles the bytes.
"""
from __future__ import annotations

import re
from typing import List

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

RTF_TYPES = {"application/rtf", "text/rtf"}
_PRINTABLE_RUN = re.compile(rb"[\x20-\x7e]{4,}")


def _para_blocks(text: str, source: Source, name: str, method: str, conf: float) -> List[Block]:
    blocks: List[Block] = []
    for chunk in re.split(r"\n\s*\n", text):
        line = " ".join(chunk.split())
        if line:
            blocks.append(Block(block_id=new_id("b"), type="paragraph", page_number=1,
                                provenance=Provenance(source_id=source.filename, parser=name,
                                                      extraction_method=method, page_number=1),
                                confidence=Confidence(value=conf, level="text", method=f"{name}:{method}"),
                                text=line))
    return blocks


class RtfParser(Parser):
    name = "rtf"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type in RTF_TYPES

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        s = data.decode("latin-1", "ignore")
        if "\\rtf" not in s[:20]:
            return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                                  diagnostics={"format": "rtf", "status": "not_rtf"})
        s = re.sub(r"\\'[0-9a-fA-F]{2}", " ", s)            # hex escapes
        s = re.sub(r"\\par[d]?\b", "\n", s)                  # paragraph breaks
        s = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", s)             # control words
        s = re.sub(r"[{}]", "", s)                           # groups
        text = re.sub(r"[ \t]+", " ", s)
        blocks = _para_blocks(text, source, self.name, "heuristic", 0.8)
        return RecoveryResult(blocks=blocks, extraction_method="heuristic",
                              confidence=0.8 if blocks else 0.0, diagnostics={"format": "rtf"})


class UniversalFallbackParser(Parser):
    name = "universal"
    version = "0.1.0"
    capabilities: set = set()          # empty => never out-ranks a real typed parser

    def supports(self, media_type: str) -> bool:
        return True                     # last resort for anything

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        # 1) Try to read it as text.
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                text = data.decode(enc)
            except Exception:
                continue
            sample = text[:4000]
            if sample:
                printable = sum(1 for c in sample if c.isprintable() or c in "\n\r\t ")
                if printable / len(sample) > 0.85:
                    blocks = _para_blocks(text, source, self.name, "text_decode", 0.6)
                    if blocks:
                        return RecoveryResult(blocks=blocks, extraction_method="heuristic", confidence=0.6,
                                              diagnostics={"format": "universal-text", "encoding": enc})
        # 2) Binary: extract printable strings + file metadata; honest about how little we got.
        runs = [m.group().decode("ascii", "ignore") for m in _PRINTABLE_RUN.finditer(data[:200000])]
        meta = f"Binary file '{source.filename}' — type {media_type or 'unknown'}, {len(data)} bytes."
        prov = Provenance(source_id=source.filename, parser=self.name, extraction_method="metadata",
                          page_number=1)
        if runs:
            preview = " ".join(runs)[:4000]
            block = Block(block_id=new_id("b"), type="other", page_number=1, provenance=prov,
                          confidence=Confidence(value=0.3, level="text", method="universal:strings"),
                          text=f"{meta} Extracted text fragments: {preview}")
            return RecoveryResult(blocks=[block], extraction_method="metadata", confidence=0.3,
                                  diagnostics={"format": "universal-binary", "status": "strings_extracted",
                                               "strings": len(runs)})
        block = Block(block_id=new_id("b"), type="other", page_number=1, provenance=prov,
                      confidence=Confidence(value=0.1, level="document", method="universal:metadata"),
                      text=None)         # no text => retrieval_state stays metadata_only (honest)
        return RecoveryResult(blocks=[block], extraction_method="metadata", confidence=0.1,
                              diagnostics={"format": "universal-binary", "status": "metadata_only",
                                           "byte_length": len(data), "media_type": media_type,
                                           "note": "no extractable text; install a typed parser/engine "
                                                   "or convert this format"})
