from abc import ABC, abstractmethod
from typing import List, Optional

from lyrics_transcriber.types import GapSequence, Word, WordCorrection


class GapCorrectionHandler(ABC):
    """Base class for gap correction handlers."""

    @abstractmethod
    def can_handle(self, gap: GapSequence) -> bool:
        """Determine if this handler can process the given gap."""
        pass

    @abstractmethod
    def handle(self, gap: GapSequence) -> List[WordCorrection]:
        """Process a gap and return any corrections."""
        pass
