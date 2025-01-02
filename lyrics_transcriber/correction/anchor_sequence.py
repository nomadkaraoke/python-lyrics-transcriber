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
        """Combine confidence and phrase quality"""
        return self.anchor.confidence * 0.6 + self.phrase_score.total_score * 0.4


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(self, min_sequence_length: int = 3, min_sources: int = 1, logger: Optional[logging.Logger] = None):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.logger = logger or logging.getLogger(__name__)
        self.phrase_analyzer = PhraseAnalyzer()

    def _clean_text(self, text: str) -> str:
        """Standardize text for comparison by:
        1. Converting to lowercase
        2. Removing punctuation
        3. Normalizing whitespace
        """
        # Remove punctuation and convert to lowercase
        text = re.sub(r"[^\w\s]", "", text.lower())
        # Normalize whitespace
        return " ".join(text.split())

    def _find_ngrams(self, words: List[str], n: int) -> List[Tuple[List[str], int]]:
        """Generate n-grams with their starting positions."""
        return [(words[i : i + n], i) for i in range(len(words) - n + 1)]

    def _find_matching_sources(self, ngram: List[str], ref_texts_clean: Dict[str, List[str]], n: int) -> Dict[str, int]:
        """Find matching positions of an n-gram in reference texts."""
        matching_sources: Dict[str, int] = {}

        for source, ref_words in ref_texts_clean.items():
            # Find all positions where this n-gram appears in the reference text
            matching_positions = []
            for ref_pos in range(len(ref_words) - n + 1):
                current_words = ref_words[ref_pos : ref_pos + n]
                if ngram == current_words:
                    matching_positions.append(ref_pos)

            # If we found matches and at least one hasn't been used before, use the first unused position
            for pos in matching_positions:
                if pos not in self.used_positions[source]:
                    matching_sources[source] = pos
                    self.used_positions[source].add(pos)
                    break

        return matching_sources

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

    def find_anchors(self, transcribed_text: str, reference_texts: Dict[str, str]) -> List[AnchorSequence]:
        """Find anchor sequences that appear in both transcribed and reference texts."""
        self.logger.debug("Starting anchor sequence search")

        # Reset used positions for new search
        self.used_positions = {source: set() for source in reference_texts.keys()}

        # Clean and split texts
        trans_words = self._clean_text(transcribed_text).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in reference_texts.items()}

        all_anchors: List[AnchorSequence] = []
        max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))

        # Try each possible sequence length
        for n in range(self.min_sequence_length, max_length + 1):
            self.logger.debug(f"Searching for {n}-word sequences")

            # Reset used positions for each sequence length
            self.used_positions = {source: set() for source in reference_texts.keys()}

            # Generate n-grams from transcribed text
            trans_ngrams = self._find_ngrams(trans_words, n)

            for ngram, trans_pos in trans_ngrams:
                matching_sources = self._find_matching_sources(ngram, ref_texts_clean, n)
                if len(matching_sources) >= self.min_sources:
                    confidence = len(matching_sources) / len(reference_texts)
                    anchor = AnchorSequence(
                        words=ngram, transcription_position=trans_pos, reference_positions=matching_sources, confidence=confidence
                    )
                    all_anchors.append(anchor)

        # Sort by position and confidence
        all_anchors.sort(key=lambda x: (x.transcription_position, -x.confidence, -x.length))
        return self._remove_overlapping_sequences(all_anchors)

    def _score_sequence(self, words: List[str], context: str) -> PhraseScore:
        """Score a sequence based on its phrase quality"""
        return self.phrase_analyzer.score_phrase(words, context)

    def _remove_overlapping_sequences(self, anchors: List[AnchorSequence], context: str) -> List[AnchorSequence]:
        """Remove overlapping sequences using phrase analysis"""
        if not anchors:
            return []

        # Score all anchors
        scored_anchors = [ScoredAnchor(anchor=anchor, phrase_score=self._score_sequence(anchor.words, context)) for anchor in anchors]

        # Sort by total score (combining confidence and phrase quality)
        scored_anchors.sort(key=lambda x: (-x.total_score, x.anchor.transcription_position))

        # Filter overlapping sequences
        filtered = []
        for scored_anchor in scored_anchors:
            overlaps = False
            for existing in filtered:
                if self._sequences_overlap(scored_anchor.anchor, existing):
                    overlaps = True
                    break
            if not overlaps:
                filtered.append(scored_anchor.anchor)

        return filtered

    def _sequences_overlap(self, a: AnchorSequence, b: AnchorSequence) -> bool:
        """Check if two sequences overlap"""
        a_end = a.transcription_position + a.length
        b_end = b.transcription_position + b.length
        return a.transcription_position < b_end and b.transcription_position < a_end
