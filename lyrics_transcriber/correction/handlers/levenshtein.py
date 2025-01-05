import string
from typing import Dict, List, Optional, Set, Tuple
import Levenshtein

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class LevenshteinSimilarityHandler(GapCorrectionHandler):
    """Handles corrections based on Levenshtein (edit distance) similarity between words."""

    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold

    def _clean_word(self, word: str) -> str:
        """Remove punctuation and standardize for comparison."""
        return word.strip().lower().strip(string.punctuation)

    def _get_string_similarity(self, word1: str, word2: str) -> float:
        """Calculate string similarity using Levenshtein ratio."""
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
            similarity = self._get_string_similarity(word, ref_word)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = ref_word
                matching_sources = {source for source, words in reference_words.items() if ref_word in words}

        return best_match, best_similarity, matching_sources

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap - we'll try if there are reference words."""
        return bool(gap.reference_words)

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on string similarity."""
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
                reason=f"String similarity ({similarity:.2f})",
                alternatives={},
            )

        return None
