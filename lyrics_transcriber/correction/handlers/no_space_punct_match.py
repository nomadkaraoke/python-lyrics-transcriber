from typing import List, Optional, Tuple, Dict, Any
import logging
import re

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class NoSpacePunctuationMatchHandler(GapCorrectionHandler):
    """Handles gaps where reference text matches when spaces and punctuation are removed."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.logger = logger or logging.getLogger(__name__)

    def _remove_spaces_and_punct(self, words: List[str]) -> str:
        """Join words and remove all whitespace and punctuation."""
        text = "".join(words).lower()
        # Remove all punctuation including apostrophes
        return re.sub(r"[^\w\s]", "", text)

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        # Must have reference words
        if not gap.reference_words:
            self.logger.debug("No reference words available.")
            return False, {}

        # Get the gap text without spaces and punctuation
        gap_text = self._remove_spaces_and_punct(gap.words)

        # Check if any reference source matches when spaces and punctuation are removed
        for words in gap.reference_words.values():
            ref_text = self._remove_spaces_and_punct(words)
            if gap_text == ref_text:
                self.logger.debug("Found a matching reference source with spaces and punctuation removed.")
                return True, {}

        self.logger.debug("No matching reference source found with spaces and punctuation removed.")
        return False, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
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
                self.logger.debug(f"Using source '{source}' for corrections.")
                break

        # Calculate reference positions for the matching source
        reference_positions = WordOperations.calculate_reference_positions(gap, [matching_source])

        # Handle cases where number of words differ
        if len(gap.words) > len(reference_words):
            # Multiple transcribed words -> fewer reference words
            corrections.extend(
                WordOperations.create_word_combine_corrections(
                    original_words=gap.words,
                    reference_word=reference_words_original[0],
                    original_position=gap.transcription_position,
                    source=matching_source,
                    confidence=1.0,
                    combine_reason="NoSpacePunctuationMatchHandler: Words combined based on text match",
                    delete_reason="NoSpacePunctuationMatchHandler: Word removed as part of text match combination",
                    reference_positions=reference_positions,
                )
            )
            self.logger.debug(f"Combined words into '{reference_words_original[0]}'.")

        elif len(gap.words) < len(reference_words):
            # Single transcribed word -> multiple reference words
            corrections.extend(
                WordOperations.create_word_split_corrections(
                    original_word=gap.words[0],
                    reference_words=reference_words_original,
                    original_position=gap.transcription_position,
                    source=matching_source,
                    confidence=1.0,
                    reason="NoSpacePunctuationMatchHandler: Split word based on text match",
                    reference_positions=reference_positions,
                )
            )
            self.logger.debug(f"Split word '{gap.words[0]}' into {reference_words_original}.")

        else:
            # One-to-one replacement
            for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
                if orig_word.lower() != ref_word.lower():
                    correction = WordOperations.create_word_replacement_correction(
                        original_word=orig_word,
                        corrected_word=ref_word_original,
                        original_position=gap.transcription_position + i,
                        source=matching_source,
                        confidence=1.0,
                        reason=f"NoSpacePunctuationMatchHandler: Source '{matching_source}' matched when spaces and punctuation removed",
                        reference_positions=reference_positions,
                    )
                    corrections.append(correction)
                    self.logger.debug(f"Correction made: {correction}")

        return corrections
