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
        for source, words in gap.reference_words.items():
            ref_text = self._remove_spaces_and_punct(words)
            if gap_text == ref_text:
                self.logger.debug("Found a matching reference source with spaces and punctuation removed.")
                return True, {
                    "matching_source": source,
                    "reference_words": words,
                    "reference_words_original": gap.reference_words_original[source],
                }

        self.logger.debug("No matching reference source found with spaces and punctuation removed.")
        return False, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Handle the gap using no-space punctuation matching."""
        if not data:
            can_handle, data = self.can_handle(gap)
            if not can_handle:
                return []

        corrections = []
        matching_source = data["matching_source"]
        reference_words = data["reference_words"]
        reference_words_original = data["reference_words_original"]

        # Get original word IDs if available
        original_word_ids = [word.id if hasattr(word, "id") else None for word in gap.words]

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
                    combine_reason="Words combined based on text match",
                    delete_reason="Word removed as part of text match combination",
                    reference_positions=reference_positions,
                    handler="NoSpacePunctuationMatchHandler",
                    original_word_ids=original_word_ids,
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
                    reason="Split word based on text match",
                    reference_positions=reference_positions,
                    handler="NoSpacePunctuationMatchHandler",
                    original_word_id=original_word_ids[0],
                )
            )
            self.logger.debug(f"Split word '{gap.words[0]}' into {reference_words_original}.")

        else:
            # One-to-one replacement
            for i, (orig_word, ref_word, ref_word_original, word_id) in enumerate(
                zip(gap.words, reference_words, reference_words_original, original_word_ids)
            ):
                if orig_word.lower() != ref_word.lower():
                    correction = WordOperations.create_word_replacement_correction(
                        original_word=orig_word,
                        corrected_word=ref_word_original,
                        original_position=gap.transcription_position + i,
                        source=matching_source,
                        confidence=1.0,
                        reason=f"Source '{matching_source}' matched when spaces and punctuation removed",
                        reference_positions=reference_positions,
                        handler="NoSpacePunctuationMatchHandler",
                        original_word_id=word_id,
                    )
                    corrections.append(correction)
                    self.logger.debug(f"Correction made: {correction}")

        return corrections
