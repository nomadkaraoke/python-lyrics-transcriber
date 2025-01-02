from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set
import logging
import re
from .text_analysis import PhraseAnalyzer, PhraseScore


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


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(self, min_sequence_length: int = 3, min_sources: int = 1, logger: Optional[logging.Logger] = None):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.logger = logger or logging.getLogger(__name__)
        self.phrase_analyzer = PhraseAnalyzer()
        self.used_positions = {}  # Initialize empty dict for used positions

    def _clean_text(self, text: str) -> str:
        """Clean text by removing punctuation and normalizing whitespace.

        Args:
            text: Text to clean

        Returns:
            Cleaned text with:
            - All text converted to lowercase
            - All punctuation removed
            - Multiple spaces/whitespace collapsed to single space
            - Leading/trailing whitespace removed
        """
        # Convert to lowercase
        text = text.lower()

        # Remove punctuation
        text = re.sub(r"[^\w\s]", "", text)

        # Normalize whitespace (collapse multiple spaces, remove leading/trailing)
        text = " ".join(text.split())

        return text

    def _find_ngrams(self, words: List[str], n: int) -> List[Tuple[List[str], int]]:
        """Generate n-grams with their starting positions."""
        return [(words[i : i + n], i) for i in range(len(words) - n + 1)]

    def _find_matching_sources(self, ngram: List[str], references: Dict[str, List[str]], n: int) -> Dict[str, int]:
        """Find which sources contain the given n-gram and at what positions."""
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
        return {source: pos for source, pos in matches.items() if pos not in self.used_positions.get(source, set())}

    def _create_anchor(
        self, ngram: List[str], trans_pos: int, matching_sources: Dict[str, int], total_sources: int
    ) -> Optional[AnchorSequence]:
        """Create an anchor sequence if it meets the minimum sources requirement."""
        if len(matching_sources) >= self.min_sources:
            confidence = len(matching_sources) / total_sources
            anchor = AnchorSequence(
                words=ngram, transcription_position=trans_pos, reference_positions=matching_sources, confidence=confidence
            )
            self.logger.debug(f"Found anchor sequence: '{' '.join(ngram)}' (confidence: {confidence:.2f})")
            return anchor
        return None

    def find_anchors(self, transcribed: str, references: Dict[str, str]) -> List[AnchorSequence]:
        """Find anchor sequences that appear in both transcription and references."""
        # Clean and split texts
        trans_words = self._clean_text(transcribed).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in references.items()}

        candidate_anchors = []
        max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))

        # Try each possible sequence length, starting with longest
        for n in range(max_length, self.min_sequence_length - 1, -1):
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

        # Use existing method to remove overlapping sequences
        return self._remove_overlapping_sequences(candidate_anchors, transcribed)

    def _score_sequence(self, words: List[str], context: str) -> PhraseScore:
        """Score a sequence based on its phrase quality"""
        return self.phrase_analyzer.score_phrase(words, context)

    def _score_anchor(self, anchor: AnchorSequence, context: str) -> ScoredAnchor:
        """Score an anchor sequence based on phrase quality and line breaks.

        Args:
            anchor: The anchor sequence to score
            context: The original transcribed text
        """
        # Check if sequence crosses a line break
        sequence_text = " ".join(anchor.words)
        if sequence_text in context.replace("\n", " "):
            # Sequence appears as-is in the text (doesn't cross line breaks)
            phrase_score = self.phrase_analyzer.score_phrase(anchor.words, context)
        else:
            # Sequence crosses line breaks - penalize heavily
            phrase_score = self.phrase_analyzer.score_phrase(anchor.words, context)
            phrase_score.natural_break_score = 0.0  # Penalize for crossing line break

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

        return trans_overlap or ref_overlap

    def _remove_overlapping_sequences(self, anchors: List[AnchorSequence], context: str) -> List[AnchorSequence]:
        """Remove overlapping sequences using phrase analysis.

        Args:
            anchors: List of anchor sequences to filter
            context: The original transcribed text for phrase analysis
        """
        if not anchors:
            return []

        # Score all anchors
        scored_anchors = [self._score_anchor(anchor, context) for anchor in anchors]

        # Sort by priority
        scored_anchors.sort(key=self._get_sequence_priority, reverse=True)

        # Filter overlapping sequences
        filtered_scored = []
        for scored_anchor in scored_anchors:
            # Check if this sequence overlaps with any existing ones
            overlaps = False
            for existing in filtered_scored:
                if self._sequences_overlap(scored_anchor.anchor, existing.anchor):
                    overlaps = True
                    break

            if not overlaps:
                filtered_scored.append(scored_anchor)

        # Return just the anchor sequences
        return [scored.anchor for scored in filtered_scored]
