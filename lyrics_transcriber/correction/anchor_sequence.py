from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set
import logging


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


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(self, min_sequence_length: int = 3, min_sources: int = 1, logger: Optional[logging.Logger] = None):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.logger = logger or logging.getLogger(__name__)

    def _clean_text(self, text: str) -> str:
        """Standardize text for comparison."""
        return " ".join(text.lower().split())

    def _find_ngrams(self, words: List[str], n: int) -> List[Tuple[List[str], int]]:
        """Generate n-grams with their starting positions."""
        return [(words[i : i + n], i) for i in range(len(words) - n + 1)]

    def _find_matching_sources(self, ngram: List[str], ref_texts_clean: Dict[str, List[str]], n: int) -> Dict[str, int]:
        """Find matching positions of an n-gram in reference texts."""
        matching_sources: Dict[str, int] = {}
        for source, ref_words in ref_texts_clean.items():
            for ref_pos in range(len(ref_words) - n + 1):
                if ngram == ref_words[ref_pos : ref_pos + n]:
                    matching_sources[source] = ref_pos
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

        # Clean and split texts
        trans_words = self._clean_text(transcribed_text).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in reference_texts.items()}

        anchors: List[AnchorSequence] = []
        max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))

        # Try different sequence lengths, starting with longest
        for n in range(max_length, self.min_sequence_length - 1, -1):
            self.logger.debug(f"Searching for {n}-word sequences")

            # Generate n-grams from transcribed text
            trans_ngrams = self._find_ngrams(trans_words, n)

            for ngram, trans_pos in trans_ngrams:
                matching_sources = self._find_matching_sources(ngram, ref_texts_clean, n)
                anchor = self._create_anchor(ngram, trans_pos, matching_sources, len(reference_texts))
                if anchor:
                    anchors.append(anchor)

        # Sort anchors by position
        anchors.sort(key=lambda x: x.transcription_position)
        return self._remove_overlapping_sequences(anchors)

    def _remove_overlapping_sequences(self, anchors: List[AnchorSequence]) -> List[AnchorSequence]:
        """Remove overlapping sequences, preferring longer/higher confidence ones."""
        if not anchors:
            return []

        filtered = [anchors[0]]

        for anchor in anchors[1:]:
            prev = filtered[-1]
            prev_end = prev.transcription_position + prev.length

            # If this anchor doesn't overlap with the previous one, keep it
            if anchor.transcription_position >= prev_end:
                filtered.append(anchor)
                continue

            # If they overlap, keep the better one
            score_prev = prev.length * prev.confidence
            score_curr = anchor.length * anchor.confidence

            if score_curr > score_prev:
                filtered[-1] = anchor

        return filtered
