from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Set, Protocol, Tuple
from enum import Enum


@dataclass
class Word:
    """Represents a single word with its timing and confidence information."""

    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert Word to dictionary for JSON serialization."""
        d = asdict(self)
        # Remove confidence from output if it's None
        if d["confidence"] is None:
            del d["confidence"]
        return d


@dataclass
class LyricsSegment:
    """Represents a segment/line of lyrics with timing information."""

    text: str
    words: List[Word]
    start_time: float
    end_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert LyricsSegment to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "words": [word.to_dict() for word in self.words],
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class LyricsMetadata:
    """Standardized metadata for lyrics results."""

    source: str
    track_name: str
    artist_names: str

    # Common metadata fields
    album_name: Optional[str] = None
    duration_ms: Optional[int] = None
    explicit: Optional[bool] = None
    language: Optional[str] = None
    is_synced: bool = False

    # Lyrics provider details
    lyrics_provider: Optional[str] = None
    lyrics_provider_id: Optional[str] = None

    # Provider-specific metadata
    provider_metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class LyricsData:
    """Standardized response format for all lyrics providers."""

    lyrics: str
    segments: List[LyricsSegment]
    metadata: LyricsMetadata
    source: str  # e.g., "genius", "spotify", etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "lyrics": self.lyrics,
            "segments": [segment.to_dict() for segment in self.segments],
            "metadata": self.metadata.to_dict(),
            "source": self.source,
        }


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
class TranscriptionData:
    """Structured container for transcription results."""

    segments: List[LyricsSegment]
    words: List[Word]
    text: str
    source: str  # e.g., "whisper", "audioshake"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert TranscriptionData to dictionary for JSON serialization."""
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "words": [word.to_dict() for word in self.words],
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class TranscriptionResult:
    name: str
    priority: int
    result: TranscriptionData


class PhraseType(Enum):
    """Types of phrases we can identify"""

    COMPLETE = "complete"  # Grammatically complete unit
    PARTIAL = "partial"  # Incomplete but valid fragment
    CROSS_BOUNDARY = "cross"  # Crosses natural boundaries


@dataclass
class PhraseScore:
    """Scores for a potential phrase"""

    phrase_type: PhraseType
    natural_break_score: float  # 0-1, how well it respects natural breaks
    length_score: float  # 0-1, how appropriate the length is

    @property
    def total_score(self) -> float:
        """Calculate total score with weights"""
        weights = {PhraseType.COMPLETE: 1.0, PhraseType.PARTIAL: 0.7, PhraseType.CROSS_BOUNDARY: 0.3}
        return weights[self.phrase_type] * 0.5 + self.natural_break_score * 0.3 + self.length_score * 0.2


@dataclass
class AnchorSequence:
    """Represents a sequence of words that appears in both transcribed and reference lyrics."""

    words: List[str]
    transcription_position: int  # Starting position in transcribed text
    reference_positions: Dict[str, int]  # Source -> position mapping
    confidence: float

    @property
    def text(self) -> str:
        """Get the sequence as a space-separated string."""
        return " ".join(self.words)

    @property
    def length(self) -> int:
        """Get the number of words in the sequence."""
        return len(self.words)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the anchor sequence to a JSON-serializable dictionary."""
        return {
            "words": self.words,
            "text": self.text,
            "length": self.length,
            "transcription_position": self.transcription_position,
            "reference_positions": self.reference_positions,
            "confidence": self.confidence,
        }


@dataclass
class ScoredAnchor:
    """An anchor sequence with its quality score"""

    anchor: AnchorSequence
    phrase_score: PhraseScore

    @property
    def total_score(self) -> float:
        """Combine confidence, phrase quality, and length"""
        # Length bonus: (length - 1) * 0.1 gives 0.1 per extra word
        length_bonus = (self.anchor.length - 1) * 0.1
        # Base score heavily weighted towards confidence
        base_score = self.anchor.confidence * 0.8 + self.phrase_score.total_score * 0.2
        # Combine scores
        return base_score + length_bonus

    def to_dict(self) -> Dict[str, Any]:
        """Convert the scored anchor to a JSON-serializable dictionary."""
        return {
            **self.anchor.to_dict(),
            "phrase_score": {
                "phrase_type": self.phrase_score.phrase_type.value,
                "natural_break_score": self.phrase_score.natural_break_score,
                "length_score": self.phrase_score.length_score,
                "total_score": self.phrase_score.total_score,
            },
            "total_score": self.total_score,
        }


@dataclass
class GapSequence:
    """Represents a sequence of words between anchor sequences in transcribed lyrics."""

    words: Tuple[str, ...]
    transcription_position: int
    preceding_anchor: Optional[AnchorSequence]
    following_anchor: Optional[AnchorSequence]
    reference_words: Dict[str, List[str]]
    corrections: List[WordCorrection] = field(default_factory=list)

    def __post_init__(self):
        # Convert words list to tuple if it's not already
        if isinstance(self.words, list):
            object.__setattr__(self, 'words', tuple(self.words))

    def __hash__(self):
        # Hash based on words and position
        return hash((self.words, self.transcription_position))

    def __eq__(self, other):
        if not isinstance(other, GapSequence):
            return NotImplemented
        return (self.words == other.words and 
                self.transcription_position == other.transcription_position)

    @property
    def text(self) -> str:
        """Get the sequence as a space-separated string."""
        return " ".join(self.words)

    @property
    def length(self) -> int:
        """Get the number of words in the sequence."""
        return len(self.words)

    @property
    def was_corrected(self) -> bool:
        """Check if this gap has any corrections."""
        return len(self.corrections) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the gap sequence to a JSON-serializable dictionary."""
        return {
            "words": self.words,
            "text": self.text,
            "length": self.length,
            "transcription_position": self.transcription_position,
            "preceding_anchor": self.preceding_anchor.to_dict() if self.preceding_anchor else None,
            "following_anchor": self.following_anchor.to_dict() if self.following_anchor else None,
            "reference_words": self.reference_words,
            "corrections": [c.to_dict() for c in self.corrections],
        }


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
