from typing import List, Optional, Tuple
import logging

from lyrics_transcriber.types import GapSequence, LyricsData, TranscriptionResult, CorrectionResult, LyricsSegment, WordCorrection, Word
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_count_match import WordCountMatchHandler
from lyrics_transcriber.correction.handlers.extra_words import ExtraWordsHandler


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
            WordCountMatchHandler(),
            ExtraWordsHandler(),
            # AnchorWordsInGapHandler(), # "Correct" words which are in the gap but are identical in the reference
            # CombinedHandler(),  # Try combined matching first
            # MetaphoneHandler(),  # Fall back to individual matchers
            # SemanticHandler(),
            # MultiWordLevenshteinHandler(),
            # LevenshteinSimilarityHandler(),  # Last resort
            # HumanHandler(),  # Open web UI for human to review and correct
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

            # Process corrections
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
        """Process corrections using handlers.

        The correction flow works as follows:
        1. First pass: Process all gaps
           - Iterate through each gap sequence
           - Try handlers until one can handle the gap
           - Store all corrections in the gap
        2. Second pass: Apply corrections to segments
           - Iterate through segments and words
           - Look up any corrections that apply to each word
           - Create new segments with corrected words

        This two-pass approach separates the concerns of:
        a) Finding and making corrections (gap-centric)
        b) Applying those corrections to the original text (segment-centric)
        """
        self.logger.info(f"Starting correction process with {len(gap_sequences)} gaps")

        # First pass: Process all gaps
        all_corrections = self._process_gaps(gap_sequences)

        # Second pass: Apply corrections to segments
        corrected_segments = self._apply_corrections_to_segments(segments, all_corrections)

        self.logger.info(f"Correction process complete. Made {len(all_corrections)} corrections")
        return all_corrections, corrected_segments

    def _process_gaps(self, gap_sequences: List[GapSequence]) -> List[WordCorrection]:
        """Process each gap using available handlers until all words are corrected or no handlers remain."""
        all_corrections = []

        for gap in gap_sequences:
            self.logger.debug(f"Processing gap: {gap.text}")

            # Try each handler until gap is fully corrected
            for handler in self.handlers:
                if gap.is_fully_corrected:
                    break

                self.logger.debug(f"Trying handler {handler.__class__.__name__}")
                if handler.can_handle(gap):
                    self.logger.debug(f"{handler.__class__.__name__} can handle gap")
                    corrections = handler.handle(gap)
                    if corrections:
                        # Add corrections to gap and track corrected positions
                        for correction in corrections:
                            gap.add_correction(correction)

                        self.logger.debug(
                            f"{handler.__class__.__name__} made {len(corrections)} corrections: "
                            f"{[f'{c.original_word}->{c.corrected_word}' for c in corrections]}"
                        )
                        all_corrections.extend(corrections)

                        # Log remaining uncorrected words
                        if not gap.is_fully_corrected:
                            uncorrected = [word for _, word in gap.uncorrected_words]
                            self.logger.debug(f"Uncorrected words remaining: {', '.join(uncorrected)}")

            if not gap.corrections:
                self.logger.warning("No handler could handle the gap")

        return all_corrections

    def _apply_corrections_to_segments(self, segments: List[LyricsSegment], corrections: List[WordCorrection]) -> List[LyricsSegment]:
        """Apply corrections to create new segments."""
        correction_map = {c.word_index: c for c in corrections}
        corrected_segments = []

        current_word_idx = 0
        for segment_idx, segment in enumerate(segments):
            corrected_words = []
            for word in segment.words:
                if current_word_idx in correction_map:
                    correction = correction_map[current_word_idx]
                    if not correction.is_deletion:
                        corrected_words.append(
                            Word(
                                text=self._preserve_formatting(correction.original_word, correction.corrected_word),
                                start_time=word.start_time,
                                end_time=word.end_time,
                                confidence=correction.confidence,
                            )
                        )
                else:
                    corrected_words.append(word)
                current_word_idx += 1

            if corrected_words:  # Only create segment if it has words
                corrected_segments.append(
                    LyricsSegment(
                        text=" ".join(w.text for w in corrected_words),
                        words=corrected_words,
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                    )
                )

        return corrected_segments

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
