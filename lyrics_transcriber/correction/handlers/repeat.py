from typing import List, Dict, Optional
from lyrics_transcriber.types import GapSequence, WordCorrection
import logging


class RepeatCorrectionHandler:
    """Handler that applies corrections that were previously made by other handlers."""

    def __init__(self, logger: Optional[logging.Logger] = None, confidence_threshold: float = 0.7):
        self.logger = logger or logging.getLogger(__name__)
        self.confidence_threshold = confidence_threshold
        self.previous_corrections: List[WordCorrection] = []

    def can_handle(self, gap: GapSequence) -> bool:
        """Check if any words in the gap match previous corrections."""
        return bool(self.previous_corrections)

    def set_previous_corrections(self, corrections: List[WordCorrection]) -> None:
        """Store corrections from previous handlers to use as reference."""
        self.previous_corrections = corrections

    def handle(self, gap: GapSequence) -> List[WordCorrection]:
        """Apply previous corrections to matching words in the current gap."""
        corrections = []

        # Build a map of original words to their corrections
        correction_map: Dict[str, List[WordCorrection]] = {}
        for corr in self.previous_corrections:
            if corr.confidence >= self.confidence_threshold:
                correction_map.setdefault(corr.original_word.lower(), []).append(corr)

        # Check each word in the gap
        for i, word in enumerate(gap.words):
            word_lower = word.lower()
            if word_lower in correction_map:
                # Get the most common correction for this word
                prev_corrections = correction_map[word_lower]
                best_correction = max(
                    prev_corrections,
                    key=lambda c: (sum(1 for pc in prev_corrections if pc.corrected_word == c.corrected_word), c.confidence),
                )

                self.logger.debug(
                    f"Applying previous correction: {word} -> {best_correction.corrected_word} "
                    f"(confidence: {best_correction.confidence:.2f})"
                )

                corrections.append(
                    WordCorrection(
                        original_word=word,
                        corrected_word=best_correction.corrected_word,
                        segment_index=0,
                        word_index=gap.transcription_position + i,
                        confidence=best_correction.confidence * 0.9,  # Slightly lower confidence for repeats
                        source=best_correction.source,
                        reason=f"RepeatCorrectionHandler: Matches previous correction",
                        alternatives={best_correction.corrected_word: 1},
                        is_deletion=False,
                    )
                )

        return corrections