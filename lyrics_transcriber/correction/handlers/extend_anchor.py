from typing import List, Optional, Tuple, Dict, Any
import logging

from lyrics_transcriber.types import GapSequence, WordCorrection, Word
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class ExtendAnchorHandler(GapCorrectionHandler):
    """Handles gaps where some words match reference text but there are extra words.

    This handler looks for cases where:
    1. One or more words in the gap match words in the same position in at least one reference source
    2. The gap may contain additional words that aren't in the reference

    When such matches are found, it:
    1. Validates all matching words (creates corrections that keep the same words)
    2. Leaves all non-matching words unchanged for other handlers to process

    The confidence of validations is based on the ratio of reference sources that agree.
    For example, if 2 out of 4 sources have the matching word, confidence will be 0.5.

    Examples:
        Gap: "hello world extra words"
        References:
            genius: ["hello", "world"]
            spotify: ["hello", "world"]
        Result:
            - Validate "hello" (confidence=1.0)
            - Validate "world" (confidence=1.0)
            - Leave "extra" and "words" unchanged

        Gap: "martyr youre a"
        References:
            genius: ["martyr"]
            spotify: ["mother"]
        Result:
            - Validate "martyr" (confidence=0.5, source="genius")
            - Leave "youre" and "a" unchanged
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def can_handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if this gap can be handled by extending anchor sequences."""
        # Check if we have anchor sequences
        if not data or "anchor_sequences" not in data:
            self.logger.debug("No anchor sequences available")
            return False, {}

        # Must have reference word IDs
        if not gap.reference_word_ids:
            self.logger.debug("No reference word IDs available.")
            return False, {}

        # Gap must have word IDs
        if not gap.transcribed_word_ids:
            self.logger.debug("No word IDs in the gap to process.")
            return False, {}

        # At least one word ID must match between gap and any reference source
        # in the same position
        has_match = any(
            i < len(ref_word_ids) and gap.transcribed_word_ids[i] == ref_word_ids[i]
            for ref_word_ids in gap.reference_word_ids.values()
            for i in range(min(len(gap.transcribed_word_ids), len(ref_word_ids)))
        )

        self.logger.debug(f"Can handle gap: {has_match}")
        return has_match, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        corrections = []

        # Get word lookup map from data
        word_map = data.get("word_map", {})
        if not word_map:
            self.logger.error("No word_map provided in data")
            return []

        # Process each word in the gap that has a corresponding reference position
        for i, word_id in enumerate(gap.transcribed_word_ids):
            # Get the actual word object
            if word_id not in word_map:
                self.logger.error(f"Word ID {word_id} not found in word_map")
                continue
            word = word_map[word_id]

            # Find reference sources that have a matching word at this position
            matching_sources = [
                source for source, ref_word_ids in gap.reference_word_ids.items() if i < len(ref_word_ids) and word_id == ref_word_ids[i]
            ]

            if not matching_sources:
                self.logger.debug(f"Skipping word '{word.text}' at position {i} - no matching references")
                continue

            if matching_sources:
                # Word matches reference(s) at this position - validate it
                confidence = len(matching_sources) / len(gap.reference_word_ids)
                sources = ", ".join(matching_sources)

                # Get base reference positions
                base_reference_positions = WordOperations.calculate_reference_positions(gap, matching_sources)

                # Adjust reference positions based on the word's position in the reference text
                reference_positions = {}
                for source in matching_sources:
                    if source in base_reference_positions:
                        # Find this word's position in the reference text
                        ref_word_ids = gap.reference_word_ids[source]
                        for ref_idx, ref_word_id in enumerate(ref_word_ids):
                            if ref_word_id == word_id:
                                reference_positions[source] = base_reference_positions[source] + ref_idx
                                break

                corrections.append(
                    WordOperations.create_word_replacement_correction(
                        original_word=word.text,
                        corrected_word=word.text,
                        original_position=gap.transcription_position + i,
                        source=sources,
                        confidence=confidence,
                        reason="Matched reference source(s)",
                        reference_positions=reference_positions,
                        handler="ExtendAnchorHandler",
                        original_word_id=word_id,
                        corrected_word_id=word_id,
                    )
                )
                self.logger.debug(f"Validated word '{word.text}' with confidence {confidence} from sources: {sources}")

        return corrections
