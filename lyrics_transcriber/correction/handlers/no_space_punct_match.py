from typing import List
import re

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class NoSpacePunctuationMatchHandler(GapCorrectionHandler):
    """Handles gaps where reference text matches when spaces and punctuation are removed."""

    def _remove_spaces_and_punct(self, words: List[str]) -> str:
        """Join words and remove all whitespace and punctuation."""
        text = "".join(words).lower()
        # Remove all punctuation including apostrophes
        return re.sub(r"[^\w\s]", "", text)

    def can_handle(self, gap: GapSequence) -> bool:
        # Must have reference words
        if not gap.reference_words:
            return False

        # Get the gap text without spaces and punctuation
        gap_text = self._remove_spaces_and_punct(gap.words)

        # Check if any reference source matches when spaces and punctuation are removed
        for words in gap.reference_words.values():
            ref_text = self._remove_spaces_and_punct(words)
            if gap_text == ref_text:
                return True

        return False

    def handle(self, gap: GapSequence) -> List[WordCorrection]:
        corrections = []

        # Find the matching source (we know there is at least one from can_handle)
        gap_text = self._remove_spaces_and_punct(gap.words)
        matching_source = None
        reference_words = None
        reference_words_original = None
        for source, words in gap.reference_words.items():
            if self._remove_spaces_and_punct(words) == gap_text:
                matching_source = source
                reference_words = words
                reference_words_original = gap.reference_words_original[source]
                break

        # Since the texts match when spaces and punctuation are removed,
        # we'll replace with the properly formatted reference words
        for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
            if orig_word.lower() != ref_word.lower():
                corrections.append(
                    WordCorrection(
                        original_word=orig_word,
                        corrected_word=ref_word_original,  # Use the original formatted word
                        segment_index=0,  # This will be updated when applying corrections
                        word_index=gap.transcription_position + i,
                        confidence=1.0,
                        source=matching_source,
                        reason=f"NoSpacePunctuationMatchHandler: Source '{matching_source}' matched when spaces and punctuation removed",
                        alternatives={},
                    )
                )

        return corrections
