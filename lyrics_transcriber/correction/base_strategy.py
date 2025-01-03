from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set

from lyrics_transcriber.correction.anchor_sequence import AnchorSequence, GapSequence
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsData
from ..transcribers.base_transcriber import LyricsSegment, TranscriptionResult


@dataclass
class WordCorrection:
    """Details about a single word correction."""

    original_word: str
    corrected_word: str
    segment_index: int
    word_index: int
    source: str  # e.g., "spotify", "genius"
    confidence: Optional[float]
    reason: str  # e.g., "matched_in_3_sources", "high_confidence_match"
    alternatives: Dict[str, int]  # Other possible corrections and their occurrence counts

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CorrectionResult:
    """Container for correction results with detailed correction information."""

    # Original (uncorrected) data
    original_segments: List[LyricsSegment]

    # Corrected data
    corrected_segments: List[LyricsSegment]
    corrected_text: str

    # Correction details
    corrections: List[WordCorrection]
    corrections_made: int
    confidence: float

    # Debug/analysis information
    transcribed_text: str
    reference_texts: Dict[str, str]
    anchor_sequences: List[AnchorSequence]
    gap_sequences: List[GapSequence]

    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the correction result to a JSON-serializable dictionary."""
        return {
            "transcribed_text": self.transcribed_text,
            "original_segments": [s.to_dict() for s in self.original_segments],
            "reference_texts": self.reference_texts,
            "anchor_sequences": [a.to_dict() for a in self.anchor_sequences],
            "gap_sequences": [g.to_dict() for g in self.gap_sequences],
            "corrected_text": self.corrected_text,
            "corrections_made": self.corrections_made,
            "confidence": self.confidence,
            "corrections": [c.to_dict() for c in self.corrections],
            "corrected_segments": [s.to_dict() for s in self.corrected_segments],
            "metadata": self.metadata,
        }


class CorrectionStrategy(Protocol):
    """Interface for different lyrics correction strategies."""

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply correction strategy to transcribed lyrics."""
        ...  # pragma: no cover
