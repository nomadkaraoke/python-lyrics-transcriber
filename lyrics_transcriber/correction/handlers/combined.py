from typing import Dict, List, Optional, Set, Tuple

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.metaphone import MetaphoneHandler
from lyrics_transcriber.correction.handlers.semantic import SemanticHandler


class CombinedHandler(GapCorrectionHandler):
    """Combines phonetic and semantic matching with weighted scoring."""

    def __init__(
        self,
        phonetic_weight: float = 0.6,
        semantic_weight: float = 0.4,
        combined_threshold: float = 0.5,
        phonetic_threshold: float = 0.4,
        semantic_threshold: float = 0.3,
    ):
        self.phonetic_matcher = MetaphoneHandler()
        self.semantic_matcher = SemanticHandler()
        self.phonetic_weight = phonetic_weight
        self.semantic_weight = semantic_weight
        self.combined_threshold = combined_threshold
        self.phonetic_threshold = phonetic_threshold
        self.semantic_threshold = semantic_threshold

    def _find_best_match(self, word: str, reference_words: Dict[str, List[str]]) -> Tuple[Optional[str], float, float, float, Set[str]]:
        """Find the best matching reference word using combined scoring."""
        best_match = None
        best_combined_score = 0.0
        best_phonetic_score = 0.0
        best_semantic_score = 0.0
        matching_sources = set()

        # Get unique reference words
        all_ref_words = {w for words in reference_words.values() for w in words}

        for ref_word in all_ref_words:
            # Get phonetic similarity
            phonetic_score = self.phonetic_matcher._get_phonetic_similarity(word, ref_word)

            # Get semantic similarity
            semantic_score = self.semantic_matcher._get_semantic_similarity(word, ref_word)

            # Calculate combined score
            combined_score = (phonetic_score * self.phonetic_weight) + (semantic_score * self.semantic_weight)

            # Check if this is a better match
            if (
                combined_score > best_combined_score
                and phonetic_score >= self.phonetic_threshold
                and semantic_score >= self.semantic_threshold
            ):
                best_combined_score = combined_score
                best_phonetic_score = phonetic_score
                best_semantic_score = semantic_score
                best_match = ref_word
                matching_sources = {source for source, words in reference_words.items() if ref_word in words}

        return best_match, best_phonetic_score, best_semantic_score, best_combined_score, matching_sources

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap."""
        return bool(gap.reference_words)

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word using combined matching."""
        if not word.text.strip():
            return None

        best_match, phonetic_score, semantic_score, combined_score, matching_sources = self._find_best_match(word.text, gap.reference_words)

        if best_match and combined_score >= self.combined_threshold and best_match.lower() != word.text.lower():
            return WordCorrection(
                original_word=word.text,
                corrected_word=best_match,
                segment_index=segment_idx,
                word_index=current_word_idx,
                confidence=combined_score,
                source=", ".join(matching_sources),
                reason=f"Combined matching (phonetic: {phonetic_score:.2f}, semantic: {semantic_score:.2f})",
                alternatives={},
            )

        return None
