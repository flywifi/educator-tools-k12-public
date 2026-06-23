"""MediaTranscriptParser — audio/video files routed to a transcription engine (honest gap if none).

Audio (.mp3/.wav/.m4a/...) and video (.mp4/.mov/...) carry no native text, so this parser delegates to
the transcription registry (shared/docintel/transcribe.py). When no engine is installed it returns an
empty, zero-confidence result with `capability_gaps: ["transcription"]` — never a fabricated transcript.
A host-AI-native or installed ASR engine plugs in behind the `Transcriber` contract to make this real
("above and beyond" base text handling).
"""
from __future__ import annotations

from ..orchestration import Parser, RecoveryResult
from ..transcribe import TranscriptionRegistry, default_transcription_registry
from ..udom import Source


class MediaTranscriptParser(Parser):
    name = "media-transcript"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def __init__(self, transcription_registry: TranscriptionRegistry | None = None) -> None:
        self._tx = transcription_registry or default_transcription_registry()

    def supports(self, media_type: str) -> bool:
        return media_type.startswith("audio/") or media_type.startswith("video/")

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        engine = self._tx.select(media_type)
        if engine is None:
            return RecoveryResult(
                blocks=[], extraction_method="transcription", confidence=0.0,
                diagnostics={"status": "capability_unavailable", "capability_gaps": ["transcription"],
                             "media_type": media_type,
                             "note": "no transcription engine installed; connect the host AI's native "
                                     "transcription or install an ASR engine — transcript not fabricated"})
        blocks = engine.transcribe(data, media_type, source)
        return RecoveryResult(blocks=blocks, extraction_method="transcription",
                              confidence=0.9 if blocks else 0.0,
                              diagnostics={"engine": engine.name, "segments": len(blocks)})
