from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Set, Protocol, Tuple
from enum import Enum


@dataclass
class Word:
    """Represents a single word with its timing (in seconds) and confidence information."""

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Word":
        """Create Word from dictionary."""
        return cls(
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            confidence=data.get("confidence"),  # Use get() since confidence is optional
        )


@dataclass
class LyricsSegment:
    """Represents a segment/line of lyrics with timing information in seconds."""

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LyricsSegment":
        """Create LyricsSegment from dictionary."""
        return cls(
            text=data["text"],
            words=[Word.from_dict(w) for w in data["words"]],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )


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
    corrected_word: str  # Empty string indicates word should be deleted
    segment_index: int
    original_position: int
    source: str  # e.g., "spotify", "genius"
    confidence: Optional[float]
    reason: str  # e.g., "matched_in_3_sources", "high_confidence_match"
    alternatives: Dict[str, int]  # Other possible corrections and their occurrence counts
    is_deletion: bool = False  # New field to explicitly mark deletions
    # New fields for handling word splits
    split_index: Optional[int] = None  # Position in the split sequence (0-based)
    split_total: Optional[int] = None  # Total number of words in split
    # New field to track position after corrections
    corrected_position: Optional[int] = None
    # New fields to match TypeScript interface
    reference_positions: Optional[Dict[str, int]] = None  # Maps source to position in reference text
    length: int = 1  # Default to 1 for single-word corrections

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordCorrection":
        """Create WordCorrection from dictionary."""
        return cls(**data)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert PhraseScore to dictionary for JSON serialization."""
        return {
            "phrase_type": self.phrase_type.value,  # Convert enum to value for JSON
            "natural_break_score": self.natural_break_score,
            "length_score": self.length_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhraseScore":
        """Create PhraseScore from dictionary."""
        return cls(
            phrase_type=PhraseType(data["phrase_type"]), natural_break_score=data["natural_break_score"], length_score=data["length_score"]
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnchorSequence":
        """Create AnchorSequence from dictionary."""
        return cls(
            words=data["words"],
            transcription_position=data["transcription_position"],
            reference_positions=data["reference_positions"],
            confidence=data["confidence"],
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoredAnchor":
        """Create ScoredAnchor from dictionary."""
        return cls(anchor=AnchorSequence.from_dict(data["anchor"]), phrase_score=PhraseScore.from_dict(data["phrase_score"]))


@dataclass
class GapSequence:
    """Represents a sequence of words between anchor sequences in transcribed lyrics."""

    words: Tuple[str, ...]
    transcription_position: int  # Original starting position in transcription
    preceding_anchor: Optional[AnchorSequence]
    following_anchor: Optional[AnchorSequence]
    reference_words: Dict[str, List[str]]
    reference_words_original: Dict[str, List[str]]
    corrections: List[WordCorrection] = field(default_factory=list)
    _corrected_positions: Set[int] = field(default_factory=set, repr=False)
    _position_offset: int = field(default=0, repr=False)  # Track cumulative position changes

    def add_correction(self, correction: WordCorrection) -> None:
        """Add a correction and mark its position as corrected."""
        self.corrections.append(correction)
        relative_pos = correction.original_position - self.transcription_position
        self._corrected_positions.add(relative_pos)

        # Update position offset based on correction type
        if correction.is_deletion:
            self._position_offset -= 1
        elif correction.split_total:
            self._position_offset += correction.split_total - 1

        # Update corrected position for the correction
        correction.corrected_position = correction.original_position + self._position_offset

    def get_corrected_position(self, original_position: int) -> int:
        """Convert an original position to its corrected position."""
        offset = sum(
            -1 if c.is_deletion else (c.split_total - 1 if c.split_total else 0)
            for c in self.corrections
            if c.original_position < original_position
        )
        return original_position + offset

    @property
    def corrected_length(self) -> int:
        """Get the length after applying all corrections."""
        return self.length + self._position_offset

    def is_word_corrected(self, relative_position: int) -> bool:
        """Check if a word at the given position (relative to gap start) has been corrected."""
        return relative_position in self._corrected_positions

    @property
    def uncorrected_words(self) -> List[Tuple[int, str]]:
        """Get list of (position, word) tuples for words that haven't been corrected yet."""
        return [(i, word) for i, word in enumerate(self.words) if i not in self._corrected_positions]

    @property
    def is_fully_corrected(self) -> bool:
        """Check if all words in the gap have been corrected."""
        return len(self._corrected_positions) == self.length

    def __hash__(self):
        # Hash based on words and position
        return hash((self.words, self.transcription_position))

    def __eq__(self, other):
        if not isinstance(other, GapSequence):
            return NotImplemented
        return self.words == other.words and self.transcription_position == other.transcription_position

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
            "reference_words_original": self.reference_words_original,
            "corrections": [c.to_dict() for c in self.corrections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GapSequence":
        """Create GapSequence from dictionary."""
        gap = cls(
            words=tuple(data["words"]),
            transcription_position=data["transcription_position"],
            preceding_anchor=AnchorSequence.from_dict(data["preceding_anchor"]) if data["preceding_anchor"] else None,
            following_anchor=AnchorSequence.from_dict(data["following_anchor"]) if data["following_anchor"] else None,
            reference_words=data["reference_words"],
            reference_words_original=data.get("reference_words_original", {}),
        )
        # Add any corrections from the data
        if "corrections" in data:
            for correction_data in data["corrections"]:
                gap.add_correction(WordCorrection.from_dict(correction_data))
        return gap


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
    resized_segments: List[LyricsSegment]

    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the correction result to a JSON-serializable dictionary."""
        return {
            "transcribed_text": self.transcribed_text,
            "original_segments": [s.to_dict() for s in self.original_segments],
            "reference_texts": self.reference_texts,
            "anchor_sequences": [a.to_dict() for a in self.anchor_sequences],
            "gap_sequences": [g.to_dict() for g in self.gap_sequences],
            "resized_segments": [s.to_dict() for s in self.resized_segments],
            "corrected_text": self.corrected_text,
            "corrections_made": self.corrections_made,
            "confidence": self.confidence,
            "corrections": [c.to_dict() for c in self.corrections],
            "corrected_segments": [s.to_dict() for s in self.corrected_segments],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrectionResult":
        """Create CorrectionResult from dictionary."""
        return cls(
            original_segments=[LyricsSegment.from_dict(s) for s in data["original_segments"]],
            corrected_segments=[LyricsSegment.from_dict(s) for s in data["corrected_segments"]],
            corrected_text=data["corrected_text"],
            corrections=[WordCorrection.from_dict(c) for c in data["corrections"]],
            corrections_made=data["corrections_made"],
            confidence=data["confidence"],
            transcribed_text=data["transcribed_text"],
            reference_texts=data["reference_texts"],
            anchor_sequences=[AnchorSequence.from_dict(a) for a in data["anchor_sequences"]],
            gap_sequences=[GapSequence.from_dict(g) for g in data["gap_sequences"]],
            resized_segments=[LyricsSegment.from_dict(s) for s in data["resized_segments"]],
            metadata=data["metadata"],
        )
