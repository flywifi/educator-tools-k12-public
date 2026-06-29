"""Transcription engine contract (audio/video -> text) — a swappable, availability-gated engine.

There is no stdlib ASR, so **no transcriber is registered by default**: audio/video inputs honestly
report a capability gap instead of fabricating a transcript (same honesty rule as OCR). A real engine —
a local ASR, or the **host AI's native transcription** (per shared/connectors: live capability is the
host AI's, not a client we build) — plugs in behind this contract and is chosen by availability + media
type, never by name (Parser/OcrEngine pattern).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .udom import Block, Source


class Transcriber(ABC):
    name: str = "transcriber"
    version: str = "0"

    def available(self) -> bool:
        return True

    @abstractmethod
    def supports(self, media_type: str) -> bool: ...

    @abstractmethod
    def transcribe(self, data: bytes, media_type: str, source: Source) -> List[Block]:
        """Return text Blocks with extraction_method='transcription' (timestamps/speakers when known)."""


class TranscriptionRegistry:
    def __init__(self) -> None:
        self._engines: List[Transcriber] = []

    def register(self, engine: Transcriber) -> "TranscriptionRegistry":
        self._engines.append(engine)
        return self

    def available(self) -> List[Transcriber]:
        return [e for e in self._engines if e.available()]

    def select(self, media_type: str) -> Optional[Transcriber]:
        for e in self.available():
            if e.supports(media_type):
                return e
        return None

    def describe(self) -> List[dict]:
        return [{"name": e.name, "version": e.version, "available": e.available()} for e in self._engines]


def default_transcription_registry() -> TranscriptionRegistry:
    """No stdlib ASR, so engines are availability-gated: WhisperTranscriber registers but only `select`s
    when `faster-whisper` is installed; otherwise audio/video is reported as a gap (never faked). Other
    engines (host-AI-native, cloud) plug in behind the same contract."""
    reg = TranscriptionRegistry()
    try:
        from .parsers.whisper_transcriber import WhisperTranscriber
        reg.register(WhisperTranscriber())
    except Exception:  # pragma: no cover - registration must never break the pipeline
        pass
    return reg
