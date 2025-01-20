from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any

from lyrics_transcriber.types import GapSequence, WordCorrection


class GapCorrectionHandler(ABC):
    """Base class for gap correction handlers."""

    @abstractmethod
    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        """Determine if this handler can process the given gap.

        Returns:
            Tuple containing:
            - bool: Whether this handler can process the gap
            - dict: Data computed during can_handle that will be needed by handle().
                   Empty dict if no data needs to be passed.
        """
        pass

    @abstractmethod
    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Process a gap and return any corrections.

        Args:
            gap: The gap sequence to process
            data: Optional data dictionary returned by can_handle()
        """
        pass
