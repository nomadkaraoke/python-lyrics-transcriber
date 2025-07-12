import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
from pathlib import Path
import json
import hashlib

from lyrics_transcriber.types import LyricsData, PhraseScore, PhraseType, AnchorSequence, GapSequence, ScoredAnchor, TranscriptionResult, Word
from lyrics_transcriber.correction.phrase_analyzer import PhraseAnalyzer
from lyrics_transcriber.correction.text_utils import clean_text
from lyrics_transcriber.utils.word_utils import WordUtils


class AnchorSequenceTimeoutError(Exception):
    """Raised when anchor sequence computation exceeds timeout."""
    pass


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(
        self,
        cache_dir: Union[str, Path],
        min_sequence_length: int = 3,
        min_sources: int = 1,
        timeout_seconds: int = 600,  # 10 minutes default timeout
        max_iterations_per_ngram: int = 1000,  # Maximum iterations for while loop
        progress_check_interval: int = 50,  # Check progress every N iterations
        logger: Optional[logging.Logger] = None,
    ):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.timeout_seconds = timeout_seconds
        self.max_iterations_per_ngram = max_iterations_per_ngram
        self.progress_check_interval = progress_check_interval
        self.logger = logger or logging.getLogger(__name__)
        self.phrase_analyzer = PhraseAnalyzer(logger=self.logger)
        self.used_positions = {}

        # Initialize cache directory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Initialized AnchorSequenceFinder with cache dir: {self.cache_dir}, timeout: {timeout_seconds}s")

    def _check_timeout(self, start_time: float, operation_name: str = "operation"):
        """Check if timeout has occurred and raise exception if so."""
        if self.timeout_seconds > 0:
            elapsed_time = time.time() - start_time
            if elapsed_time > self.timeout_seconds:
                raise AnchorSequenceTimeoutError(f"{operation_name} exceeded {self.timeout_seconds} seconds (elapsed: {elapsed_time:.1f}s)")

    def _clean_text(self, text: str) -> str:
        """Clean text by removing punctuation and normalizing whitespace."""
        # self.logger.debug(f"_clean_text called with text length: {len(text)}")
        return clean_text(text)

    def _find_ngrams(self, words: List[str], n: int) -> List[Tuple[List[str], int]]:
        """Generate n-grams with their starting positions."""
        # self.logger.debug(f"_find_ngrams called with {len(words)} words, n={n}")
        return [(words[i : i + n], i) for i in range(len(words) - n + 1)]

    def _find_matching_sources(self, ngram: List[str], references: Dict[str, List[str]], n: int) -> Dict[str, int]:
        """Find which sources contain the given n-gram and at what positions."""
        # self.logger.debug(f"_find_matching_sources called for ngram: '{' '.join(ngram)}'")
        matches = {}
        all_positions = {source: [] for source in references}

        # First, find all positions in each source
        for source, words in references.items():
            for i in range(len(words) - n + 1):
                if words[i : i + n] == ngram:
                    all_positions[source].append(i)

        # Then, try to find an unused position for each source
        for source, positions in all_positions.items():
            used = self.used_positions.get(source, set())
            # Try each position in order
            for pos in positions:
                if pos not in used:
                    matches[source] = pos
                    break

        return matches

    def _filter_used_positions(self, matches: Dict[str, int]) -> Dict[str, int]:
        """Filter out positions that have already been used.

        Args:
            matches: Dict mapping source IDs to positions

        Returns:
            Dict mapping source IDs to unused positions
        """
        self.logger.debug(f"_filter_used_positions called with {len(matches)} matches")
        return {source: pos for source, pos in matches.items() if pos not in self.used_positions.get(source, set())}

    def _create_anchor(
        self, ngram: List[str], trans_pos: int, matching_sources: Dict[str, int], total_sources: int
    ) -> Optional[AnchorSequence]:
        """Create an anchor sequence if it meets the minimum sources requirement."""
        self.logger.debug(f"_create_anchor called for ngram: '{' '.join(ngram)}' at position {trans_pos}")
        if len(matching_sources) >= self.min_sources:
            confidence = len(matching_sources) / total_sources
            # Use new API to avoid setting _words field
            anchor = AnchorSequence(
                id=WordUtils.generate_id(),
                transcribed_word_ids=[WordUtils.generate_id() for _ in ngram],
                transcription_position=trans_pos,
                reference_positions=matching_sources,
                reference_word_ids={source: [WordUtils.generate_id() for _ in ngram] 
                                   for source in matching_sources.keys()},
                confidence=confidence
            )
            self.logger.debug(f"Found anchor sequence: '{' '.join(ngram)}' (confidence: {confidence:.2f})")
            return anchor
        return None

    def _get_cache_key(self, transcribed: str, references: Dict[str, LyricsData], transcription_result: TranscriptionResult) -> str:
        """Generate a unique cache key for the input combination."""
        # Create a string that uniquely identifies the inputs, including word IDs
        ref_texts = []
        for source, lyrics in sorted(references.items()):
            # Include both text and ID for each word to ensure cache uniqueness
            words_with_ids = [f"{w.text}:{w.id}" for s in lyrics.segments for w in s.words]
            ref_texts.append(f"{source}:{','.join(words_with_ids)}")

        # Also include transcription word IDs to ensure complete matching
        trans_words_with_ids = [f"{w.text}:{w.id}" for s in transcription_result.result.segments for w in s.words]

        input_str = f"{transcribed}|" f"{','.join(trans_words_with_ids)}|" f"{','.join(ref_texts)}"
        return hashlib.md5(input_str.encode()).hexdigest()

    def _save_to_cache(self, cache_path: Path, anchors: List[ScoredAnchor]) -> None:
        """Save results to cache file."""
        self.logger.debug(f"Saving to cache: {cache_path}")
        # Convert to dictionary format that matches the expected loading format
        cache_data = [{"anchor": anchor.anchor.to_dict(), "phrase_score": anchor.phrase_score.to_dict()} for anchor in anchors]
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    def _load_from_cache(self, cache_path: Path) -> Optional[List[ScoredAnchor]]:
        """Load results from cache if available."""
        try:
            self.logger.debug(f"Attempting to load from cache: {cache_path}")
            with open(cache_path, "r") as f:
                cached_data = json.load(f)

            self.logger.info("Loading anchors from cache")
            try:
                # Log the raw dictionary data instead of the object
                # if cached_data:
                #     self.logger.debug(f"Cached data structure: {json.dumps(cached_data[0], indent=2)}")

                # Convert cached data back to ScoredAnchor objects
                anchors = []
                for data in cached_data:
                    if "anchor" not in data or "phrase_score" not in data:
                        raise KeyError("Missing required keys: anchor, phrase_score")

                    anchor = AnchorSequence.from_dict(data["anchor"])
                    phrase_score = PhraseScore.from_dict(data["phrase_score"])
                    anchors.append(ScoredAnchor(anchor=anchor, phrase_score=phrase_score))

                return anchors

            except KeyError as e:
                self.logger.error(f"Cache format mismatch. Missing key: {e}")
                # Log the raw data for debugging
                if cached_data:
                    self.logger.error(f"First cached anchor data: {json.dumps(cached_data[0], indent=2)}")
                self.logger.error("Expected keys: anchor, phrase_score")
                self.logger.warning(f"Cache format mismatch: {e}. Recomputing.")
                return None

        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.debug(f"Cache miss or invalid cache file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error loading cache: {type(e).__name__}: {e}")
            return None

    def _process_ngram_length(
        self,
        n: int,
        trans_words: List[str],
        all_words: List[Word],
        ref_texts_clean: Dict[str, List[str]],
        ref_words: Dict[str, List[Word]],
        min_sources: int,
    ) -> List[AnchorSequence]:
        """Process a single n-gram length to find matching sequences with timeout and early termination."""
        self.logger.info(f"🔍 N-GRAM {n}: Starting processing with {len(trans_words)} transcription words")
        self.logger.info(f"🔍 N-GRAM {n}: Reference sources: {list(ref_texts_clean.keys())}")
        self.logger.info(f"🔍 N-GRAM {n}: Max iterations limit: {self.max_iterations_per_ngram}")
        
        candidate_anchors = []
        used_positions = {source: set() for source in ref_texts_clean.keys()}
        used_trans_positions = set()
        
        iteration_count = 0
        last_progress_check = 0
        last_anchor_count = 0
        stagnation_count = 0
        
        self.logger.debug(f"🔍 N-GRAM {n}: Processing n-gram length {n} with max {self.max_iterations_per_ngram} iterations")

        # Generate n-grams from transcribed text once
        trans_ngrams = self._find_ngrams(trans_words, n)
        self.logger.info(f"🔍 N-GRAM {n}: Generated {len(trans_ngrams)} n-grams for processing")

        # Process all n-grams efficiently in multiple passes
        found_new_match = True
        while found_new_match and iteration_count < self.max_iterations_per_ngram:
            found_new_match = False
            iteration_count += 1
            anchors_found_this_iteration = 0

            # Log every 10th iteration to track progress
            if iteration_count % 10 == 0:
                self.logger.debug(f"🔍 N-GRAM {n}: Iteration {iteration_count}, anchors found: {len(candidate_anchors)}")

            # Check for progress stagnation every N iterations
            if iteration_count - last_progress_check >= self.progress_check_interval:
                current_anchor_count = len(candidate_anchors)
                if current_anchor_count == last_anchor_count:
                    stagnation_count += 1
                    self.logger.debug(f"🔍 N-GRAM {n}: Stagnation check {stagnation_count}/3 at iteration {iteration_count}")
                    if stagnation_count >= 3:  # No progress for 3 consecutive checks
                        self.logger.info(f"🔍 N-GRAM {n}: ⏹️ Early termination due to stagnation after {iteration_count} iterations")
                        break
                else:
                    stagnation_count = 0  # Reset stagnation counter
                
                last_anchor_count = current_anchor_count
                last_progress_check = iteration_count
                
                self.logger.debug(f"🔍 N-GRAM {n}: iteration {iteration_count}, anchors: {current_anchor_count}, stagnation: {stagnation_count}")

            # Process all n-grams in this iteration
            for ngram, trans_pos in trans_ngrams:
                # Skip if we've already used this transcription position
                if trans_pos in used_trans_positions:
                    continue

                # Get the actual words from the transcription at this position
                actual_words = [w.text.lower().strip('.,?!"\n') for w in all_words[trans_pos : trans_pos + n]]
                ngram_words = [w.lower() for w in ngram]

                if actual_words != ngram_words:
                    self.logger.error(f"🔍 N-GRAM {n}: ❌ Mismatch between ngram and actual words at position {trans_pos}:")
                    self.logger.error(f"🔍 N-GRAM {n}: Ngram words: {ngram_words}")
                    self.logger.error(f"🔍 N-GRAM {n}: Actual words: {actual_words}")
                    self.logger.error(f"🔍 N-GRAM {n}: Full trans_words: {trans_words}")
                    self.logger.error(f"🔍 N-GRAM {n}: Full all_words: {[w.text for w in all_words]}")
                    raise AssertionError(
                        f"Ngram words don't match actual words at position {trans_pos}. "
                        f"This should never happen as trans_words should be derived from all_words."
                    )

                matches = self._find_matching_sources(ngram, ref_texts_clean, n)
                if len(matches) >= min_sources:
                    # Log successful match
                    if len(candidate_anchors) < 5:  # Only log first few matches to avoid spam
                        self.logger.debug(f"🔍 N-GRAM {n}: ✅ Found match: '{' '.join(ngram)}' at pos {trans_pos} with {len(matches)} sources")
                    
                    # Get Word IDs for transcribed words
                    transcribed_word_ids = [w.id for w in all_words[trans_pos : trans_pos + n]]

                    # Get Word IDs for reference words
                    reference_word_ids = {source: [w.id for w in ref_words[source][pos : pos + n]] for source, pos in matches.items()}

                    # Mark positions as used
                    for source, pos in matches.items():
                        used_positions[source].add(pos)
                    used_trans_positions.add(trans_pos)

                    anchor = AnchorSequence(
                        id=WordUtils.generate_id(),
                        transcribed_word_ids=transcribed_word_ids,
                        transcription_position=trans_pos,
                        reference_positions=matches,
                        reference_word_ids=reference_word_ids,
                        confidence=len(matches) / len(ref_texts_clean),
                    )
                    candidate_anchors.append(anchor)
                    anchors_found_this_iteration += 1
                    found_new_match = True
                    
                    # For efficiency, if we have very low iteration limits, find one match per iteration
                    if self.max_iterations_per_ngram <= 10:
                        break
            
            # Log progress for this iteration
            if anchors_found_this_iteration > 0:
                self.logger.debug(f"🔍 N-GRAM {n}: Found {anchors_found_this_iteration} anchors in iteration {iteration_count}")
            
            # Early termination if we've found enough anchors or processed all positions
            if len(used_trans_positions) >= len(trans_ngrams) or len(candidate_anchors) >= len(trans_ngrams):
                self.logger.info(f"🔍 N-GRAM {n}: ⏹️ Early termination - processed all positions after {iteration_count} iterations")
                break

        if iteration_count >= self.max_iterations_per_ngram:
            self.logger.warning(f"🔍 N-GRAM {n}: ⏰ Processing terminated after reaching max iterations ({self.max_iterations_per_ngram})")
        
        self.logger.info(f"🔍 N-GRAM {n}: ✅ Completed processing after {iteration_count} iterations, found {len(candidate_anchors)} anchors")
        return candidate_anchors

    def find_anchors(
        self,
        transcribed: str,
        references: Dict[str, LyricsData],
        transcription_result: TranscriptionResult,
    ) -> List[ScoredAnchor]:
        """Find anchor sequences that appear in both transcription and references with timeout protection."""
        start_time = time.time()
        
        try:
            self.logger.info(f"🔍 ANCHOR SEARCH: Starting find_anchors with timeout {self.timeout_seconds}s")
            self.logger.info(f"🔍 ANCHOR SEARCH: Transcribed text length: {len(transcribed)}")
            self.logger.info(f"🔍 ANCHOR SEARCH: Reference sources: {list(references.keys())}")
            
            cache_key = self._get_cache_key(transcribed, references, transcription_result)
            cache_path = self.cache_dir / f"anchors_{cache_key}.json"
            self.logger.info(f"🔍 ANCHOR SEARCH: Cache key: {cache_key}")

            # Try to load from cache
            self.logger.info(f"🔍 ANCHOR SEARCH: Checking cache at {cache_path}")
            if cached_data := self._load_from_cache(cache_path):
                self.logger.info("🔍 ANCHOR SEARCH: ✅ Cache hit! Loading anchors from cache")
                try:
                    # Convert cached_data to dictionary before logging
                    if cached_data:
                        first_anchor = {"anchor": cached_data[0].anchor.to_dict(), "phrase_score": cached_data[0].phrase_score.to_dict()}
                    return cached_data
                except Exception as e:
                    self.logger.error(f"🔍 ANCHOR SEARCH: ❌ Error loading cache: {type(e).__name__}: {e}")
                    if cached_data:
                        try:
                            first_anchor = {"anchor": cached_data[0].anchor.to_dict(), "phrase_score": cached_data[0].phrase_score.to_dict()}
                            self.logger.error(f"First cached anchor data: {json.dumps(first_anchor, indent=2)}")
                        except:
                            self.logger.error("Could not serialize first cached anchor for logging")

            # If not in cache or cache format invalid, perform the computation
            self.logger.info(f"🔍 ANCHOR SEARCH: ❌ Cache miss - computing anchors with timeout {self.timeout_seconds}s")
            self.logger.info(f"🔍 ANCHOR SEARCH: Finding anchor sequences for transcription with length {len(transcribed)}")

            # Check timeout before starting computation
            self._check_timeout(start_time, "anchor computation initialization")
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Timeout check passed - initialization")

            # Get all words from transcription
            self.logger.info(f"🔍 ANCHOR SEARCH: Extracting words from transcription result...")
            all_words = []
            for segment in transcription_result.result.segments:
                all_words.extend(segment.words)
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Extracted {len(all_words)} words from transcription")

            # Clean and split texts
            self.logger.info(f"🔍 ANCHOR SEARCH: Cleaning transcription words...")
            trans_words = [w.text.lower().strip('.,?!"\n') for w in all_words]
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Cleaned {len(trans_words)} transcription words")
            
            self.logger.info(f"🔍 ANCHOR SEARCH: Processing reference sources...")
            ref_texts_clean = {
                source: self._clean_text(" ".join(w.text for s in lyrics.segments for w in s.words)).split()
                for source, lyrics in references.items()
            }
            ref_words = {source: [w for s in lyrics.segments for w in s.words] for source, lyrics in references.items()}
            
            for source, words in ref_texts_clean.items():
                self.logger.info(f"🔍 ANCHOR SEARCH: Reference '{source}': {len(words)} words")

            # Check timeout after preprocessing
            self._check_timeout(start_time, "anchor computation preprocessing")
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Timeout check passed - preprocessing")

            # Filter out very short reference sources for n-gram length calculation
            self.logger.info(f"🔍 ANCHOR SEARCH: Calculating n-gram lengths...")
            valid_ref_lengths = [
                len(words) for words in ref_texts_clean.values()
                if len(words) >= self.min_sequence_length
            ]

            if not valid_ref_lengths:
                self.logger.warning("🔍 ANCHOR SEARCH: ❌ No reference sources long enough for anchor detection")
                return []

            # Calculate max length using only valid reference sources
            max_length = min(len(trans_words), min(valid_ref_lengths))
            n_gram_lengths = range(max_length, self.min_sequence_length - 1, -1)
            self.logger.info(f"🔍 ANCHOR SEARCH: N-gram lengths to process: {list(n_gram_lengths)} (max_length: {max_length})")

            # Process n-gram lengths in parallel with timeout
            self.logger.info(f"🔍 ANCHOR SEARCH: Setting up parallel processing...")
            process_length_partial = partial(
                self._process_ngram_length,
                trans_words=trans_words,
                all_words=all_words,  # Pass the Word objects
                ref_texts_clean=ref_texts_clean,
                ref_words=ref_words,
                min_sources=self.min_sources,
            )

            # Process n-gram lengths in parallel with timeout
            candidate_anchors = []
            pool_timeout = max(60, self.timeout_seconds // 2) if self.timeout_seconds > 0 else 300  # Use half the total timeout for pool operations
            
            # Check timeout before parallel processing
            self._check_timeout(start_time, "parallel processing start")
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Timeout check passed - about to start parallel processing")
            
            try:
                self.logger.info(f"🔍 ANCHOR SEARCH: 🚀 Starting parallel processing with {max(cpu_count() - 1, 1)} processes, pool timeout: {pool_timeout}s")
                with Pool(processes=max(cpu_count() - 1, 1)) as pool:
                    self.logger.debug(f"🔍 ANCHOR SEARCH: Pool created successfully")
                    results = []
                    
                    # Submit all jobs first
                    self.logger.info(f"🔍 ANCHOR SEARCH: Submitting {len(n_gram_lengths)} n-gram processing jobs...")
                    async_results = []
                    for i, n in enumerate(n_gram_lengths):
                        self.logger.debug(f"🔍 ANCHOR SEARCH: Submitting job {i+1}/{len(n_gram_lengths)} for n-gram length {n}")
                        async_result = pool.apply_async(process_length_partial, (n,))
                        async_results.append(async_result)
                    
                    self.logger.info(f"🔍 ANCHOR SEARCH: ✅ All {len(async_results)} jobs submitted")
                    
                    # Collect results with individual timeouts
                    for i, async_result in enumerate(async_results):
                        n_gram_length = n_gram_lengths[i]
                        try:
                            self.logger.info(f"🔍 ANCHOR SEARCH: ⏳ Collecting result {i+1}/{len(async_results)} for n-gram length {n_gram_length}")
                            
                            # Check remaining time for pool timeout (more lenient than overall timeout)
                            elapsed_time = time.time() - start_time
                            remaining_time = max(10, self.timeout_seconds - elapsed_time) if self.timeout_seconds > 0 else pool_timeout
                            
                            self.logger.debug(f"🔍 ANCHOR SEARCH: Remaining time for n-gram {n_gram_length}: {remaining_time}s")
                            
                            # Use a more lenient timeout for individual results to allow fallback
                            individual_timeout = min(pool_timeout, remaining_time) if self.timeout_seconds > 0 else pool_timeout
                            
                            result = async_result.get(timeout=individual_timeout)
                            results.append(result)
                            
                            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Completed n-gram length {n_gram_length} ({i+1}/{len(n_gram_lengths)}) - found {len(result)} anchors")
                            
                        except Exception as e:
                            self.logger.warning(f"🔍 ANCHOR SEARCH: ⚠️ n-gram length {n_gram_length} failed or timed out: {str(e)}")
                            results.append([])  # Add empty result to maintain order
                            
                            # If we're running short on time, trigger fallback early
                            if self.timeout_seconds > 0 and (time.time() - start_time) > (self.timeout_seconds * 0.8):
                                self.logger.warning(f"🔍 ANCHOR SEARCH: ⚠️ Approaching timeout limit, triggering early fallback")
                                # Raise exception to trigger fallback to sequential processing
                                raise Exception("Parallel processing timeout, triggering fallback")
                    
                    self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Parallel processing completed, combining results...")
                    for anchors in results:
                        candidate_anchors.extend(anchors)
                        
            except AnchorSequenceTimeoutError:
                self.logger.error(f"🔍 ANCHOR SEARCH: ❌ Parallel processing timed out")
                # Re-raise timeout errors
                raise
            except Exception as e:
                self.logger.error(f"🔍 ANCHOR SEARCH: ❌ Parallel processing failed: {str(e)}")
                # Fall back to sequential processing with timeout checks
                self.logger.info("🔍 ANCHOR SEARCH: 🔄 Falling back to sequential processing")
                for n in n_gram_lengths:
                    try:
                        # Check timeout more leniently during sequential processing
                        if self.timeout_seconds > 0:
                            elapsed_time = time.time() - start_time
                            # Allow more time for sequential processing (up to 2x the original timeout)
                            if elapsed_time > (self.timeout_seconds * 2.0):
                                self.logger.warning(f"🔍 ANCHOR SEARCH: ⏰ Sequential processing timeout for n-gram {n}")
                                break
                        
                        self.logger.info(f"🔍 ANCHOR SEARCH: 🔄 Sequential processing n-gram length {n}")
                        
                        anchors = self._process_ngram_length(
                            n, trans_words, all_words, ref_texts_clean, ref_words, self.min_sources
                        )
                        candidate_anchors.extend(anchors)
                        self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Sequential n-gram {n} completed - found {len(anchors)} anchors")
                    except Exception as e:
                        self.logger.warning(f"🔍 ANCHOR SEARCH: ⚠️ Sequential processing failed for n-gram length {n}: {str(e)}")
                        continue

            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Found {len(candidate_anchors)} candidate anchors in {time.time() - start_time:.1f}s")
            
            # Check timeout before expensive filtering operation
            self._check_timeout(start_time, "overlap filtering start")
            self.logger.info(f"🔍 ANCHOR SEARCH: 🔄 Starting overlap filtering...")
            
            filtered_anchors = self._remove_overlapping_sequences(candidate_anchors, transcribed, transcription_result)
            self.logger.info(f"🔍 ANCHOR SEARCH: ✅ Filtering completed - {len(filtered_anchors)} final anchors")

            # Save to cache
            self.logger.info(f"🔍 ANCHOR SEARCH: 💾 Saving results to cache...")
            self._save_to_cache(cache_path, filtered_anchors)
            
            total_time = time.time() - start_time
            self.logger.info(f"🔍 ANCHOR SEARCH: 🎉 Anchor sequence computation completed successfully in {total_time:.1f}s")
            
            return filtered_anchors
            
        except AnchorSequenceTimeoutError:
            elapsed_time = time.time() - start_time
            self.logger.error(f"🔍 ANCHOR SEARCH: ⏰ TIMEOUT after {elapsed_time:.1f}s (limit: {self.timeout_seconds}s)")
            raise
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"🔍 ANCHOR SEARCH: ❌ FAILED after {elapsed_time:.1f}s: {str(e)}")
            self.logger.error(f"🔍 ANCHOR SEARCH: Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"🔍 ANCHOR SEARCH: Traceback: {traceback.format_exc()}")
            raise
        finally:
            # No cleanup needed for time-based timeout checks
            pass

    def _score_sequence(self, words: List[str], context: str) -> PhraseScore:
        """Score a sequence based on its phrase quality"""
        self.logger.debug(f"_score_sequence called for: '{' '.join(words)}'")
        return self.phrase_analyzer.score_phrase(words, context)

    def _get_sequence_priority(self, scored_anchor: ScoredAnchor) -> Tuple[float, float, float, float, int]:
        """Get priority tuple for sorting sequences.

        Returns tuple of:
        - Number of sources matched (higher is better)
        - Length bonus (length * 0.2) to favor longer sequences
        - Break score (higher is better)
        - Total score (higher is better)
        - Negative position (earlier is better)

        Position bonus: Add 1.0 to total score for sequences at position 0
        """
        # self.logger.debug(f"_get_sequence_priority called for anchor: '{scored_anchor.anchor.text}'")
        position_bonus = 1.0 if scored_anchor.anchor.transcription_position == 0 else 0.0
        length_bonus = len(scored_anchor.anchor.transcribed_word_ids) * 0.2  # Changed from words to transcribed_word_ids

        return (
            len(scored_anchor.anchor.reference_positions),  # More sources is better
            length_bonus,  # Longer sequences preferred
            scored_anchor.phrase_score.natural_break_score,  # Better breaks preferred
            scored_anchor.phrase_score.total_score + position_bonus,  # Add bonus for position 0
            -scored_anchor.anchor.transcription_position,  # Earlier positions preferred
        )

    def _sequences_overlap(self, seq1: AnchorSequence, seq2: AnchorSequence) -> bool:
        """Check if two sequences overlap in either transcription or references.

        Args:
            seq1: First sequence
            seq2: Second sequence

        Returns:
            True if sequences overlap in transcription or share any reference positions
        """
        # Check transcription overlap
        seq1_trans_range = range(
            seq1.transcription_position, seq1.transcription_position + len(seq1.transcribed_word_ids)
        )  # Changed from words
        seq2_trans_range = range(
            seq2.transcription_position, seq2.transcription_position + len(seq2.transcribed_word_ids)
        )  # Changed from words
        trans_overlap = bool(set(seq1_trans_range) & set(seq2_trans_range))

        # Check reference overlap - only consider positions in shared sources
        shared_sources = set(seq1.reference_positions.keys()) & set(seq2.reference_positions.keys())
        ref_overlap = any(seq1.reference_positions[source] == seq2.reference_positions[source] for source in shared_sources)

        return trans_overlap or ref_overlap

    def _remove_overlapping_sequences(
        self,
        anchors: List[AnchorSequence],
        context: str,
        transcription_result: TranscriptionResult,
    ) -> List[ScoredAnchor]:
        """Remove overlapping sequences using phrase analysis with timeout protection."""
        self.logger.info(f"🔍 FILTERING: Starting overlap removal for {len(anchors)} anchors")
        
        if not anchors:
            self.logger.info(f"🔍 FILTERING: No anchors to process")
            return []

        self.logger.info(f"🔍 FILTERING: Scoring {len(anchors)} anchors")

        # Create word map for scoring
        word_map = {w.id: w for s in transcription_result.result.segments for w in s.words}
        self.logger.debug(f"🔍 FILTERING: Created word map with {len(word_map)} words")

        # Add word map to each anchor for scoring
        for i, anchor in enumerate(anchors):
            # For backwards compatibility, only add transcribed_words if all IDs exist in word_map
            try:
                anchor.transcribed_words = [word_map[word_id] for word_id in anchor.transcribed_word_ids]
                # Also set _words for backwards compatibility with text display
                anchor._words = [word_map[word_id].text for word_id in anchor.transcribed_word_ids]
            except KeyError:
                # This can happen in tests using backwards compatible constructors
                # Create dummy Word objects with the text from _words if available
                if hasattr(anchor, '_words') and anchor._words is not None:
                    from lyrics_transcriber.types import Word
                    from lyrics_transcriber.utils.word_utils import WordUtils
                    anchor.transcribed_words = [
                        Word(
                            id=word_id,
                            text=text,
                            start_time=i * 1.0,
                            end_time=(i + 1) * 1.0,
                            confidence=1.0
                        )
                        for i, (word_id, text) in enumerate(zip(anchor.transcribed_word_ids, anchor._words))
                    ]
                else:
                    # Create generic word objects for scoring
                    from lyrics_transcriber.types import Word
                    anchor.transcribed_words = [
                        Word(
                            id=word_id,
                            text=f"word_{i}",
                            start_time=i * 1.0,
                            end_time=(i + 1) * 1.0,
                            confidence=1.0
                        )
                        for i, word_id in enumerate(anchor.transcribed_word_ids)
                    ]

        start_time = time.time()

        # Try different pool sizes with timeout
        num_processes = max(cpu_count() - 1, 1)  # Leave one CPU free
        self.logger.info(f"🔍 FILTERING: Using {num_processes} processes for scoring")

        # Create a partial function with the context parameter fixed
        score_anchor_partial = partial(self._score_anchor_static, context=context)

        # Use multiprocessing to score anchors in parallel with timeout
        scored_anchors = []
        pool_timeout = 300  # 5 minutes for scoring phase
        
        try:
            self.logger.info(f"🔍 FILTERING: 🚀 Starting parallel scoring with timeout {pool_timeout}s")
            with Pool(processes=num_processes) as pool:
                # Submit scoring jobs with timeout
                async_results = []
                batch_size = 50
                
                self.logger.info(f"🔍 FILTERING: Splitting {len(anchors)} anchors into batches of {batch_size}")
                for i in range(0, len(anchors), batch_size):
                    batch = anchors[i:i + batch_size]
                    async_result = pool.apply_async(self._score_batch_static, (batch, context))
                    async_results.append(async_result)
                
                self.logger.info(f"🔍 FILTERING: Submitted {len(async_results)} scoring batches")
                
                # Collect results with timeout
                for i, async_result in enumerate(async_results):
                    try:
                        self.logger.debug(f"🔍 FILTERING: ⏳ Collecting batch {i+1}/{len(async_results)}")
                        batch_results = async_result.get(timeout=pool_timeout)
                        scored_anchors.extend(batch_results)
                        self.logger.debug(f"🔍 FILTERING: ✅ Completed scoring batch {i+1}/{len(async_results)}")
                    except Exception as e:
                        self.logger.warning(f"🔍 FILTERING: ⚠️ Scoring batch {i+1} failed or timed out: {str(e)}")
                        # Add basic scores for failed batch
                        start_idx = i * batch_size
                        end_idx = min((i + 1) * batch_size, len(anchors))
                        for j in range(start_idx, end_idx):
                            if j < len(anchors):
                                try:
                                    phrase_score = PhraseScore(
                                        total_score=1.0,
                                        natural_break_score=1.0,
                                        phrase_type=PhraseType.COMPLETE
                                    )
                                    scored_anchors.append(ScoredAnchor(anchor=anchors[j], phrase_score=phrase_score))
                                except:
                                    continue
                        
        except Exception as e:
            self.logger.warning(f"🔍 FILTERING: ❌ Parallel scoring failed: {str(e)}, falling back to basic scoring")
            # Fall back to basic scoring
            for anchor in anchors:
                try:
                    phrase_score = PhraseScore(
                        total_score=1.0,
                        natural_break_score=1.0,
                        phrase_type=PhraseType.COMPLETE
                    )
                    scored_anchors.append(ScoredAnchor(anchor=anchor, phrase_score=phrase_score))
                except:
                    continue

        parallel_time = time.time() - start_time
        self.logger.info(f"🔍 FILTERING: ✅ Parallel scoring completed in {parallel_time:.2f}s, scored {len(scored_anchors)} anchors")

        # Sort and filter as before
        self.logger.info(f"🔍 FILTERING: 🔄 Sorting anchors by priority...")
        scored_anchors.sort(key=self._get_sequence_priority, reverse=True)
        self.logger.info(f"🔍 FILTERING: ✅ Sorting completed")

        self.logger.info(f"🔍 FILTERING: 🔄 Filtering {len(scored_anchors)} overlapping sequences")
        filtered_scored = []
        
        for i, scored_anchor in enumerate(scored_anchors):
            # Check timeout every 100 anchors using our timeout mechanism (more lenient)
            if i % 100 == 0 and i > 0:
                # Only check timeout if we're significantly over the limit
                if self.timeout_seconds > 0:
                    elapsed_time = time.time() - start_time
                    # Use a more lenient timeout for filtering (allow 50% more time)
                    if elapsed_time > (self.timeout_seconds * 1.5):
                        self.logger.warning(f"🔍 FILTERING: ⏰ Filtering timed out, returning {len(filtered_scored)} anchors out of {len(scored_anchors)}")
                        break
                
                self.logger.debug(f"🔍 FILTERING: Progress: {i}/{len(scored_anchors)} processed, {len(filtered_scored)} kept")
            
            overlaps = False
            for existing in filtered_scored:
                if self._sequences_overlap(scored_anchor.anchor, existing.anchor):
                    overlaps = True
                    break

            if not overlaps:
                filtered_scored.append(scored_anchor)

        self.logger.info(f"🔍 FILTERING: ✅ Filtering completed - kept {len(filtered_scored)} non-overlapping anchors out of {len(scored_anchors)}")
        return filtered_scored

    @staticmethod
    def _score_anchor_static(anchor: AnchorSequence, context: str) -> ScoredAnchor:
        """Static version of _score_anchor for multiprocessing compatibility."""
        # Create analyzer only once per process
        if not hasattr(AnchorSequenceFinder._score_anchor_static, "_phrase_analyzer"):
            AnchorSequenceFinder._score_anchor_static._phrase_analyzer = PhraseAnalyzer(logger=logging.getLogger(__name__))

        # Get the words from the transcribed word IDs
        # We need to pass in the actual words for scoring
        words = [w.text for w in anchor.transcribed_words]  # This needs to be passed in

        phrase_score = AnchorSequenceFinder._score_anchor_static._phrase_analyzer.score_phrase(words, context)
        return ScoredAnchor(anchor=anchor, phrase_score=phrase_score)

    @staticmethod
    def _score_batch_static(anchors: List[AnchorSequence], context: str) -> List[ScoredAnchor]:
        """Score a batch of anchors for better timeout handling."""
        # Create analyzer only once per process
        if not hasattr(AnchorSequenceFinder._score_batch_static, "_phrase_analyzer"):
            AnchorSequenceFinder._score_batch_static._phrase_analyzer = PhraseAnalyzer(logger=logging.getLogger(__name__))

        scored_anchors = []
        for anchor in anchors:
            try:
                words = [w.text for w in anchor.transcribed_words]
                phrase_score = AnchorSequenceFinder._score_batch_static._phrase_analyzer.score_phrase(words, context)
                scored_anchors.append(ScoredAnchor(anchor=anchor, phrase_score=phrase_score))
            except Exception:
                # Add basic score for failed anchor
                phrase_score = PhraseScore(
                    total_score=1.0,
                    natural_break_score=1.0,
                    phrase_type=PhraseType.COMPLETE
                )
                scored_anchors.append(ScoredAnchor(anchor=anchor, phrase_score=phrase_score))
        
        return scored_anchors

    def _get_reference_words(self, source: str, ref_words: List[str], start_pos: Optional[int], end_pos: Optional[int]) -> List[str]:
        """Get words from reference text between two positions.

        Args:
            source: Reference source identifier
            ref_words: List of words from the reference text
            start_pos: Starting position (None for beginning)
            end_pos: Ending position (None for end)

        Returns:
            List of words between the positions
        """
        if start_pos is None:
            start_pos = 0
        if end_pos is None:
            end_pos = len(ref_words)
        return ref_words[start_pos:end_pos]

    def find_gaps(
        self,
        transcribed: str,
        anchors: List[ScoredAnchor],
        references: Dict[str, LyricsData],
        transcription_result: TranscriptionResult,
    ) -> List[GapSequence]:
        """Find gaps between anchor sequences in the transcribed text."""
        # Get all words from transcription
        all_words = []
        for segment in transcription_result.result.segments:
            all_words.extend(segment.words)

        # Clean and split reference texts
        ref_texts_clean = {
            source: self._clean_text(" ".join(w.text for s in lyrics.segments for w in s.words)).split()
            for source, lyrics in references.items()
        }
        ref_words = {source: [w for s in lyrics.segments for w in s.words] for source, lyrics in references.items()}

        # Create gaps with Word IDs
        gaps = []
        sorted_anchors = sorted(anchors, key=lambda x: x.anchor.transcription_position)

        # Handle initial gap
        if sorted_anchors:
            first_anchor = sorted_anchors[0].anchor
            first_anchor_pos = first_anchor.transcription_position
            if first_anchor_pos > 0:
                gap_word_ids = [w.id for w in all_words[:first_anchor_pos]]
                if gap := self._create_initial_gap(
                    id=WordUtils.generate_id(),
                    transcribed_word_ids=gap_word_ids,
                    transcription_position=0,
                    following_anchor_id=first_anchor.id,
                    ref_texts_clean=ref_texts_clean,
                    ref_words=ref_words,
                    following_anchor=first_anchor,
                ):
                    gaps.append(gap)

        # Handle gaps between anchors
        for i in range(len(sorted_anchors) - 1):
            current_anchor = sorted_anchors[i].anchor
            next_anchor = sorted_anchors[i + 1].anchor
            gap_start = current_anchor.transcription_position + len(current_anchor.transcribed_word_ids)
            gap_end = next_anchor.transcription_position

            if gap_end > gap_start:
                gap_word_ids = [w.id for w in all_words[gap_start:gap_end]]
                if between_gap := self._create_between_gap(
                    id=WordUtils.generate_id(),
                    transcribed_word_ids=gap_word_ids,
                    transcription_position=gap_start,
                    preceding_anchor_id=current_anchor.id,
                    following_anchor_id=next_anchor.id,
                    ref_texts_clean=ref_texts_clean,
                    ref_words=ref_words,
                    preceding_anchor=current_anchor,
                    following_anchor=next_anchor,
                ):
                    gaps.append(between_gap)

        # Handle final gap
        if sorted_anchors:
            last_anchor = sorted_anchors[-1].anchor
            last_pos = last_anchor.transcription_position + len(last_anchor.transcribed_word_ids)
            if last_pos < len(all_words):
                gap_word_ids = [w.id for w in all_words[last_pos:]]
                if final_gap := self._create_final_gap(
                    id=WordUtils.generate_id(),
                    transcribed_word_ids=gap_word_ids,
                    transcription_position=last_pos,
                    preceding_anchor_id=last_anchor.id,
                    ref_texts_clean=ref_texts_clean,
                    ref_words=ref_words,
                    preceding_anchor=last_anchor,
                ):
                    gaps.append(final_gap)

        return gaps

    def _create_initial_gap(
        self,
        id: str,
        transcribed_word_ids: List[str],
        transcription_position: int,
        following_anchor_id: str,
        ref_texts_clean: Dict[str, List[str]],
        ref_words: Dict[str, List[Word]],
        following_anchor: AnchorSequence,
    ) -> Optional[GapSequence]:
        """Create gap sequence before the first anchor.

        The gap includes all reference words from the start of each reference
        up to the position where the following anchor starts in that reference.
        """
        if transcription_position > 0:
            # Get reference word IDs for the gap
            reference_word_ids = {}
            for source, words in ref_words.items():
                if source in ref_texts_clean:
                    # Get the position where the following anchor starts in this source
                    if source in following_anchor.reference_positions:
                        end_pos = following_anchor.reference_positions[source]
                        # Include all words from start up to the anchor
                        reference_word_ids[source] = [w.id for w in words[:end_pos]]
                    else:
                        # If this source doesn't contain the following anchor,
                        # we can't determine the gap content for it
                        reference_word_ids[source] = []

            return GapSequence(
                id=id,
                transcribed_word_ids=transcribed_word_ids,
                transcription_position=transcription_position,
                preceding_anchor_id=None,
                following_anchor_id=following_anchor_id,
                reference_word_ids=reference_word_ids,
            )
        return None

    def _create_between_gap(
        self,
        id: str,
        transcribed_word_ids: List[str],
        transcription_position: int,
        preceding_anchor_id: str,
        following_anchor_id: str,
        ref_texts_clean: Dict[str, List[str]],
        ref_words: Dict[str, List[Word]],
        preceding_anchor: AnchorSequence,
        following_anchor: AnchorSequence,
    ) -> Optional[GapSequence]:
        """Create gap sequence between two anchors.

        For each reference source, the gap includes all words between the end of the
        preceding anchor and the start of the following anchor in that source.
        """
        # Get reference word IDs for the gap
        reference_word_ids = {}
        for source, words in ref_words.items():
            if source in ref_texts_clean:
                # Only process sources that contain both anchors
                if source in preceding_anchor.reference_positions and source in following_anchor.reference_positions:
                    start_pos = preceding_anchor.reference_positions[source] + len(preceding_anchor.reference_word_ids[source])
                    end_pos = following_anchor.reference_positions[source]
                    # Include all words between the anchors
                    reference_word_ids[source] = [w.id for w in words[start_pos:end_pos]]
                else:
                    # If this source doesn't contain both anchors,
                    # we can't determine the gap content for it
                    reference_word_ids[source] = []

        return GapSequence(
            id=id,
            transcribed_word_ids=transcribed_word_ids,
            transcription_position=transcription_position,
            preceding_anchor_id=preceding_anchor_id,
            following_anchor_id=following_anchor_id,
            reference_word_ids=reference_word_ids,
        )

    def _create_final_gap(
        self,
        id: str,
        transcribed_word_ids: List[str],
        transcription_position: int,
        preceding_anchor_id: str,
        ref_texts_clean: Dict[str, List[str]],
        ref_words: Dict[str, List[Word]],
        preceding_anchor: AnchorSequence,
    ) -> Optional[GapSequence]:
        """Create gap sequence after the last anchor.

        For each reference source, includes all words from the end of the
        preceding anchor to the end of that reference.
        """
        # Get reference word IDs for the gap
        reference_word_ids = {}
        for source, words in ref_words.items():
            if source in ref_texts_clean:
                if source in preceding_anchor.reference_positions:
                    start_pos = preceding_anchor.reference_positions[source] + len(preceding_anchor.reference_word_ids[source])
                    # Include all words from end of last anchor to end of reference
                    reference_word_ids[source] = [w.id for w in words[start_pos:]]
                else:
                    # If this source doesn't contain the preceding anchor,
                    # we can't determine the gap content for it
                    reference_word_ids[source] = []

        return GapSequence(
            id=id,
            transcribed_word_ids=transcribed_word_ids,
            transcription_position=transcription_position,
            preceding_anchor_id=preceding_anchor_id,
            following_anchor_id=None,
            reference_word_ids=reference_word_ids,
        )
