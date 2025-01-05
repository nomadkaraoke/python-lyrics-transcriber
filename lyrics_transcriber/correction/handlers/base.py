from abc import ABC, abstractmethod
from typing import Optional

from lyrics_transcriber.types import GapSequence, Word, WordCorrection


class GapCorrectionHandler(ABC):
    """Base class for gap correction strategies."""

    @abstractmethod
    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Determine if this handler can process the given gap."""
        pass

    @abstractmethod
    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Process the gap and return a correction if possible."""
        pass
