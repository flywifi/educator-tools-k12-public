"""Caption / transcript-file parsers (.vtt, .srt) — stdlib only.

Reads the caption/transcript files that come out of video calls and recordings (WebVTT, SubRip) into
UDOM text blocks, and stashes the timed segments (start/end/speaker/text) in the recovery diagnostics so
a consumer can use a transcript without retyping it. Nothing is fabricated: a file that isn't a caption
track yields an empty, zero-confidence result.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

VTT_TYPE = "text/vtt"
SRT_TYPE = "application/x-subrip"

_TIMING = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})")
_VOICE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>|$)", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _clean(line: str) -> Tuple[Optional[str], str]:
    """Return (speaker, text) — speaker from a <v Name> voice tag or a 'Name: ...' lead-in."""
    speaker = None
    m = _VOICE.search(line)
    if m:
        speaker, line = m.group(1).strip(), m.group(2)
    line = _TAG.sub("", line)
    if speaker is None:
        lead = re.match(r"^([A-Z][\w .'-]{1,40}):\s+(.*)$", line)
        if lead:
            speaker, line = lead.group(1).strip(), lead.group(2)
    return speaker, " ".join(line.split())


def _segments_to_result(parser: Parser, segments: List[Dict], source: Source, fmt: str) -> RecoveryResult:
    blocks: List[Block] = []
    for seg in segments:
        prov = Provenance(source_id=source.filename, parser=parser.name, parser_version=parser.version,
                          extraction_method="native", page_number=1)
        text = f"{seg['speaker']}: {seg['text']}" if seg.get("speaker") else seg["text"]
        blocks.append(Block(block_id=new_id("b"), type="paragraph", page_number=1, provenance=prov,
                            confidence=Confidence(value=0.92, level="text", method=f"{fmt}:cue"),
                            text=text))
    return RecoveryResult(blocks=blocks, extraction_method="native",
                          confidence=0.92 if blocks else 0.0,
                          diagnostics={"format": fmt, "segments": segments})


class VttParser(Parser):
    name = "vtt"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type == VTT_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        text = data.decode("utf-8", "ignore")
        if "WEBVTT" not in text[:64].upper() and not _TIMING.search(text):
            return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                                  diagnostics={"format": "vtt", "status": "not_webvtt"})
        segments: List[Dict] = []
        for cue in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
            tm = _TIMING.search(cue)
            if not tm:
                continue
            body_lines = cue.split("\n")[cue.split("\n").index(tm.string.splitlines()[0]) + 1:] \
                if False else []
            # collect lines after the timing line, ignoring NOTE/identifier lines
            lines = [ln for ln in cue.splitlines() if ln.strip()]
            after = lines[lines.index(next(l for l in lines if _TIMING.search(l))) + 1:]
            speaker, joined = None, []
            for ln in after:
                sp, txt = _clean(ln)
                speaker = speaker or sp
                if txt:
                    joined.append(txt)
            if joined:
                segments.append({"start": tm.group(1), "end": tm.group(2),
                                 "speaker": speaker, "text": " ".join(joined)})
        return _segments_to_result(self, segments, source, "vtt")


class SrtParser(Parser):
    name = "srt"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type == SRT_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        text = data.decode("utf-8-sig", "ignore").replace("\r\n", "\n")
        if not _TIMING.search(text):
            return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                                  diagnostics={"format": "srt", "status": "not_subrip"})
        segments: List[Dict] = []
        for block in re.split(r"\n\s*\n", text):
            tm = _TIMING.search(block)
            if not tm:
                continue
            after = [ln for ln in block.splitlines() if ln.strip() and not _TIMING.search(ln)
                     and not ln.strip().isdigit()]
            speaker, joined = None, []
            for ln in after:
                sp, txt = _clean(ln)
                speaker = speaker or sp
                if txt:
                    joined.append(txt)
            if joined:
                segments.append({"start": tm.group(1), "end": tm.group(2),
                                 "speaker": speaker, "text": " ".join(joined)})
        return _segments_to_result(self, segments, source, "srt")
