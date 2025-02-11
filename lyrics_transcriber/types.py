from dataclasses import dataclass, asdict, field, fields
from typing import Any, Dict, List, Optional, Set, Protocol, Tuple
from enum import Enum


@dataclass
class Word:
    """Represents a single word with its timing (in seconds) and confidence information."""

    id: str  # New: Unique identifier for each word
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None
    # New: Track if this word was created during correction
    created_during_correction: bool = False

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
            id=data["id"],
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            confidence=data.get("confidence"),  # Use get() since confidence is optional
            created_during_correction=data.get("created_during_correction", False),
        )


@dataclass
class LyricsSegment:
    """Represents a segment/line of lyrics with timing information in seconds."""

    id: str  # New: Unique identifier for each segment
    text: str
    words: List[Word]
    start_time: float
    end_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert LyricsSegment to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "words": [word.to_dict() for word in self.words],
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LyricsSegment":
        """Create LyricsSegment from dictionary."""
        return cls(
            id=data["id"],
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
    provider_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LyricsMetadata":
        """Create LyricsMetadata from dictionary."""
        return cls(
            source=data["source"],
            track_name=data["track_name"],
            artist_names=data["artist_names"],
            album_name=data.get("album_name"),
            duration_ms=data.get("duration_ms"),
            explicit=data.get("explicit"),
            language=data.get("language"),
            is_synced=data.get("is_synced", False),
            lyrics_provider=data.get("lyrics_provider"),
            lyrics_provider_id=data.get("lyrics_provider_id"),
            provider_metadata=data.get("provider_metadata", {}),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LyricsData":
        """Create LyricsData from dictionary."""
        return cls(
            lyrics=data["lyrics"],
            segments=[LyricsSegment.from_dict(s) for s in data["segments"]],
            metadata=LyricsMetadata.from_dict(data["metadata"]),
            source=data["source"],
        )


@dataclass
class WordCorrection:
    """Details about a single word correction."""

    original_word: str
    corrected_word: str  # Empty string indicates word should be deleted
    original_position: int
    source: str  # e.g., "spotify", "genius"
    reason: str  # e.g., "matched_in_3_sources", "high_confidence_match"
    segment_index: int = 0  # Default to 0 since it's often not needed
    confidence: Optional[float] = None
    alternatives: Dict[str, int] = field(default_factory=dict)  # Other possible corrections and their occurrence counts
    is_deletion: bool = False  # New field to explicitly mark deletions
    # New fields for handling word splits
    split_index: Optional[int] = None  # Position in the split sequence (0-based)
    split_total: Optional[int] = None  # Total number of words in split
    # New field to track position after corrections
    corrected_position: Optional[int] = None
    # New fields to match TypeScript interface
    reference_positions: Optional[Dict[str, int]] = None  # Maps source to position in reference text
    length: int = 1  # Default to 1 for single-word corrections
    handler: Optional[str] = None  # Name of the correction handler that created this correction
    # New ID fields for tracking word identity through corrections
    word_id: Optional[str] = None  # ID of the original word being corrected
    corrected_word_id: Optional[str] = None  # ID of the new word after correction

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordCorrection":
        """Create WordCorrection from dictionary."""
        # Filter out any keys that aren't part of the dataclass
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


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

    words: List[str]  # The text of the words in the transcription
    transcribed_words: List[Word]  # The actual Word objects from the transcription
    transcription_position: int  # Starting position in transcribed text
    reference_positions: Dict[str, int]  # Source -> position mapping
    reference_words: Dict[str, List[Word]]  # Source -> list of Word objects from reference
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
            "transcribed_words": [w.to_dict() for w in self.transcribed_words],
            "text": self.text,
            "length": self.length,
            "transcription_position": self.transcription_position,
            "reference_positions": self.reference_positions,
            "reference_words": {source: [w.to_dict() for w in words] for source, words in self.reference_words.items()},
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnchorSequence":
        """Create AnchorSequence from dictionary."""
        return cls(
            words=data["words"],
            transcribed_words=[Word.from_dict(w) for w in data["transcribed_words"]],
            transcription_position=data["transcription_position"],
            reference_positions=data["reference_positions"],
            reference_words={source: [Word.from_dict(w) for w in words] for source, words in data["reference_words"].items()},
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
    transcribed_words: List[Word]  # The actual Word objects from the transcription
    transcription_position: int  # Original starting position in transcription
    preceding_anchor: Optional[AnchorSequence]
    following_anchor: Optional[AnchorSequence]
    reference_words: Dict[str, List[Word]]  # Source -> list of Word objects from reference
    reference_words_original: Dict[str, List[Word]]  # Original reference words before any corrections
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
            "transcribed_words": [w.to_dict() for w in self.transcribed_words],
            "text": self.text,
            "length": self.length,
            "transcription_position": self.transcription_position,
            "preceding_anchor": self.preceding_anchor.to_dict() if self.preceding_anchor else None,
            "following_anchor": self.following_anchor.to_dict() if self.following_anchor else None,
            "reference_words": {source: [w.to_dict() for w in words] for source, words in self.reference_words.items()},
            "reference_words_original": {source: [w.to_dict() for w in words] for source, words in self.reference_words_original.items()},
            "corrections": [c.to_dict() for c in self.corrections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GapSequence":
        """Create GapSequence from dictionary."""
        gap = cls(
            words=tuple(data["words"]),
            transcribed_words=[Word.from_dict(w) for w in data["transcribed_words"]],
            transcription_position=data["transcription_position"],
            preceding_anchor=AnchorSequence.from_dict(data["preceding_anchor"]) if data["preceding_anchor"] else None,
            following_anchor=AnchorSequence.from_dict(data["following_anchor"]) if data["following_anchor"] else None,
            reference_words={source: [Word.from_dict(w) for w in words] for source, words in data["reference_words"].items()},
            reference_words_original={
                source: [Word.from_dict(w) for w in words] for source, words in data["reference_words_original"].items()
            },
        )
        # Add any corrections from the data
        if "corrections" in data:
            for correction_data in data["corrections"]:
                gap.add_correction(WordCorrection.from_dict(correction_data))
        return gap


@dataclass
class CorrectionStep:
    """Represents a single correction operation with enough info to replay/undo."""

    handler_name: str
    affected_word_ids: List[str]  # IDs of words modified/deleted
    affected_segment_ids: List[str]  # IDs of segments modified
    corrections: List[WordCorrection]
    # State before and after for affected segments
    segments_before: List[LyricsSegment]
    segments_after: List[LyricsSegment]
    # For splits/merges
    created_word_ids: List[str] = field(default_factory=list)  # New words created
    deleted_word_ids: List[str] = field(default_factory=list)  # Words removed

    def to_dict(self) -> Dict[str, Any]:
        """Convert CorrectionStep to dictionary for JSON serialization."""
        return {
            "handler_name": self.handler_name,
            "affected_word_ids": self.affected_word_ids,
            "affected_segment_ids": self.affected_segment_ids,
            "corrections": [c.to_dict() for c in self.corrections],
            "segments_before": [s.to_dict() for s in self.segments_before],
            "segments_after": [s.to_dict() for s in self.segments_after],
            "created_word_ids": self.created_word_ids,
            "deleted_word_ids": self.deleted_word_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrectionStep":
        """Create CorrectionStep from dictionary."""
        return cls(
            handler_name=data["handler_name"],
            affected_word_ids=data["affected_word_ids"],
            affected_segment_ids=data["affected_segment_ids"],
            corrections=[WordCorrection.from_dict(c) for c in data["corrections"]],
            segments_before=[LyricsSegment.from_dict(s) for s in data["segments_before"]],
            segments_after=[LyricsSegment.from_dict(s) for s in data["segments_after"]],
            created_word_ids=data["created_word_ids"],
            deleted_word_ids=data["deleted_word_ids"],
        )


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
    reference_lyrics: Dict[str, LyricsData]  # Maps source to LyricsData
    anchor_sequences: List[AnchorSequence]
    gap_sequences: List[GapSequence]
    resized_segments: List[LyricsSegment]

    metadata: Dict[str, Any]

    # Correction history
    correction_steps: List[CorrectionStep]
    word_id_map: Dict[str, str]  # Maps original word IDs to corrected word IDs
    segment_id_map: Dict[str, str]  # Maps original segment IDs to corrected segment IDs

    def to_dict(self) -> Dict[str, Any]:
        """Convert the correction result to a JSON-serializable dictionary."""
        return {
            "transcribed_text": self.transcribed_text,
            "original_segments": [s.to_dict() for s in self.original_segments],
            "reference_lyrics": {source: lyrics.to_dict() for source, lyrics in self.reference_lyrics.items()},
            "anchor_sequences": [a.to_dict() for a in self.anchor_sequences],
            "gap_sequences": [g.to_dict() for g in self.gap_sequences],
            "resized_segments": [s.to_dict() for s in self.resized_segments],
            "corrected_text": self.corrected_text,
            "corrections_made": self.corrections_made,
            "confidence": self.confidence,
            "corrections": [c.to_dict() for c in self.corrections],
            "corrected_segments": [s.to_dict() for s in self.corrected_segments],
            "metadata": self.metadata,
            "correction_steps": [step.to_dict() for step in self.correction_steps],
            "word_id_map": self.word_id_map,
            "segment_id_map": self.segment_id_map,
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
            reference_lyrics={source: LyricsData.from_dict(lyrics) for source, lyrics in data["reference_lyrics"].items()},
            anchor_sequences=[AnchorSequence.from_dict(a) for a in data["anchor_sequences"]],
            gap_sequences=[GapSequence.from_dict(g) for g in data["gap_sequences"]],
            resized_segments=[LyricsSegment.from_dict(s) for s in data["resized_segments"]],
            metadata=data["metadata"],
            correction_steps=[CorrectionStep.from_dict(step) for step in data["correction_steps"]],
            word_id_map=data["word_id_map"],
            segment_id_map=data["segment_id_map"],
        )
