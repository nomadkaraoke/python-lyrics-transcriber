from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set
import logging
from .text_analysis import PhraseAnalyzer, PhraseScore
from .text_utils import clean_text
from tqdm import tqdm


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
    def words(self) -> List[str]:
        """Get the words from the underlying anchor."""
        return self.anchor.words

    @property
    def text(self) -> str:
        """Get the text from the underlying anchor."""
        return self.anchor.text

    @property
    def confidence(self) -> float:
        """Get the confidence from the underlying anchor."""
        return self.anchor.confidence

    @property
    def transcription_position(self) -> int:
        """Get the transcription position from the underlying anchor."""
        return self.anchor.transcription_position

    @property
    def reference_positions(self) -> Dict[str, int]:
        """Get the reference positions from the underlying anchor."""
        return self.anchor.reference_positions

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
            **self.anchor.to_dict(),  # Include all AnchorSequence fields
            "phrase_score": {
                "phrase_type": self.phrase_score.phrase_type.value,
                "natural_break_score": self.phrase_score.natural_break_score,
                "length_score": self.phrase_score.length_score,
                "total_score": self.phrase_score.total_score,
            },
            "total_score": self.total_score,
        }


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(self, min_sequence_length: int = 3, min_sources: int = 1, logger: Optional[logging.Logger] = None):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.logger = logger or logging.getLogger(__name__)
        self.phrase_analyzer = PhraseAnalyzer(logger=self.logger)
        self.used_positions = {}  # Initialize empty dict for used positions

    def _clean_text(self, text: str) -> str:
        """Clean text by removing punctuation and normalizing whitespace."""
        # self.logger.debug(f"_clean_text called with text length: {len(text)}")
        return clean_text(text)

    def _find_ngrams(self, words: List[str], n: int) -> List[Tuple[List[str], int]]:
        """Generate n-grams with their starting positions."""
        # self.logger.debug(f"_find_ngrams called with {len(words)} words, n={n}")
        return [(words[i : i + n], i) for i in range(len(words) - n + 1)]

    def _find_matching_sources(self, ngram: List[str], references: Dict[str, List[str]], n: int) -> Dict[str, int]:
        """Find which sources contain the given n-gram and at what positions."""
        # self.logger.debug(f"_find_matching_sources called for ngram: '{' '.join(ngram)}'")
        matches = {}
        all_positions = {source: [] for source in references}

        # First, find all positions in each source
        for source, words in references.items():
            for i in range(len(words) - n + 1):
                if words[i : i + n] == ngram:
                    all_positions[source].append(i)

        # Then, try to find an unused position for each source
        for source, positions in all_positions.items():
            used = self.used_positions.get(source, set())
            # Try each position in order
            for pos in positions:
                if pos not in used:
                    matches[source] = pos
                    break

        return matches

    def _filter_used_positions(self, matches: Dict[str, int]) -> Dict[str, int]:
        """Filter out positions that have already been used.

        Args:
            matches: Dict mapping source IDs to positions

        Returns:
            Dict mapping source IDs to unused positions
        """
        self.logger.debug(f"_filter_used_positions called with {len(matches)} matches")
        return {source: pos for source, pos in matches.items() if pos not in self.used_positions.get(source, set())}

    def _create_anchor(
        self, ngram: List[str], trans_pos: int, matching_sources: Dict[str, int], total_sources: int
    ) -> Optional[AnchorSequence]:
        """Create an anchor sequence if it meets the minimum sources requirement."""
        self.logger.debug(f"_create_anchor called for ngram: '{' '.join(ngram)}' at position {trans_pos}")
        if len(matching_sources) >= self.min_sources:
            confidence = len(matching_sources) / total_sources
            anchor = AnchorSequence(
                words=ngram, transcription_position=trans_pos, reference_positions=matching_sources, confidence=confidence
            )
            self.logger.debug(f"Found anchor sequence: '{' '.join(ngram)}' (confidence: {confidence:.2f})")
            return anchor
        return None

    def find_anchors(self, transcribed: str, references: Dict[str, str]) -> List[ScoredAnchor]:
        """Find anchor sequences that appear in both transcription and references.

        Returns:
            List of ScoredAnchor objects containing both the anchor sequences and their quality scores.
        """
        self.logger.info(f"Finding anchor sequences for transcription with length {len(transcribed)}")

        self.logger.info(f"Cleaning and splitting texts")
        # Clean and split texts
        trans_words = self._clean_text(transcribed).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in references.items()}

        candidate_anchors = []
        max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))

        self.logger.info(f"Checking sequence lengths")
        for n in tqdm(range(max_length, self.min_sequence_length - 1, -1), desc="Checking sequence lengths"):
            # Reset used positions for each n-gram length
            self.used_positions = {source: set() for source in references.keys()}
            used_trans_positions = set()

            # Try each position in the transcribed text multiple times
            # to catch repeated phrases
            found_new_match = True
            while found_new_match:
                found_new_match = False

                # Generate n-grams from transcribed text
                trans_ngrams = self._find_ngrams(trans_words, n)

                for ngram, trans_pos in trans_ngrams:
                    # Skip if we've already used this transcription position
                    if trans_pos in used_trans_positions:
                        continue

                    matches = self._find_matching_sources(ngram, ref_texts_clean, n)
                    if len(matches) >= self.min_sources:
                        # Mark positions as used
                        for source, pos in matches.items():
                            self.used_positions[source].add(pos)
                        used_trans_positions.add(trans_pos)

                        anchor = AnchorSequence(ngram, trans_pos, matches, len(matches) / len(references))
                        candidate_anchors.append(anchor)
                        found_new_match = True
                        break  # Start over to try finding more matches

        self.logger.info(f"Found {len(candidate_anchors)} candidate anchors")
        filtered_anchors = self._remove_overlapping_sequences(candidate_anchors, transcribed)
        return filtered_anchors  # Now returns ScoredAnchor objects directly

    def _score_sequence(self, words: List[str], context: str) -> PhraseScore:
        """Score a sequence based on its phrase quality"""
        self.logger.debug(f"_score_sequence called for: '{' '.join(words)}'")
        return self.phrase_analyzer.score_phrase(words, context)

    def _score_anchor(self, anchor: AnchorSequence, context: str) -> ScoredAnchor:
        """Score an anchor sequence based on phrase quality and line breaks.

        Args:
            anchor: The anchor sequence to score
            context: The original transcribed text
        """
        # Let phrase_analyzer handle all scoring including line breaks
        phrase_score = self.phrase_analyzer.score_phrase(anchor.words, context)

        # self.logger.debug(f"_score_anchor called for sequence: '{anchor.text}'")
        return ScoredAnchor(anchor=anchor, phrase_score=phrase_score)

    def _get_sequence_priority(self, scored_anchor: ScoredAnchor) -> Tuple[float, float, float, int, int]:
        """Get priority tuple for sorting sequences.

        Returns tuple of:
        - Number of sources matched (higher is better)
        - Break score (higher is better)
        - Total score (higher is better)
        - Negative length (shorter is better)
        - Negative position (earlier is better)

        Position bonus: Add 1.0 to total score for sequences at position 0
        """
        # self.logger.debug(f"_get_sequence_priority called for anchor: '{scored_anchor.anchor.text}'")
        position_bonus = 1.0 if scored_anchor.anchor.transcription_position == 0 else 0.0
        return (
            len(scored_anchor.anchor.reference_positions),  # More sources is better
            scored_anchor.phrase_score.natural_break_score,
            scored_anchor.phrase_score.total_score + position_bonus,  # Add bonus for position 0
            -len(scored_anchor.anchor.words),  # Shorter sequences preferred
            -scored_anchor.anchor.transcription_position,  # Earlier positions preferred
        )

    def _sequences_overlap(self, seq1: AnchorSequence, seq2: AnchorSequence) -> bool:
        """Check if two sequences overlap in either transcription or references.

        Args:
            seq1: First sequence
            seq2: Second sequence

        Returns:
            True if sequences overlap in transcription or share any reference positions
        """
        # Check transcription overlap
        seq1_trans_range = range(seq1.transcription_position, seq1.transcription_position + len(seq1.words))
        seq2_trans_range = range(seq2.transcription_position, seq2.transcription_position + len(seq2.words))
        trans_overlap = bool(set(seq1_trans_range) & set(seq2_trans_range))

        # Check reference overlap - only consider positions in shared sources
        shared_sources = set(seq1.reference_positions.keys()) & set(seq2.reference_positions.keys())
        ref_overlap = any(seq1.reference_positions[source] == seq2.reference_positions[source] for source in shared_sources)

        # self.logger.debug(f"Checking overlap between '{seq1.text}' and '{seq2.text}'")
        return trans_overlap or ref_overlap

    def _remove_overlapping_sequences(self, anchors: List[AnchorSequence], context: str) -> List[ScoredAnchor]:
        """Remove overlapping sequences using phrase analysis."""
        if not anchors:
            return []

        self.logger.info(f"Scoring {len(anchors)} anchors")

        # Score all anchors with progress bar
        scored_anchors = [self._score_anchor(anchor, context) for anchor in tqdm(anchors, desc="Scoring anchors")]
        scored_anchors.sort(key=self._get_sequence_priority, reverse=True)

        self.logger.info(f"Filtering {len(scored_anchors)} overlapping sequences")

        filtered_scored = []
        # Filter with progress bar
        for scored_anchor in tqdm(scored_anchors, desc="Filtering overlaps"):
            overlaps = False
            for existing in filtered_scored:
                if self._sequences_overlap(scored_anchor.anchor, existing.anchor):
                    overlaps = True
                    break

            if not overlaps:
                filtered_scored.append(scored_anchor)

        self.logger.info(f"Filtered down to {len(filtered_scored)} non-overlapping anchors")
        return filtered_scored
