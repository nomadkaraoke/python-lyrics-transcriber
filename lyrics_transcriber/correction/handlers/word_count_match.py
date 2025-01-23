from typing import List, Tuple, Dict, Any, Optional

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class WordCountMatchHandler(GapCorrectionHandler):
    """Handles gaps where reference sources agree and have matching word counts."""

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        # Must have reference words
        if not gap.reference_words:
            return False, {}

        ref_words_lists = list(gap.reference_words.values())

        # All sources must have same number of words as gap
        if not all(len(words) == gap.length for words in ref_words_lists):
            return False, {}

        # If we have multiple sources, they must all agree
        if len(ref_words_lists) > 1 and not all(words == ref_words_lists[0] for words in ref_words_lists[1:]):
            return False, {}

        return True, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        corrections = []
        # Get both clean and original reference words from first source
        source = list(gap.reference_words.keys())[0]
        reference_words = gap.reference_words[source]
        reference_words_original = gap.reference_words_original[source]
        sources = ", ".join(gap.reference_words.keys())

        # Use the centralized method to calculate reference positions for all sources
        reference_positions = WordOperations.calculate_reference_positions(gap)

        # Since we know all reference sources agree, we can correct all words in the gap
        for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
            if orig_word.lower() != ref_word.lower():
                corrections.append(
                    WordOperations.create_word_replacement_correction(
                        original_word=orig_word,
                        corrected_word=ref_word_original,
                        original_position=gap.transcription_position + i,
                        source=sources,
                        confidence=1.0,
                        reason="WordCountMatchHandler: Reference sources had same word count as gap",
                        reference_positions=reference_positions,
                    )
                )

        return corrections
