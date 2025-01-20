from typing import List

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class RelaxedWordCountMatchHandler(GapCorrectionHandler):
    """Handles gaps where at least one reference source has matching word count."""

    def can_handle(self, gap: GapSequence) -> bool:
        # Must have reference words
        if not gap.reference_words:
            return False

        # Check if any source has matching word count
        for words in gap.reference_words.values():
            if len(words) == gap.length:
                return True

        return False

    def handle(self, gap: GapSequence) -> List[WordCorrection]:
        corrections = []

        # Find the first source that has matching word count
        matching_source = None
        reference_words = None
        for source, words in gap.reference_words.items():
            if len(words) == gap.length:
                matching_source = source
                reference_words = words
                break

        # Since we found a source with matching word count, we can correct using that source
        for i, (orig_word, ref_word) in enumerate(zip(gap.words, reference_words)):
            if orig_word.lower() != ref_word.lower():
                corrections.append(
                    WordCorrection(
                        original_word=orig_word,
                        corrected_word=ref_word,
                        segment_index=0,  # This will be updated when applying corrections
                        word_index=gap.transcription_position + i,
                        confidence=1.0,
                        source=matching_source,
                        reason=f"RelaxedWordCountMatchHandler: Source '{matching_source}' had matching word count",
                        alternatives={},
                    )
                )

        return corrections
