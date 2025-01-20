from typing import List
from lyrics_transcriber.types import WordCorrection


class WordOperations:
    """Utility class for common word manipulation operations used by correction handlers."""

    @staticmethod
    def create_word_replacement_correction(
        original_word: str,
        corrected_word: str,
        word_index: int,
        source: str,
        confidence: float,
        reason: str,
    ) -> WordCorrection:
        """Creates a correction for replacing a single word with another word."""
        return WordCorrection(
            original_word=original_word,
            corrected_word=corrected_word,
            segment_index=0,
            word_index=word_index,
            confidence=confidence,
            source=source,
            reason=reason,
            alternatives={},
        )

    @staticmethod
    def create_word_split_corrections(
        original_word: str,
        reference_words: List[str],
        word_index: int,
        source: str,
        confidence: float,
        reason: str,
    ) -> List[WordCorrection]:
        """Creates corrections for splitting a single word into multiple words."""
        corrections = []
        for split_idx, ref_word in enumerate(reference_words):
            corrections.append(
                WordCorrection(
                    original_word=original_word,
                    corrected_word=ref_word,
                    segment_index=0,
                    word_index=word_index,
                    confidence=confidence,
                    source=source,
                    reason=reason,
                    alternatives={},
                    split_index=split_idx,
                    split_total=len(reference_words),
                )
            )
        return corrections

    @staticmethod
    def create_word_combine_corrections(
        original_words: List[str],
        reference_word: str,
        word_index: int,
        source: str,
        confidence: float,
        combine_reason: str,
        delete_reason: str,
    ) -> List[WordCorrection]:
        """Creates corrections for combining multiple words into a single word."""
        corrections = []

        # First word gets replaced
        corrections.append(
            WordCorrection(
                original_word=original_words[0],
                corrected_word=reference_word,
                segment_index=0,
                word_index=word_index,
                confidence=confidence,
                source=source,
                reason=combine_reason,
                alternatives={},
            )
        )

        # Additional words get marked for deletion
        for i, word in enumerate(original_words[1:], start=1):
            corrections.append(
                WordCorrection(
                    original_word=word,
                    corrected_word="",
                    segment_index=0,
                    word_index=word_index + i,
                    confidence=confidence,
                    source=source,
                    reason=delete_reason,
                    alternatives={},
                    is_deletion=True,
                )
            )

        return corrections
