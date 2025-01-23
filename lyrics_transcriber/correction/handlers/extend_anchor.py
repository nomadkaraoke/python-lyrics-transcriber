from typing import List, Optional, Tuple, Dict, Any

from lyrics_transcriber.types import GapSequence, WordCorrection
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

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        # Must have reference words
        if not gap.reference_words:
            return False, {}

        # Gap must have words
        if not gap.words:
            return False, {}

        # At least one word must match between gap and any reference source
        # in the same position
        has_match = any(
            i < len(ref_words) and gap.words[i].lower() == ref_words[i].lower()
            for ref_words in gap.reference_words.values()
            for i in range(min(len(gap.words), len(ref_words)))
        )

        return has_match, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        corrections = []

        # Process each word in the gap that has a corresponding reference position
        for i, word in enumerate(gap.words):
            # Find reference sources that have a matching word at this position
            matching_sources = [
                source for source, ref_words in gap.reference_words.items() if i < len(ref_words) and word.lower() == ref_words[i].lower()
            ]

            if matching_sources:
                # Word matches reference(s) at this position - validate it
                confidence = len(matching_sources) / len(gap.reference_words)
                sources = ", ".join(matching_sources)

                # Calculate reference positions for matching sources
                reference_positions = WordOperations.calculate_reference_positions(gap, matching_sources)

                corrections.append(
                    WordOperations.create_word_replacement_correction(
                        original_word=word,
                        corrected_word=word,  # Same word, just validating
                        original_position=gap.transcription_position + i,
                        source=sources,
                        confidence=confidence,
                        reason="ExtendAnchorHandler: Matched reference source(s)",
                        reference_positions=reference_positions,
                    )
                )
            # No else clause - non-matching words are left unchanged

        return corrections
