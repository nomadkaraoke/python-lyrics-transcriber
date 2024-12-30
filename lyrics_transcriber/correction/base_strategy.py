from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsData
from ..transcribers.base_transcriber import LyricsSegment, TranscriptionResult


@dataclass
class CorrectionResult:
    """Container for correction results."""

    segments: List[LyricsSegment]
    text: str
    confidence: float
    corrections_made: int
    source_mapping: Dict[str, str]  # Maps corrected words to their source
    metadata: Dict[str, Any]


class CorrectionStrategy(Protocol):
    """Interface for different lyrics correction strategies."""

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply correction strategy to transcribed lyrics."""
        ...  # pragma: no cover
