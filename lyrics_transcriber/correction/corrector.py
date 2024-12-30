from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
import logging

from lyrics_transcriber.transcribers.base_transcriber import TranscriptionResult
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsData
from .strategy_diff import DiffBasedCorrector
from .base_strategy import CorrectionResult, CorrectionStrategy


class LyricsCorrector:
    """
    Coordinates lyrics correction process using multiple data sources
    and correction strategies.
    """

    def __init__(
        self,
        correction_strategy: Optional[CorrectionStrategy] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.correction_strategy = correction_strategy or DiffBasedCorrector(logger=self.logger)

    def run(self, transcription_results: List[TranscriptionResult], lyrics_results: List[LyricsData]) -> CorrectionResult:
        """Execute the correction process using configured strategy."""
        if not transcription_results:
            self.logger.error("No transcription results available")
            raise ValueError("No primary transcription data available")

        try:
            self.logger.debug(f"Running correction with strategy: {self.correction_strategy.__class__.__name__}")

            result = self.correction_strategy.correct(
                transcription_results=transcription_results,
                lyrics_results=lyrics_results,
            )

            self.logger.debug(f"Correction completed. Made {result.corrections_made} corrections")
            return result

        except Exception as e:
            self.logger.error(f"Correction failed: {str(e)}", exc_info=True)
            # Return uncorrected transcription as fallback
            return CorrectionResult(
                segments=transcription_results[0].result.segments,
                text=transcription_results[0].result.text,
                confidence=1.0,
                corrections_made=0,
                source_mapping={},
                metadata=transcription_results[0].result.metadata or {},
            )
