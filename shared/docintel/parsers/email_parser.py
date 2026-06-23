"""EmlParser - RFC-822 email (.eml) reader, stdlib only.

Reads a saved email message (the file a teacher forwards/drops) using the stdlib `email` package, which
handles MIME, transfer encodings, and header folding. Headers + body are normalized into UDOM text
blocks plus a structured `email` dict in the recovery diagnostics, so a consumer (e.g.
skills/meeting-classifier) can use the sender/subject/body without retyping. Nothing is fabricated: a
file that does not parse as a message yields an empty, zero-confidence result.
"""
from __future__ import annotations

import html as _html
import re
from email import policy as email_policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from typing import List, Optional

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

EML_TYPE = "message/rfc822"


def _html_to_text(text: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return _html.unescape(text)


def _names(pairs: List) -> List[str]:
    """Prefer display names, fall back to the address; drop empties."""
    out = []
    for name, addr in pairs:
        chosen = (name or addr).strip()
        if chosen:
            out.append(chosen)
    return out


class EmlParser(Parser):
    name = "eml"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type == EML_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        try:
            msg = BytesParser(policy=email_policy.default).parsebytes(data)
        except Exception:
            return self._empty("unparseable")
        if not (msg["From"] or msg["Subject"] or msg["To"]):
            return self._empty("not_email")

        from_name, from_addr = parseaddr(str(msg["From"] or ""))
        from_domain = from_addr.split("@")[-1] if "@" in from_addr else ""
        to = _names(getaddresses(msg.get_all("To", [])))
        cc = _names(getaddresses(msg.get_all("Cc", [])))
        subject = str(msg["Subject"] or "").strip()
        date = str(msg["Date"] or "").strip()

        body = ""
        body_part = msg.get_body(preferencelist=("plain", "html"))
        if body_part is not None:
            try:
                content = body_part.get_content()
            except Exception:
                content = ""
            body = _html_to_text(content) if body_part.get_content_type() == "text/html" else content
        attachments = [p.get_filename() for p in msg.iter_attachments() if p.get_filename()]

        email_obj = {"from": from_addr, "from_name": from_name, "from_domain": from_domain,
                     "to": to, "cc": cc, "subject": subject, "date": date,
                     "attachments": attachments}

        prov = Provenance(source_id=source.filename, parser=self.name, parser_version=self.version,
                          extraction_method="native", page_number=1)

        def blk(kind: str, text: str, level: Optional[int] = None) -> Block:
            return Block(block_id=new_id("b"), type=kind, page_number=1, provenance=prov,
                         confidence=Confidence(value=0.95, level="text", method=f"eml:{kind}"),
                         text=text, level=level)

        sender = f"{from_name} <{from_addr}>".strip() if from_addr else (from_name or "(unknown)")
        blocks: List[Block] = [blk("heading", subject or "(no subject)", 1),
                               blk("paragraph", f"From: {sender}")]
        if to:
            blocks.append(blk("paragraph", f"To: {', '.join(to)}"))
        if date:
            blocks.append(blk("paragraph", f"Date: {date}"))
        for chunk in re.split(r"\n\s*\n", body):
            line = " ".join(chunk.split())
            if line:
                blocks.append(blk("paragraph", line))
        if attachments:
            blocks.append(blk("paragraph", f"Attachments: {', '.join(attachments)}"))

        return RecoveryResult(blocks=blocks, extraction_method="native", confidence=0.95,
                              diagnostics={"format": "eml", "email": email_obj})

    def _empty(self, status: str) -> RecoveryResult:
        return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                              diagnostics={"format": "eml", "status": status})
