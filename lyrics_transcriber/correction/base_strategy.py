from typing import List, Protocol

from lyrics_transcriber.types import LyricsData, TranscriptionResult, CorrectionResult


class CorrectionStrategy(Protocol):
    """Interface for different lyrics correction strategies."""

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply correction strategy to transcribed lyrics."""
        ...  # pragma: no cover
