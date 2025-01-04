import logging
import difflib
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import string
from abc import ABC, abstractmethod

from ..transcribers.base_transcriber import TranscriptionData, LyricsSegment, Word, TranscriptionResult
from ..lyrics.base_lyrics_provider import LyricsData
from .base_strategy import CorrectionResult, CorrectionStrategy, WordCorrection
from .anchor_sequence import AnchorSequenceFinder, AnchorSequence, GapSequence, ScoredAnchor


@dataclass
class CorrectionEntry:
    """Stores information about potential corrections for a word."""

    sources: Set[str] = field(default_factory=set)
    frequencies: Dict[str, int] = field(default_factory=dict)
    cases: Dict[str, Dict[str, int]] = field(default_factory=lambda: {})
    original_form: str = ""  # Store original formatting

    def add_correction(self, correction: str, source: str, preserve_case: bool = False) -> None:
        """Add a correction instance."""
        self.sources.add(source)

        # Update frequency count
        if correction not in self.frequencies:
            self.frequencies[correction] = 0
        self.frequencies[correction] += 1

        # Track case variations if requested
        if preserve_case:
            if correction not in self.cases:
                self.cases[correction] = {}
            if correction not in self.cases[correction]:
                self.cases[correction][correction] = 0
            self.cases[correction][correction] += 1


class GapCorrectionHandler(ABC):
    """Base class for gap correction strategies."""

    @abstractmethod
    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Determine if this handler can process the given gap."""
        pass

    @abstractmethod
    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Process the gap and return a correction if possible."""
        pass


class ExactMatchHandler(GapCorrectionHandler):
    """Handles gaps where reference sources agree and have matching word counts."""

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        if not gap.reference_words:
            return False

        ref_words_lists = list(gap.reference_words.values())
        return all(len(words) == gap.length for words in ref_words_lists) and all(
            words == ref_words_lists[0] for words in ref_words_lists[1:]
        )

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        gap_pos = current_word_idx - gap.transcription_position
        correction = list(gap.reference_words.values())[0][gap_pos]

        if correction.lower() == word.text.lower():
            return None

        return WordCorrection(
            original_word=word.text,
            corrected_word=correction,
            segment_index=segment_idx,
            word_index=current_word_idx,
            confidence=1.0,
            source=", ".join(gap.reference_words.keys()),
            reason="All reference sources agree on correction",
            alternatives={},
        )


class DiffBasedCorrector(CorrectionStrategy):
    """Implements correction strategy focusing on gaps between anchor sequences."""

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        anchor_finder: Optional[AnchorSequenceFinder] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.anchor_finder = anchor_finder or AnchorSequenceFinder(logger=self.logger)
        self.handlers: List[GapCorrectionHandler] = [
            ExactMatchHandler(),
            # Add new handlers here
        ]

    def _preserve_formatting(self, original: str, new_word: str) -> str:
        """Preserve original word's formatting when applying correction."""
        # Find leading/trailing whitespace
        leading_space = " " if original != original.lstrip() else ""
        trailing_space = " " if original != original.rstrip() else ""
        return leading_space + new_word.strip() + trailing_space

    def _try_correct_word(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Attempt to correct a word using available handlers."""
        for handler in self.handlers:
            if handler.can_handle(gap, current_word_idx):
                correction = handler.handle(gap, word, current_word_idx, segment_idx)
                if correction:
                    return correction
        return None

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply corrections based on gap sequences between anchors."""
        self.logger.info("Starting gap-based correction")

        # Get primary transcription
        primary_transcription = sorted(transcription_results, key=lambda x: x.priority)[0].result
        transcribed_text = " ".join(" ".join(w.text for w in segment.words) for segment in primary_transcription.segments)
        reference_texts = {lyrics.source: lyrics.lyrics for lyrics in lyrics_results}

        # Find anchor sequences and gaps
        anchor_sequences = self.anchor_finder.find_anchors(transcribed_text, reference_texts)
        gap_sequences = self.anchor_finder.find_gaps(transcribed_text, anchor_sequences, reference_texts)

        corrections: List[WordCorrection] = []
        corrected_segments = []

        # Track current position in segments/words
        current_segment_idx = 0
        current_word_idx = 0
        corrections_made = 0

        for segment in primary_transcription.segments:
            corrected_words = []

            for word in segment.words:
                gap = next(
                    (g for g in gap_sequences if g.transcription_position <= current_word_idx < g.transcription_position + g.length), None
                )

                if gap:
                    correction = self._try_correct_word(gap, word, current_word_idx, current_segment_idx)
                    if correction:
                        corrected_text = self._preserve_formatting(word.text, correction.corrected_word)
                        corrected_word = Word(
                            text=corrected_text,
                            start_time=word.start_time,
                            end_time=word.end_time,
                            confidence=correction.confidence,
                        )
                        corrected_words.append(corrected_word)
                        corrections.append(correction)
                        gap.corrections.append(correction)
                        corrections_made += 1
                        current_word_idx += 1
                        continue

                # If no correction made, keep original word
                corrected_words.append(word)
                current_word_idx += 1

            # Create corrected segment
            corrected_segment = LyricsSegment(
                text=" ".join(w.text for w in corrected_words),
                words=corrected_words,
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
            corrected_segments.append(corrected_segment)
            current_segment_idx += 1

        # Calculate correction ratio
        total_words = sum(len(segment.words) for segment in corrected_segments)
        correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

        return CorrectionResult(
            original_segments=primary_transcription.segments,
            corrected_segments=corrected_segments,
            corrected_text="\n".join(segment.text for segment in corrected_segments) + "\n",
            corrections=corrections,
            corrections_made=corrections_made,
            confidence=correction_ratio,
            transcribed_text=transcribed_text,
            reference_texts=reference_texts,
            anchor_sequences=anchor_sequences,
            gap_sequences=gap_sequences,
            metadata={
                "correction_strategy": "gap_based",
                "anchor_sequences_count": len(anchor_sequences),
                "gap_sequences_count": len(gap_sequences),
                "total_words": total_words,
                "correction_ratio": correction_ratio,
            },
        )
