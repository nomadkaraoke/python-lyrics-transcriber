from typing import Dict, List, Optional, Set, Tuple
from metaphone import doublemetaphone
from nltk.metrics import edit_distance

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class MetaphoneHandler(GapCorrectionHandler):
    """Handles corrections using Double Metaphone phonetic algorithm."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def _get_phonetic_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity between two words using Double Metaphone."""
        # Get phonetic codes
        code1_primary, code1_secondary = doublemetaphone(word1)
        code2_primary, code2_secondary = doublemetaphone(word2)

        # Handle empty codes
        if not code1_primary or not code2_primary:
            return 0.0

        # Compare primary codes
        primary_similarity = 1 - (edit_distance(code1_primary, code2_primary) / max(len(code1_primary), len(code2_primary)))

        # Compare secondary codes if available
        if code1_secondary and code2_secondary:
            secondary_similarity = 1 - (edit_distance(code1_secondary, code2_secondary) / max(len(code1_secondary), len(code2_secondary)))
            return max(primary_similarity, secondary_similarity)

        return primary_similarity

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
        """Check if we can handle this gap."""
        return bool(gap.reference_words)

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on phonetic similarity."""
        if not word.text.strip():
            return None

        best_match, similarity, matching_sources = self._find_best_match(word.text, gap.reference_words)

        if best_match and similarity >= self.similarity_threshold and best_match.lower() != word.text.lower():
            return WordCorrection(
                original_word=word.text,
                corrected_word=best_match,
                segment_index=segment_idx,
                word_index=current_word_idx,
                confidence=similarity,
                source=", ".join(matching_sources),
                reason=f"Metaphone phonetic similarity ({similarity:.2f})",
                alternatives={},
            )

        return None
