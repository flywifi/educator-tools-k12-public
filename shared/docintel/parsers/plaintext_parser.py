"""PlainTextParser - the always-available, stdlib-only reference parser.

Handles text/plain, text/markdown, text/html, and .docx (via zipfile/XML). It exists so the
pipeline runs end to end with zero external dependencies; richer parsers (PyMuPDF, Docling, ...)
register alongside it and are preferred by capability when available.
"""
from __future__ import annotations

import html
import re
import zipfile
from io import BytesIO
from typing import List, Optional, Tuple

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..tables import _is_md_sep
from ..udom import Block, Source

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEXT_TYPES = {"text/plain", "text/markdown", "text/html"}


class PlainTextParser(Parser):
    name = "plaintext"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def available(self) -> bool:
        return True

    def supports(self, media_type: str) -> bool:
        return media_type in TEXT_TYPES or media_type == DOCX_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        if media_type == DOCX_TYPE:
            paras = self._docx_paragraphs(data)
            method, base_conf = "native", 0.97
        elif media_type == "text/html":
            paras = self._html_paragraphs(data.decode("utf-8", "ignore"))
            method, base_conf = "heuristic", 0.85
        else:
            markdown = media_type == "text/markdown"
            paras = self._text_paragraphs(data.decode("utf-8", "ignore"), markdown=markdown)
            method, base_conf = "native", 0.95

        blocks: List[Block] = []
        for text, kind, level in paras:
            prov = Provenance(source_id=source.filename, parser=self.name,
                              parser_version=self.version, extraction_method=method,
                              page_number=1)
            conf = Confidence(value=base_conf, level="text", method=f"{self.name}:{method}")
            blocks.append(Block(block_id=new_id("b"), type=kind, page_number=1,
                                provenance=prov, confidence=conf, text=text, level=level))
        return RecoveryResult(blocks=blocks, extraction_method=method,
                              confidence=base_conf if blocks else 0.0,
                              diagnostics={"paragraphs": len(blocks)})

    # -- format helpers --------------------------------------------------
    @staticmethod
    def _text_paragraphs(text: str, markdown: bool = False
                         ) -> List[Tuple[str, str, Optional[int]]]:
        out: List[Tuple[str, str, Optional[int]]] = []
        for chunk in re.split(r"\n\s*\n", text):
            line = chunk.strip()
            if not line:
                continue
            # Markdown tables are owned by the Table Intelligence stage - don't double-count them.
            if markdown and any(_is_md_sep(ln) for ln in chunk.splitlines()):
                continue
            kind, level = "paragraph", None
            if markdown:
                m = re.match(r"^(#{1,6})\s+(.*)$", line)
                if m:
                    kind, level, line = "heading", len(m.group(1)), m.group(2).strip()
            out.append((line, kind, level))
        return out

    @staticmethod
    def _docx_paragraphs(data: bytes) -> List[Tuple[str, str, Optional[int]]]:
        out: List[Tuple[str, str, Optional[int]]] = []
        with zipfile.ZipFile(BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        # Tables are owned by the Table Intelligence stage - strip them from the text pass.
        xml = re.sub(r"(?is)<w:tbl>.*?</w:tbl>", " ", xml)
        for para_xml in re.split(r"</w:p>", xml):
            is_heading = bool(re.search(r'w:val="Heading', para_xml))
            text = re.sub(r"<[^>]+>", "", para_xml)
            text = html.unescape(text)
            text = " ".join(text.split())
            if text:
                out.append((text, "heading" if is_heading else "paragraph", None))
        return out

    @staticmethod
    def _html_paragraphs(text: str) -> List[Tuple[str, str, Optional[int]]]:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        # Tables are owned by the Table Intelligence stage - strip them from the text pass.
        text = re.sub(r"(?is)<table\b.*?</table>", " ", text)
        text = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        out: List[Tuple[str, str, Optional[int]]] = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                out.append((line, "paragraph", None))
        return out
