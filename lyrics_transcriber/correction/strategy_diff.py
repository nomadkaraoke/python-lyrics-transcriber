import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import string
from abc import ABC, abstractmethod
import Levenshtein

from lyrics_transcriber.types import (
    LyricsData,
    LyricsSegment,
    Word,
    TranscriptionResult,
    CorrectionResult,
    WordCorrection,
    GapSequence,
)
from lyrics_transcriber.correction.base_strategy import CorrectionStrategy
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder


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


class PhoneticSimilarityHandler(GapCorrectionHandler):
    """Handles corrections based on phonetic similarity between words."""

    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold

    def _clean_word(self, word: str) -> str:
        """Remove punctuation and standardize for comparison."""
        return word.strip().lower().strip(string.punctuation)

    def _get_phonetic_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity between two words."""
        # Clean words
        w1, w2 = self._clean_word(word1), self._clean_word(word2)
        if not w1 or not w2:
            return 0.0

        # Calculate Levenshtein ratio
        similarity = Levenshtein.ratio(w1, w2)

        # Boost similarity for words starting with the same letter
        if w1[0] == w2[0]:
            similarity = (similarity + 1) / 2
        else:
            # Penalize words starting with different letters
            similarity = similarity * 0.9

        # Boost for similar length words
        length_ratio = min(len(w1), len(w2)) / max(len(w1), len(w2))
        similarity = (similarity + length_ratio) / 2

        return similarity

    def _find_best_match(self, word: str, reference_words: Dict[str, List[str]]) -> Tuple[Optional[str], float, Set[str]]:
        """Find the best matching reference word across all sources."""
        best_match = None
        best_similarity = 0.0
        matching_sources = set()

        # Get unique reference words
        all_ref_words = {w for words in reference_words.values() for w in words}

        for ref_word in all_ref_words:
            similarity = self._get_phonetic_similarity(word, ref_word)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = ref_word
                matching_sources = {source for source, words in reference_words.items() if ref_word in words}

        return best_match, best_similarity, matching_sources

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap - we'll try if there are reference words."""
        return bool(gap.reference_words)

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on phonetic similarity."""
        # Skip if word is empty or just punctuation
        if not word.text.strip():
            return None

        # Find best matching reference word
        best_match, similarity, matching_sources = self._find_best_match(word.text, gap.reference_words)

        # Return correction if we found a good match
        if best_match and similarity >= self.similarity_threshold and best_match.lower() != word.text.lower():

            return WordCorrection(
                original_word=word.text,
                corrected_word=best_match,
                segment_index=segment_idx,
                word_index=current_word_idx,
                confidence=similarity,
                source=", ".join(matching_sources),
                reason=f"Phonetic similarity ({similarity:.2f})",
                alternatives={},  # Could add other close matches here
            )

        return None


class MultiWordSequenceHandler(GapCorrectionHandler):
    """Handles corrections by matching sequences of words."""

    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold
        self.phonetic_matcher = PhoneticSimilarityHandler(similarity_threshold)

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap."""
        if not gap.reference_words:
            return False

        # Don't handle cases where sources disagree
        ref_words_lists = list(gap.reference_words.values())
        if not all(words == ref_words_lists[0] for words in ref_words_lists[1:]):
            print("Sources disagree on reference words")
            return False

        # Don't handle cases where reference has different length than gap
        if any(len(words) != len(gap.words) for words in gap.reference_words.values()):
            print("Reference length doesn't match gap length")
            return False

        return True

    def _align_sequences(self, gap_words: List[str], ref_words: List[str]) -> List[Tuple[Optional[str], Optional[str], float]]:
        """Align two sequences of words and return matches with confidence scores."""
        alignments = []

        print(f"\nDebug: Aligning sequences")
        print(f"Gap words: {gap_words}")
        print(f"Reference words: {ref_words}")

        # For each gap word, try to find the best match in the reference words
        for i, gap_word in enumerate(gap_words):
            best_match = None
            best_score = 0.0

            # First, try exact position match if available
            if i < len(ref_words):
                ref_word = ref_words[i]
                # Use a base position confidence even if words aren't similar
                position_score = 0.7  # Base confidence for position match

                # If words are similar, boost the confidence
                similarity = self.phonetic_matcher._get_phonetic_similarity(gap_word, ref_word)
                score = max(position_score, similarity)

                print(f"Position match attempt: '{gap_word}' vs '{ref_word}' (score: {score:.2f})")

                if score >= self.similarity_threshold:
                    best_match = ref_word
                    best_score = score

            alignments.append((gap_word, best_match, best_score))
            print(f"Final alignment for '{gap_word}': {best_match} (score: {best_score:.2f})")

        return alignments

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on sequence alignment."""
        if not word.text.strip():
            return None

        gap_pos = current_word_idx - gap.transcription_position
        print(f"\nDebug: Processing word '{word.text}' at position {gap_pos}")

        best_alignment = None
        best_confidence = 0.0
        best_sources = set()

        for source, ref_words in gap.reference_words.items():
            print(f"\nTrying source: {source}")
            alignments = self._align_sequences(gap.words, ref_words)

            if gap_pos < len(alignments):
                gap_word, correction, confidence = alignments[gap_pos]
                print(f"Alignment result: {gap_word} -> {correction} (confidence: {confidence:.2f})")

                if correction and correction.lower() == word.text.lower():
                    print("Skipping exact match")
                    return None

                if correction and confidence > best_confidence:
                    best_alignment = correction
                    best_confidence = confidence
                    best_sources = {source}
                elif correction and confidence == best_confidence:
                    best_sources.add(source)

        if best_alignment and best_confidence >= self.similarity_threshold:
            print(f"Making correction: {word.text} -> {best_alignment}")
            return WordCorrection(
                original_word=word.text,
                corrected_word=best_alignment,
                segment_index=segment_idx,
                word_index=current_word_idx,
                confidence=best_confidence,
                source=", ".join(best_sources),
                reason=f"Sequence alignment ({best_confidence:.2f})",
                alternatives={},
            )

        print("No correction made")
        return None


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
            MultiWordSequenceHandler(),
            PhoneticSimilarityHandler(),
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
