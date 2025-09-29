from typing import List, Optional, Tuple, Union, Dict, Any
import logging
from pathlib import Path
from copy import deepcopy
import os

from lyrics_transcriber.correction.handlers.levenshtein import LevenshteinHandler
from lyrics_transcriber.correction.handlers.llm import LLMHandler
from lyrics_transcriber.correction.handlers.no_space_punct_match import NoSpacePunctuationMatchHandler
from lyrics_transcriber.correction.handlers.relaxed_word_count_match import RelaxedWordCountMatchHandler
from lyrics_transcriber.correction.handlers.repeat import RepeatCorrectionHandler
from lyrics_transcriber.correction.handlers.sound_alike import SoundAlikeHandler
from lyrics_transcriber.correction.handlers.syllables_match import SyllablesMatchHandler
from lyrics_transcriber.correction.handlers.word_count_match import WordCountMatchHandler
from lyrics_transcriber.types import (
    CorrectionStep,
    GapSequence,
    LyricsData,
    TranscriptionResult,
    CorrectionResult,
    LyricsSegment,
    WordCorrection,
    Word,
)
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.extend_anchor import ExtendAnchorHandler
from lyrics_transcriber.utils.word_utils import WordUtils
from lyrics_transcriber.correction.handlers.llm_providers import OllamaProvider, OpenAIProvider


class LyricsCorrector:
    """
    Coordinates lyrics correction process using multiple correction handlers.
    """

    def __init__(
        self,
        cache_dir: Union[str, Path],
        handlers: Optional[List[GapCorrectionHandler]] = None,
        enabled_handlers: Optional[List[str]] = None,
        anchor_finder: Optional[AnchorSequenceFinder] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self._anchor_finder = anchor_finder
        self._cache_dir = Path(cache_dir)

        # Define default enabled handlers - excluding LLM, Repeat, SoundAlike, and Levenshtein
        DEFAULT_ENABLED_HANDLERS = [
            "ExtendAnchorHandler",
            "WordCountMatchHandler",
            "SyllablesMatchHandler",
            "RelaxedWordCountMatchHandler",
            "NoSpacePunctuationMatchHandler",
        ]

        # Create all handlers but respect enabled_handlers if provided
        all_handlers = [
            ("ExtendAnchorHandler", ExtendAnchorHandler(logger=self.logger)),
            ("WordCountMatchHandler", WordCountMatchHandler(logger=self.logger)),
            ("SyllablesMatchHandler", SyllablesMatchHandler(logger=self.logger)),
            ("RelaxedWordCountMatchHandler", RelaxedWordCountMatchHandler(logger=self.logger)),
            ("NoSpacePunctuationMatchHandler", NoSpacePunctuationMatchHandler(logger=self.logger)),
            (
                "LLMHandler_Ollama_R17B",
                LLMHandler(
                    provider=OllamaProvider(model="deepseek-r1:7b", logger=self.logger),
                    name="LLMHandler_Ollama_R17B",
                    logger=self.logger,
                    cache_dir=self._cache_dir,
                ),
            ),
            ("RepeatCorrectionHandler", RepeatCorrectionHandler(logger=self.logger)),
            ("SoundAlikeHandler", SoundAlikeHandler(logger=self.logger)),
            ("LevenshteinHandler", LevenshteinHandler(logger=self.logger)),
        ]

        # Add OpenRouter handlers only if API key is available
        if os.getenv("OPENROUTER_API_KEY"):
            openrouter_handlers = [
                (
                    "LLMHandler_OpenRouter_Sonnet",
                    LLMHandler(
                        provider=OpenAIProvider(
                            model="anthropic/claude-3-sonnet",
                            api_key=os.getenv("OPENROUTER_API_KEY"),
                            base_url="https://openrouter.ai/api/v1",
                            logger=self.logger,
                        ),
                        name="LLMHandler_OpenRouter_Sonnet",
                        logger=self.logger,
                        cache_dir=self._cache_dir,
                    ),
                ),
                (
                    "LLMHandler_OpenRouter_R1",
                    LLMHandler(
                        provider=OpenAIProvider(
                            model="deepseek/deepseek-r1",
                            api_key=os.getenv("OPENROUTER_API_KEY"),
                            base_url="https://openrouter.ai/api/v1",
                            logger=self.logger,
                        ),
                        name="LLMHandler_OpenRouter_R1",
                        logger=self.logger,
                        cache_dir=self._cache_dir,
                    ),
                ),
            ]
            all_handlers.extend(openrouter_handlers)

        # Store all handler information
        self.all_handlers = [
            {
                "id": handler_id,
                "name": handler_id,
                "description": handler.__class__.__doc__ or "",
                "enabled": handler_id in (enabled_handlers if enabled_handlers is not None else DEFAULT_ENABLED_HANDLERS),
            }
            for handler_id, handler in all_handlers
        ]

        if handlers:
            self.handlers = handlers
        else:
            # Use provided enabled_handlers if available, otherwise use defaults
            handler_filter = enabled_handlers if enabled_handlers is not None else DEFAULT_ENABLED_HANDLERS
            self.handlers = [h[1] for h in all_handlers if h[0] in handler_filter]

    @property
    def anchor_finder(self) -> AnchorSequenceFinder:
        """Lazy load the anchor finder instance, initializing it if not already set."""
        if self._anchor_finder is None:
            self._anchor_finder = AnchorSequenceFinder(cache_dir=self._cache_dir, logger=self.logger)
        return self._anchor_finder

    def run(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: Dict[str, LyricsData],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CorrectionResult:
        """Execute the correction process."""
        # Optional agentic routing flag from environment; default off for safety
        agentic_enabled = os.getenv("USE_AGENTIC_AI", "").lower() in {"1", "true", "yes"}
        if not transcription_results:
            self.logger.error("No transcription results available")
            raise ValueError("No primary transcription data available")

        # Store reference lyrics for use in word map
        self.reference_lyrics = lyrics_results

        # Get primary transcription
        primary_transcription_result = sorted(transcription_results, key=lambda x: x.priority)[0]
        primary_transcription = primary_transcription_result.result
        transcribed_text = " ".join(" ".join(w.text for w in segment.words) for segment in primary_transcription.segments)

        # Find anchor sequences and gaps
        self.logger.debug("Finding anchor sequences and gaps")
        anchor_sequences = self.anchor_finder.find_anchors(transcribed_text, lyrics_results, primary_transcription_result)
        gap_sequences = self.anchor_finder.find_gaps(transcribed_text, anchor_sequences, lyrics_results, primary_transcription_result)

        # Store anchor sequences for use in correction handlers
        self._anchor_sequences = anchor_sequences

        # Process corrections with metadata
        corrections, corrected_segments, correction_steps, word_id_map, segment_id_map = self._process_corrections(
            primary_transcription.segments, gap_sequences, metadata=metadata
        )

        # Calculate correction ratio
        total_words = sum(len(segment.words) for segment in corrected_segments)
        corrections_made = len(corrections)
        correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

        # Get the currently enabled handler IDs using the handler's name attribute if available
        enabled_handlers = [getattr(handler, "name", handler.__class__.__name__) for handler in self.handlers]

        result = CorrectionResult(
            original_segments=primary_transcription.segments,
            corrected_segments=corrected_segments,
            corrections=corrections,
            corrections_made=corrections_made,
            confidence=correction_ratio,
            reference_lyrics=lyrics_results,
            anchor_sequences=anchor_sequences,
            resized_segments=[],
            gap_sequences=gap_sequences,
            metadata={
                "anchor_sequences_count": len(anchor_sequences),
                "gap_sequences_count": len(gap_sequences),
                "total_words": total_words,
                "correction_ratio": correction_ratio,
                "available_handlers": self.all_handlers,
                "enabled_handlers": enabled_handlers,
                "agentic_routing": "agentic" if agentic_enabled else "rule-based",
            },
            correction_steps=correction_steps,
            word_id_map=word_id_map,
            segment_id_map=segment_id_map,
        )
        return result

    def _preserve_formatting(self, original: str, new_word: str) -> str:
        """Preserve original word's formatting when applying correction."""
        # Find leading/trailing whitespace
        leading_space = " " if original != original.lstrip() else ""
        trailing_space = " " if original != original.rstrip() else ""
        return leading_space + new_word.strip() + trailing_space

    def _process_corrections(
        self, segments: List[LyricsSegment], gap_sequences: List[GapSequence], metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[WordCorrection], List[LyricsSegment], List[CorrectionStep], Dict[str, str], Dict[str, str]]:
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
        correction_steps = []
        all_corrections = []
        word_id_map = {}
        segment_id_map = {}

        # Create word map for handlers - include both transcribed and reference words
        word_map = {w.id: w for s in segments for w in s.words}  # Transcribed words

        # Add reference words from all sources
        for source, lyrics_data in self.reference_lyrics.items():
            for segment in lyrics_data.segments:
                for word in segment.words:
                    if word.id not in word_map:  # Don't overwrite transcribed words
                        word_map[word.id] = word

        # Build a linear position map for words to support agentic proposals
        linear_position_map = {}
        _pos_idx = 0
        for s in segments:
            for w in s.words:
                linear_position_map[w.id] = _pos_idx
                _pos_idx += 1

        # Base handler data that all handlers need
        base_handler_data = {
            "word_map": word_map,
            "anchor_sequences": self._anchor_sequences,
            "audio_file_hash": metadata.get("audio_file_hash") if metadata else None,
        }

        for i, gap in enumerate(gap_sequences, 1):
            self.logger.info(f"Processing gap {i}/{len(gap_sequences)} at position {gap.transcription_position}")

            # Get the actual words for logging
            gap_words = [word_map[word_id] for word_id in gap.transcribed_word_ids]
            self.logger.debug(f"Gap text: '{' '.join(w.text for w in gap_words)}'")

            # Optionally, attempt agentic correction first
            try:
                import os as _os
                from lyrics_transcriber.correction.agentic.agent import AgenticCorrector as _AgenticCorrector
                from lyrics_transcriber.correction.agentic.adapter import adapt_proposals_to_word_corrections as _adapt
            except Exception:
                _AgenticCorrector = None  # type: ignore
                _adapt = None  # type: ignore

            if _AgenticCorrector and _adapt and (_os.getenv("USE_AGENTIC_AI", "").lower() in {"1", "true", "yes"}):
                try:
                    # Simple prompt using gap text and optional reference text
                    gap_text = " ".join(w.text for w in gap_words)
                    ref_text = " ".join(next(iter(self.reference_lyrics.values())).get_full_text().split()[:50]) if self.reference_lyrics else ""
                    prompt = (
                        "You are correcting transcription errors in lyrics.\n"
                        f"Transcribed gap: '{gap_text}'.\n"
                        f"Reference context (optional): '{ref_text}'.\n"
                        "Return a JSON list of proposals matching the CorrectionProposal schema."
                    )
                    # Choose model via router if available
                    try:
                        from lyrics_transcriber.correction.agentic.router import ModelRouter as _ModelRouter
                        _router = _ModelRouter()
                        # naive uncertainty estimate: short gaps => low uncertainty
                        uncertainty = 0.3 if len(gap_words) <= 2 else 0.7
                        model_id = _router.choose_model("gap", uncertainty)
                    except Exception:
                        model_id = _os.getenv("AGENTIC_AI_MODEL", "anthropic/claude-4-sonnet")
                    _agent = _AgenticCorrector(model=model_id)
                    _proposals = _agent.propose(prompt)
                    _agentic_corrections = _adapt(_proposals, word_map, linear_position_map) if _proposals else []
                    if _agentic_corrections:
                        affected_word_ids = [w.id for w in self._get_affected_words(gap, segments)]
                        affected_segment_ids = [s.id for s in self._get_affected_segments(gap, segments)]
                        updated_segments = self._apply_corrections_to_segments(self._get_affected_segments(gap, segments), _agentic_corrections)
                        for correction in _agentic_corrections:
                            if correction.word_id and correction.corrected_word_id:
                                word_id_map[correction.word_id] = correction.corrected_word_id
                        for old_seg, new_seg in zip(self._get_affected_segments(gap, segments), updated_segments):
                            segment_id_map[old_seg.id] = new_seg.id
                        step = CorrectionStep(
                            handler_name="AgenticCorrector",
                            affected_word_ids=affected_word_ids,
                            affected_segment_ids=affected_segment_ids,
                            corrections=_agentic_corrections,
                            segments_before=self._get_affected_segments(gap, segments),
                            segments_after=updated_segments,
                            created_word_ids=[w.id for w in self._get_new_words(updated_segments, affected_word_ids)],
                            deleted_word_ids=[id for id in affected_word_ids if not self._word_exists(id, updated_segments)],
                        )
                        correction_steps.append(step)
                        all_corrections.extend(_agentic_corrections)
                        # Stop trying other handlers if agentic made corrections
                        continue
                except Exception:
                    # Silent fallback to rule-based handlers
                    pass

            # Try each handler in order
            for handler in self.handlers:
                handler_name = handler.__class__.__name__
                can_handle, handler_data = handler.can_handle(gap, base_handler_data)

                if can_handle:
                    # Merge base handler data with specific handler data
                    handler_data = {**base_handler_data, **(handler_data or {})}

                    corrections = handler.handle(gap, handler_data)
                    if corrections:
                        self.logger.info(f"Handler {handler_name} made {len(corrections)} corrections")
                        # Track affected IDs
                        affected_word_ids = [w.id for w in self._get_affected_words(gap, segments)]
                        affected_segment_ids = [s.id for s in self._get_affected_segments(gap, segments)]

                        # Apply corrections and get updated segments
                        updated_segments = self._apply_corrections_to_segments(self._get_affected_segments(gap, segments), corrections)

                        # Update ID maps
                        for correction in corrections:
                            if correction.word_id and correction.corrected_word_id:
                                word_id_map[correction.word_id] = correction.corrected_word_id

                        # Map segment IDs
                        for old_seg, new_seg in zip(self._get_affected_segments(gap, segments), updated_segments):
                            segment_id_map[old_seg.id] = new_seg.id

                        # Create correction step
                        step = CorrectionStep(
                            handler_name=handler_name,
                            affected_word_ids=affected_word_ids,
                            affected_segment_ids=affected_segment_ids,
                            corrections=corrections,
                            segments_before=self._get_affected_segments(gap, segments),
                            segments_after=updated_segments,
                            created_word_ids=[w.id for w in self._get_new_words(updated_segments, affected_word_ids)],
                            deleted_word_ids=[id for id in affected_word_ids if not self._word_exists(id, updated_segments)],
                        )
                        correction_steps.append(step)
                        all_corrections.extend(corrections)

                        # Log correction details
                        for correction in corrections:
                            self.logger.info(
                                f"Made correction: '{correction.original_word}' -> '{correction.corrected_word}' "
                                f"(confidence: {correction.confidence:.2f}, reason: {correction.reason})"
                            )
                        break  # Stop trying other handlers once we've made corrections
                    else:
                        self.logger.debug(f"Handler {handler_name} found no corrections needed")
                else:
                    self.logger.debug(f"Handler {handler_name} cannot handle gap")

        # Create final result with correction history
        corrected_segments = self._apply_all_corrections(segments, all_corrections)
        self.logger.info(f"Correction process completed with {len(all_corrections)} total corrections")
        return all_corrections, corrected_segments, correction_steps, word_id_map, segment_id_map

    def _get_new_words(self, segments: List[LyricsSegment], original_word_ids: List[str]) -> List[Word]:
        """Find words that were created during correction."""
        return [w for s in segments for w in s.words if w.id not in original_word_ids]

    def _word_exists(self, word_id: str, segments: List[LyricsSegment]) -> bool:
        """Check if a word ID still exists in the segments."""
        return any(w.id == word_id for s in segments for w in s.words)

    def _apply_corrections_to_segments(self, segments: List[LyricsSegment], corrections: List[WordCorrection]) -> List[LyricsSegment]:
        """Apply corrections to create new segments."""
        # Create word ID map for quick lookup
        word_map = {w.id: w for s in segments for w in s.words}

        # Group corrections by original_position to handle splits
        correction_map = {}
        for c in corrections:
            if c.original_position not in correction_map:
                correction_map[c.original_position] = []
            correction_map[c.original_position].append(c)

        corrected_segments = []
        current_word_idx = 0

        for segment in segments:
            corrected_words = []
            for word in segment.words:
                if current_word_idx in correction_map:
                    word_corrections = sorted(correction_map[current_word_idx], key=lambda x: x.split_index or 0)

                    # Check if any correction has a valid split_total
                    total_splits = next((c.split_total for c in word_corrections if c.split_total is not None), None)

                    if total_splits:
                        # Handle word split
                        split_duration = (word.end_time - word.start_time) / total_splits

                        for i, correction in enumerate(word_corrections):
                            start_time = word.start_time + (i * split_duration)
                            end_time = start_time + split_duration

                            # Update corrected_position as we create new words
                            correction.corrected_position = len(corrected_words)
                            new_word = Word(
                                id=correction.corrected_word_id or WordUtils.generate_id(),
                                text=self._preserve_formatting(correction.original_word, correction.corrected_word),
                                start_time=start_time,
                                end_time=end_time,
                                confidence=correction.confidence,
                                created_during_correction=True,
                            )
                            corrected_words.append(new_word)
                    else:
                        # Handle single word replacement
                        correction = word_corrections[0]
                        if not correction.is_deletion:
                            # Update corrected_position
                            correction.corrected_position = len(corrected_words)
                            new_word = Word(
                                id=correction.corrected_word_id or WordUtils.generate_id(),
                                text=self._preserve_formatting(correction.original_word, correction.corrected_word),
                                start_time=word.start_time,
                                end_time=word.end_time,
                                confidence=correction.confidence,
                                created_during_correction=True,
                            )
                            corrected_words.append(new_word)
                else:
                    corrected_words.append(word)
                current_word_idx += 1

            if corrected_words:
                corrected_segments.append(
                    LyricsSegment(
                        id=segment.id,  # Preserve original segment ID
                        text=" ".join(w.text for w in corrected_words),
                        words=corrected_words,
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                    )
                )

        return corrected_segments

    def _get_affected_segments(self, gap: GapSequence, segments: List[LyricsSegment]) -> List[LyricsSegment]:
        """Get segments that contain words from the gap sequence."""
        affected_segments = []
        gap_word_ids = set(gap.transcribed_word_ids)

        for segment in segments:
            # Check if any words in this segment are part of the gap
            if any(w.id in gap_word_ids for w in segment.words):
                affected_segments.append(segment)
            elif affected_segments:  # We've passed the gap
                break

        return affected_segments

    def _get_affected_words(self, gap: GapSequence, segments: List[LyricsSegment]) -> List[Word]:
        """Get words that are part of the gap sequence."""
        # Create a map of word IDs to Word objects for quick lookup
        word_map = {w.id: w for s in segments for w in s.words}

        # Get the actual Word objects using the IDs
        return [word_map[word_id] for word_id in gap.transcribed_word_ids]

    def _apply_all_corrections(self, segments: List[LyricsSegment], corrections: List[WordCorrection]) -> List[LyricsSegment]:
        """Apply all corrections to create final corrected segments."""
        # Make a deep copy to avoid modifying original segments
        working_segments = deepcopy(segments)

        # Apply corrections in order
        return self._apply_corrections_to_segments(working_segments, corrections)
