from typing import Optional

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class ExactMatchHandler(GapCorrectionHandler):
    """Handles gaps where reference sources agree and have matching word counts."""

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        if not gap.reference_words:
            return False

        ref_words_lists = list(gap.reference_words.values())
        return all(len(words) == gap.length for words in ref_words_lists) and all(
            words == ref_words_lists[0] for words in ref_words_lists[1:]
        )

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        gap_pos = current_word_idx - gap.transcription_position
        correction = list(gap.reference_words.values())[0][gap_pos]

        if correction.lower() == word.text.lower():
            return None

        return WordCorrection(
            original_word=word.text,
            corrected_word=correction,
            segment_index=segment_idx,
            word_index=current_word_idx,
            confidence=1.0,
            source=", ".join(gap.reference_words.keys()),
            reason="All reference sources agree on correction",
            alternatives={},
        )
