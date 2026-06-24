"""LegacyOfficeParser — read legacy/ODF binary office files via LibreOffice headless (render_convert).

Handles formats no stdlib parser covers: legacy MS (.doc/.ppt/.xls) and ODF (.odp/.ods/.odg). When
`soffice` is on PATH it converts to text and ingests it; when absent, `available()` is False so the
registry skips it and the universal fallback reports an honest binary gap (never fabricates). Activated
by the render_convert capability (LibreOffice).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

_LEGACY = {
    "application/msword": ".doc",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.oasis.opendocument.presentation": ".odp",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/vnd.oasis.opendocument.graphics": ".odg",
}


class LegacyOfficeParser(Parser):
    name = "libreoffice"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def _soffice(self) -> str | None:
        return shutil.which("soffice") or shutil.which("libreoffice")

    def available(self) -> bool:
        return self._soffice() is not None

    def supports(self, media_type: str) -> bool:
        return media_type in _LEGACY

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        soffice = self._soffice()
        if not soffice:
            return RecoveryResult(blocks=[], extraction_method="metadata", confidence=0.0,
                                  diagnostics={"status": "capability_unavailable",
                                               "capability_gaps": ["render_convert"], "media_type": media_type})
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / ("in" + _LEGACY[media_type])
            src.write_bytes(data)
            try:
                subprocess.run([soffice, "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(src)],
                               capture_output=True, timeout=120, check=True)
                txt_path = src.with_suffix(".txt")
                text = txt_path.read_text(encoding="utf-8", errors="ignore") if txt_path.exists() else ""
            except Exception as exc:
                return RecoveryResult(blocks=[], extraction_method="metadata", confidence=0.0,
                                      diagnostics={"status": "convert_failed", "detail": str(exc)})
        blocks: List[Block] = []
        import re
        for chunk in re.split(r"\n\s*\n", text):
            line = " ".join(chunk.split())
            if line:
                blocks.append(Block(block_id=new_id("b"), type="paragraph", page_number=1,
                                    provenance=Provenance(source_id=source.filename, parser=self.name,
                                                          parser_version=self.version,
                                                          extraction_method="native", page_number=1),
                                    confidence=Confidence(value=0.9, level="text", method="libreoffice:convert"),
                                    text=line))
        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.9 if blocks else 0.0,
                              diagnostics={"format": "libreoffice", "source_type": media_type})
