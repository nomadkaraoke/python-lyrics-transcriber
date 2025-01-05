from typing import List, Optional, Tuple

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.levenshtein import LevenshteinSimilarityHandler


class MultiWordLevenshteinHandler(GapCorrectionHandler):
    """Handles corrections by matching sequences of words."""

    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold
        self.levenshtein_matcher = LevenshteinSimilarityHandler(similarity_threshold)

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap."""
        if not gap.reference_words:
            return False

        # Don't handle cases where sources disagree
        ref_words_lists = list(gap.reference_words.values())
        if not all(words == ref_words_lists[0] for words in ref_words_lists[1:]):
            return False

        # Don't handle cases where reference has different length than gap
        if any(len(words) != len(gap.words) for words in gap.reference_words.values()):
            return False

        return True

    def _align_sequences(self, gap_words: List[str], ref_words: List[str]) -> List[Tuple[Optional[str], Optional[str], float]]:
        """Align two sequences of words and return matches with confidence scores."""
        alignments = []

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
                similarity = self.levenshtein_matcher._get_string_similarity(gap_word, ref_word)
                score = max(position_score, similarity)

                if score >= self.similarity_threshold:
                    best_match = ref_word
                    best_score = score

            alignments.append((gap_word, best_match, best_score))

        return alignments

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on sequence alignment."""
        if not word.text.strip():
            return None

        gap_pos = current_word_idx - gap.transcription_position

        best_alignment = None
        best_confidence = 0.0
        best_sources = set()

        for source, ref_words in gap.reference_words.items():
            alignments = self._align_sequences(gap.words, ref_words)

            if gap_pos < len(alignments):
                gap_word, correction, confidence = alignments[gap_pos]

                if correction and correction.lower() == word.text.lower():
                    return None

                if correction and confidence > best_confidence:
                    best_alignment = correction
                    best_confidence = confidence
                    best_sources = {source}
                elif correction and confidence == best_confidence:
                    best_sources.add(source)

        if best_alignment and best_confidence >= self.similarity_threshold:
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

        return None
