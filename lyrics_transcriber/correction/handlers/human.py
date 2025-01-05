from typing import Optional

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class HumanHandler(GapCorrectionHandler):
    """Handles gaps by opening a web UI for human to review the corrections made and manually fix any last gaps."""

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        return True

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        # TODO: Open web UI for human to review the corrections made and manually fix any last gaps
        return None
