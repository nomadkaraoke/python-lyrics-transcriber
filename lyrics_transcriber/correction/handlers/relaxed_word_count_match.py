from typing import List, Tuple, Dict, Any, Optional
import logging

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class RelaxedWordCountMatchHandler(GapCorrectionHandler):
    """Handles gaps where at least one reference source has matching word count."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.logger = logger

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        # Must have reference words
        if not gap.reference_words:
            self.logger.debug("No reference words available.")
            return False, {}

        # Check if any source has matching word count
        for source, words in gap.reference_words.items():
            if len(words) == gap.length:
                self.logger.debug(f"Source '{source}' has matching word count.")
                return True, {}

        self.logger.debug("No source with matching word count found.")
        return False, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        corrections = []

        # Find the first source that has matching word count
        matching_source = None
        reference_words = None
        reference_words_original = None
        for source, words in gap.reference_words.items():
            if len(words) == gap.length:
                matching_source = source
                reference_words = words
                reference_words_original = gap.reference_words_original[source]
                self.logger.debug(f"Using source '{source}' for corrections.")
                break

        # Use the centralized method to calculate reference positions for the matching source
        reference_positions = WordOperations.calculate_reference_positions(gap, [matching_source])
        self.logger.debug(f"Calculated reference positions: {reference_positions}")

        # Since we found a source with matching word count, we can correct using that source
        for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
            if orig_word.lower() != ref_word.lower():
                correction = WordOperations.create_word_replacement_correction(
                    original_word=orig_word,
                    corrected_word=ref_word_original,
                    original_position=gap.transcription_position + i,
                    source=matching_source,
                    confidence=1.0,
                    reason=f"RelaxedWordCountMatchHandler: Source '{matching_source}' had matching word count",
                    reference_positions=reference_positions,
                )
                corrections.append(correction)
                self.logger.debug(f"Correction made: {correction}")

        return corrections
