"""WhisperTranscriber — local, offline ASR engine behind the docintel Transcriber contract.

Makes audio/video transcription real WHEN `faster-whisper` (+ the system `ffmpeg`) is installed; absent,
`available()` is False so the registry never selects it and MediaTranscriptParser reports an honest
`transcription` gap (no fabricated transcript). Chosen by availability + media type, never by name.
Install: tools/requirements-media.txt + `apt-get install ffmpeg`.
"""
from __future__ import annotations

import importlib.util
import math
import os
import tempfile
from typing import List

from ..governance import Confidence, Provenance, new_id
from ..transcribe import Transcriber
from ..udom import Block, Source

_SUFFIX = {"audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/mp4": ".m4a", "audio/aac": ".aac",
           "audio/ogg": ".ogg", "audio/flac": ".flac", "video/mp4": ".mp4", "video/quicktime": ".mov",
           "video/webm": ".webm", "video/x-matroska": ".mkv", "video/x-msvideo": ".avi"}


class WhisperTranscriber(Transcriber):
    name = "faster-whisper"
    version = "0.1.0"

    def available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def supports(self, media_type: str) -> bool:
        return media_type.startswith("audio/") or media_type.startswith("video/")

    def transcribe(self, data: bytes, media_type: str, source: Source) -> List[Block]:
        from faster_whisper import WhisperModel  # lazy: only when actually transcribing

        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=_SUFFIX.get(media_type, ".bin"), delete=False) as tf:
                tf.write(data)
                path = tf.name
            model = WhisperModel(os.environ.get("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
            segments, _info = model.transcribe(path)
            blocks: List[Block] = []
            for seg in segments:
                text = (seg.text or "").strip()
                if not text:
                    continue
                value = max(0.0, min(1.0, math.exp(getattr(seg, "avg_logprob", -0.5))))
                blocks.append(Block(
                    block_id=new_id("b"), type="paragraph", page_number=1,
                    provenance=Provenance(source_id=source.filename, parser=self.name,
                                          parser_version=self.version, extraction_method="transcription",
                                          page_number=1),
                    confidence=Confidence(value=value, level="text", method="whisper:avg_logprob"),
                    text=text))
            return blocks
        finally:
            if path and os.path.exists(path):
                os.unlink(path)
