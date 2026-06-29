"""ResilientHtmlParser - robust, i18n-safe HTML recovery that survives messy / restructured markup.

Thin wrapper over the shared shared/docintel/html_util toolkit: i18n-safe decode (foreign scripts,
legacy encodings, full punctuation preserved) -> resilient text blocks (Scrapling/lxml, stdlib
fallback). Parser ONLY: no fetching, no anti-bot evasion. Always runs (stdlib tier guarantees output);
records which engine actually ran. Registered ahead of plaintext for text/html.
"""
from __future__ import annotations

from typing import List

from ..governance import Confidence, Provenance, new_id
from ..html_util import decode_bytes, get_text_blocks, scrapling_present
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source


class ResilientHtmlParser(Parser):
    name = "resilient_html"
    version = "0.2.0"
    capabilities = {"text", "reading_order"}

    def available(self) -> bool:
        return True  # the stdlib tier in html_util guarantees a result with no extra deps

    def supports(self, media_type: str) -> bool:
        return media_type == "text/html"

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        text = decode_bytes(data)                 # encoding-aware (not utf-8/ignore) -> keeps foreign chars
        method, paras = get_text_blocks(text)
        base_conf = 0.90 if method != "stdlib_html" else 0.85
        blocks: List[Block] = []
        for content, kind, level in paras:
            prov = Provenance(source_id=source.filename, parser=self.name,
                              parser_version=self.version, extraction_method=method, page_number=1)
            conf = Confidence(value=base_conf, level="text", method=f"{self.name}:{method}")
            blocks.append(Block(block_id=new_id("b"), type=kind, page_number=1,
                                provenance=prov, confidence=conf, text=content, level=level))
        return RecoveryResult(blocks=blocks, extraction_method=method,
                              confidence=base_conf if blocks else 0.0,
                              diagnostics={"paragraphs": len(blocks), "resilient_engine": method,
                                           "scrapling_available": scrapling_present()})
