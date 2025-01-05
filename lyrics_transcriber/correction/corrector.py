from typing import List, Optional, Tuple
import logging

from lyrics_transcriber.types import GapSequence, LyricsData, TranscriptionResult, CorrectionResult, LyricsSegment, WordCorrection, Word
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.exact_match import ExactMatchHandler
from lyrics_transcriber.correction.handlers.levenshtein import LevenshteinSimilarityHandler
from lyrics_transcriber.correction.handlers.multi_levenshtein import MultiWordLevenshteinHandler
from lyrics_transcriber.correction.handlers.metaphone import MetaphoneHandler
from lyrics_transcriber.correction.handlers.semantic import SemanticHandler
from lyrics_transcriber.correction.handlers.combined import CombinedHandler
from lyrics_transcriber.correction.handlers.human import HumanHandler


class LyricsCorrector:
    """
    Coordinates lyrics correction process using multiple correction handlers.
    """

    def __init__(
        self,
        handlers: Optional[List[GapCorrectionHandler]] = None,
        anchor_finder: Optional[AnchorSequenceFinder] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.anchor_finder = anchor_finder or AnchorSequenceFinder(logger=self.logger)

        # Default handlers in order of preference
        self.handlers = handlers or [
            ExactMatchHandler(),
            # CombinedHandler(),  # Try combined matching first
            MetaphoneHandler(),  # Fall back to individual matchers
            # SemanticHandler(),
            # MultiWordLevenshteinHandler(),
            # LevenshteinSimilarityHandler(),  # Last resort
            HumanHandler(),  # Open web UI for human to review and correct
        ]

    def run(self, transcription_results: List[TranscriptionResult], lyrics_results: List[LyricsData]) -> CorrectionResult:
        """Execute the correction process."""
        if not transcription_results:
            self.logger.error("No transcription results available")
            raise ValueError("No primary transcription data available")

        try:
            # Get primary transcription
            primary_transcription = sorted(transcription_results, key=lambda x: x.priority)[0].result
            transcribed_text = " ".join(" ".join(w.text for w in segment.words) for segment in primary_transcription.segments)
            reference_texts = {lyrics.source: lyrics.lyrics for lyrics in lyrics_results}

            # Find anchor sequences and gaps
            self.logger.debug("Finding anchor sequences and gaps")
            anchor_sequences = self.anchor_finder.find_anchors(transcribed_text, reference_texts)
            gap_sequences = self.anchor_finder.find_gaps(transcribed_text, anchor_sequences, reference_texts)

            # Process corrections (we'll implement this next)
            corrections, corrected_segments = self._process_corrections(primary_transcription.segments, gap_sequences)

            # Calculate correction ratio
            total_words = sum(len(segment.words) for segment in corrected_segments)
            corrections_made = len(corrections)
            correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

            return CorrectionResult(
                original_segments=primary_transcription.segments,
                corrected_segments=corrected_segments,
                corrected_text="\n".join(segment.text for segment in corrected_segments) + "\n",
                corrections=corrections,
                corrections_made=corrections_made,
                confidence=correction_ratio,
                transcribed_text=transcribed_text,
                reference_texts=reference_texts,
                anchor_sequences=anchor_sequences,
                gap_sequences=gap_sequences,
                metadata={
                    "anchor_sequences_count": len(anchor_sequences),
                    "gap_sequences_count": len(gap_sequences),
                    "total_words": total_words,
                    "correction_ratio": correction_ratio,
                },
            )

        except Exception as e:
            self.logger.error(f"Correction failed: {str(e)}", exc_info=True)
            # Return uncorrected transcription as fallback
            return self._create_fallback_result(primary_transcription)

    def _preserve_formatting(self, original: str, new_word: str) -> str:
        """Preserve original word's formatting when applying correction."""
        # Find leading/trailing whitespace
        leading_space = " " if original != original.lstrip() else ""
        trailing_space = " " if original != original.rstrip() else ""
        return leading_space + new_word.strip() + trailing_space

    def _try_correct_word(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Attempt to correct a word using available handlers."""
        for handler in self.handlers:
            if handler.can_handle(gap, current_word_idx):
                correction = handler.handle(gap, word, current_word_idx, segment_idx)
                if correction:
                    return correction
        return None

    def _process_corrections(
        self, segments: List[LyricsSegment], gap_sequences: List[GapSequence]
    ) -> Tuple[List[WordCorrection], List[LyricsSegment]]:
        """Process corrections using handlers."""
        corrections: List[WordCorrection] = []
        corrected_segments = []

        # Track current position in segments/words
        current_segment_idx = 0
        current_word_idx = 0

        # Keep track of which gaps have been corrected
        corrected_gaps = set()

        self.logger.debug(f"Starting correction process with {len(gap_sequences)} gaps")

        for segment in segments:
            self.logger.debug(f"Processing segment {current_segment_idx}: {segment.text}")
            corrected_words = []

            for word in segment.words:
                self.logger.debug(f"Processing word at position {current_word_idx}: {word.text}")

                gap = next(
                    (g for g in gap_sequences if g.transcription_position <= current_word_idx < g.transcription_position + g.length), None
                )

                if gap:
                    self.logger.debug(f"Found gap at position {gap.transcription_position}: {gap.words}")
                    if gap not in corrected_gaps:
                        self.logger.debug("Gap not yet corrected, trying handlers")
                        # Try handlers in order until one makes a correction
                        for handler in self.handlers:
                            self.logger.debug(f"Trying handler {handler.__class__.__name__}")
                            if handler.can_handle(gap, current_word_idx):
                                self.logger.debug(f"Handler {handler.__class__.__name__} can handle gap")
                                correction = handler.handle(gap, word, current_word_idx, current_segment_idx)
                                if correction:
                                    self.logger.debug(f"Handler made correction: {correction.original_word} -> {correction.corrected_word}")
                                    corrected_text = self._preserve_formatting(word.text, correction.corrected_word)
                                    corrected_word = Word(
                                        text=corrected_text,
                                        start_time=word.start_time,
                                        end_time=word.end_time,
                                        confidence=correction.confidence,
                                    )
                                    corrected_words.append(corrected_word)
                                    corrections.append(correction)
                                    gap.corrections.append(correction)
                                    corrected_gaps.add(gap)
                                    current_word_idx += 1
                                    break  # Stop trying other handlers for this word
                        else:
                            self.logger.debug("No handler made a correction")
                            corrected_words.append(word)
                            current_word_idx += 1
                    else:
                        self.logger.debug("Gap already corrected")
                        corrected_words.append(word)
                        current_word_idx += 1
                else:
                    self.logger.debug("No gap found for this word")
                    corrected_words.append(word)
                    current_word_idx += 1

            # Create corrected segment
            corrected_segment = LyricsSegment(
                text=" ".join(w.text for w in corrected_words),
                words=corrected_words,
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
            corrected_segments.append(corrected_segment)
            current_segment_idx += 1

        self.logger.debug(f"Correction process complete. Made {len(corrections)} corrections")
        return corrections, corrected_segments

    def _create_fallback_result(self, transcription):
        """Create a fallback result when correction fails."""
        return CorrectionResult(
            original_segments=transcription.segments,
            corrected_segments=transcription.segments,
            corrected_text="\n".join(segment.text for segment in transcription.segments) + "\n",
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            transcribed_text="\n".join(segment.text for segment in transcription.segments),
            reference_texts={},
            anchor_sequences=[],
            gap_sequences=[],
            metadata={
                "error": "Correction failed, using original transcription",
                "anchor_sequences_count": 0,
                "gap_sequences_count": 0,
                "total_words": sum(len(segment.words) for segment in transcription.segments),
                "correction_ratio": 1.0,
            },
        )
