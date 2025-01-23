from typing import List, Optional, Dict
from lyrics_transcriber.types import WordCorrection, GapSequence


class WordOperations:
    """Utility class for common word manipulation operations used by correction handlers."""

    @staticmethod
    def calculate_reference_positions(gap: GapSequence, sources: Optional[List[str]] = None) -> Dict[str, int]:
        """Calculate reference positions for given sources based on preceding anchor.

        Args:
            gap: The gap sequence containing the preceding anchor
            sources: Optional list of sources to calculate positions for. If None, uses all sources.

        Returns:
            Dictionary mapping source names to their reference positions
        """
        reference_positions = {}
        if gap.preceding_anchor:
            # If no sources specified, use all sources from reference words
            sources_to_check = sources or list(gap.reference_words.keys())

            for source in sources_to_check:
                if source in gap.preceding_anchor.reference_positions:
                    # Calculate position based on anchor position and offset
                    anchor_pos = gap.preceding_anchor.reference_positions[source]
                    ref_pos = anchor_pos + len(gap.preceding_anchor.words)
                    reference_positions[source] = ref_pos
        return reference_positions

    @staticmethod
    def create_word_replacement_correction(
        original_word: str,
        corrected_word: str,
        original_position: int,
        source: str,
        confidence: float,
        reason: str,
        reference_positions: Optional[Dict[str, int]] = None,
    ) -> WordCorrection:
        """Creates a correction for replacing a single word with another word."""
        return WordCorrection(
            original_word=original_word,
            corrected_word=corrected_word,
            segment_index=0,
            original_position=original_position,
            confidence=confidence,
            source=source,
            reason=reason,
            alternatives={},
            reference_positions=reference_positions,
            length=1,  # Single word replacement
        )

    @staticmethod
    def create_word_split_corrections(
        original_word: str,
        reference_words: List[str],
        original_position: int,
        source: str,
        confidence: float,
        reason: str,
        reference_positions: Optional[Dict[str, int]] = None,
    ) -> List[WordCorrection]:
        """Creates corrections for splitting a single word into multiple words."""
        corrections = []
        for split_idx, ref_word in enumerate(reference_words):
            corrections.append(
                WordCorrection(
                    original_word=original_word,
                    corrected_word=ref_word,
                    segment_index=0,
                    original_position=original_position,
                    confidence=confidence,
                    source=source,
                    reason=reason,
                    alternatives={},
                    split_index=split_idx,
                    split_total=len(reference_words),
                    reference_positions=reference_positions,
                    length=1,  # Each split word is length 1
                )
            )
        return corrections

    @staticmethod
    def create_word_combine_corrections(
        original_words: List[str],
        reference_word: str,
        original_position: int,
        source: str,
        confidence: float,
        combine_reason: str,
        delete_reason: str,
        reference_positions: Optional[Dict[str, int]] = None,
    ) -> List[WordCorrection]:
        """Creates corrections for combining multiple words into a single word."""
        corrections = []

        # First word gets replaced
        corrections.append(
            WordCorrection(
                original_word=original_words[0],
                corrected_word=reference_word,
                segment_index=0,
                original_position=original_position,
                confidence=confidence,
                source=source,
                reason=combine_reason,
                alternatives={},
                reference_positions=reference_positions,
                length=len(original_words),  # Combined word spans all original words
            )
        )

        # Additional words get marked for deletion
        for i, word in enumerate(original_words[1:], start=1):
            corrections.append(
                WordCorrection(
                    original_word=word,
                    corrected_word="",
                    segment_index=0,
                    original_position=original_position + i,
                    confidence=confidence,
                    source=source,
                    reason=delete_reason,
                    alternatives={},
                    is_deletion=True,
                    reference_positions=reference_positions,
                    length=1,  # Deleted words are length 1
                )
            )

        return corrections
