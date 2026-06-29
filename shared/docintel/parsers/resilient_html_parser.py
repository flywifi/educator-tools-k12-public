"""ResilientHtmlParser - robust HTML recovery that survives messy / restructured markup.

Upgrades HTML recovery beyond the stdlib tag-stripper. It prefers Scrapling's resilient parser
(the PARSER ONLY - base install, no fetchers/stealth/network) and its lxml engine, then falls back
to lxml.html, then to the proven stdlib heuristic - in that order, automatically, so it ALWAYS runs.

WHY THIS HELPS UPLOADS: lxml/Scrapling parse broken or re-laid-out saved pages (a district page whose
structure drifted, a "Save As HTML" dump with tag soup) far more reliably than the stdlib stripper.
That is exactly what lets an uploaded page be re-parsed correctly now OR at a later time, even after
the source site changed. Honest: it records which engine actually ran; no fabrication, no network,
no anti-bot evasion - extraction only.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_Para = Tuple[str, str, Optional[int]]  # (text, block_type, heading_level)


def _scrapling_present() -> bool:
    try:
        import scrapling  # noqa: F401
        return True
    except Exception:
        return False


class ResilientHtmlParser(Parser):
    name = "resilient_html"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def available(self) -> bool:
        return True  # always: the stdlib tier guarantees a result even with no extra deps

    def supports(self, media_type: str) -> bool:
        return media_type == "text/html"

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        text = data.decode("utf-8", "ignore")
        method, paras = self._extract(text)
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
                                           "scrapling_available": _scrapling_present()})

    # -- tiered extraction (resilient -> robust -> always-works) ----------
    def _extract(self, text: str) -> Tuple[str, List[_Para]]:
        # Tier 1/2: lxml DOM walk in document order (lxml is Scrapling's parser engine; pulled in by
        # a parser-only `pip install scrapling`, or a standalone lxml). Robust on malformed HTML.
        try:
            import lxml.html as LH
            root = LH.fromstring(text)
            for bad in root.xpath("//script | //style | //noscript | //template"):
                bad.drop_tree()
            paras: List[_Para] = []
            # Walk in document order; emit each target tag once. To avoid re-emitting a nested target
            # (e.g. a <p> inside an <li>), skip any element that has a target ANCESTOR — the outer one's
            # text_content already covers it. (lxml proxies have no stable id(), so dedup via ancestors.)
            _anc = ("ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or "
                    "self::h6 or self::p or self::li]")
            for el in root.iter():
                tag = el.tag if isinstance(el.tag, str) else ""
                if tag in _HEADINGS:
                    kind, level = "heading", _HEADINGS[tag]
                elif tag == "li":
                    kind, level = "list_item", None
                elif tag == "p":
                    kind, level = "paragraph", None
                else:
                    continue
                if el.xpath(_anc):
                    continue  # nested inside another target; the outer element already emitted this text
                content = " ".join(el.text_content().split())
                if content:
                    paras.append((content, kind, level))
            if paras:
                return ("scrapling_lxml" if _scrapling_present() else "lxml_html"), paras
        except Exception:
            pass
        # Tier 3: stdlib fallback - reuse the proven PlainTextParser HTML heuristic, else strip tags.
        try:
            from .plaintext_parser import PlainTextParser
            return "stdlib_html", list(PlainTextParser()._html_paragraphs(text))
        except Exception:
            stripped = " ".join(re.sub(r"<[^>]+>", " ", text).split())
            return "stdlib_html", ([(stripped, "paragraph", None)] if stripped else [])
