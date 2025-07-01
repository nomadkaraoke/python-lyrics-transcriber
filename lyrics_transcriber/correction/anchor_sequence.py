from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
import time
from pathlib import Path
import json
import hashlib

from lyrics_transcriber.types import LyricsData, PhraseScore, AnchorSequence, GapSequence, ScoredAnchor, TranscriptionResult, Word
from lyrics_transcriber.correction.phrase_analyzer import PhraseAnalyzer
from lyrics_transcriber.correction.text_utils import clean_text
from lyrics_transcriber.utils.word_utils import WordUtils


class AnchorSequenceFinder:
    """Identifies and manages anchor sequences between transcribed and reference lyrics."""

    def __init__(
        self,
        cache_dir: Union[str, Path],
        min_sequence_length: int = 3,
        min_sources: int = 1,
        logger: Optional[logging.Logger] = None,
    ):
        self.min_sequence_length = min_sequence_length
        self.min_sources = min_sources
        self.logger = logger or logging.getLogger(__name__)
        self.phrase_analyzer = PhraseAnalyzer(logger=self.logger)
        self.used_positions = {}

        # Initialize cache directory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Initialized AnchorSequenceFinder with cache dir: {self.cache_dir}")

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
        """Process a single n-gram length to find matching sequences."""
        candidate_anchors = []
        used_positions = {source: set() for source in ref_texts_clean.keys()}
        used_trans_positions = set()

        found_new_match = True
        while found_new_match:
            found_new_match = False

            # Generate n-grams from transcribed text
            trans_ngrams = self._find_ngrams(trans_words, n)

            for ngram, trans_pos in trans_ngrams:
                # Skip if we've already used this transcription position
                if trans_pos in used_trans_positions:
                    continue

                # Get the actual words from the transcription at this position
                actual_words = [w.text.lower().strip('.,?!"\n') for w in all_words[trans_pos : trans_pos + n]]
                ngram_words = [w.lower() for w in ngram]

                if actual_words != ngram_words:
                    self.logger.error(f"Mismatch between ngram and actual words at position {trans_pos}:")
                    self.logger.error(f"Ngram words: {ngram_words}")
                    self.logger.error(f"Actual words: {actual_words}")
                    self.logger.error(f"Full trans_words: {trans_words}")
                    self.logger.error(f"Full all_words: {[w.text for w in all_words]}")
                    raise AssertionError(
                        f"Ngram words don't match actual words at position {trans_pos}. "
                        f"This should never happen as trans_words should be derived from all_words."
                    )

                matches = self._find_matching_sources(ngram, ref_texts_clean, n)
                if len(matches) >= min_sources:
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
                    found_new_match = True
                    break

        return candidate_anchors

    def find_anchors(
        self,
        transcribed: str,
        references: Dict[str, LyricsData],
        transcription_result: TranscriptionResult,
    ) -> List[ScoredAnchor]:
        """Find anchor sequences that appear in both transcription and references."""
        cache_key = self._get_cache_key(transcribed, references, transcription_result)
        cache_path = self.cache_dir / f"anchors_{cache_key}.json"

        # Try to load from cache
        if cached_data := self._load_from_cache(cache_path):
            self.logger.info("Loading anchors from cache")
            try:
                # Convert cached_data to dictionary before logging
                if cached_data:
                    first_anchor = {"anchor": cached_data[0].anchor.to_dict(), "phrase_score": cached_data[0].phrase_score.to_dict()}
                return cached_data
            except Exception as e:
                self.logger.error(f"Unexpected error loading cache: {type(e).__name__}: {e}")
                if cached_data:
                    try:
                        first_anchor = {"anchor": cached_data[0].anchor.to_dict(), "phrase_score": cached_data[0].phrase_score.to_dict()}
                        self.logger.error(f"First cached anchor data: {json.dumps(first_anchor, indent=2)}")
                    except:
                        self.logger.error("Could not serialize first cached anchor for logging")

        # If not in cache or cache format invalid, perform the computation
        self.logger.info(f"Cache miss for key {cache_key} - computing anchors")
        self.logger.info(f"Finding anchor sequences for transcription with length {len(transcribed)}")

        # Get all words from transcription
        all_words = []
        for segment in transcription_result.result.segments:
            all_words.extend(segment.words)

        # Clean and split texts
        trans_words = [w.text.lower().strip('.,?!"\n') for w in all_words]
        ref_texts_clean = {
            source: self._clean_text(" ".join(w.text for s in lyrics.segments for w in s.words)).split()
            for source, lyrics in references.items()
        }
        ref_words = {source: [w for s in lyrics.segments for w in s.words] for source, lyrics in references.items()}

        # Filter out very short reference sources for n-gram length calculation
        valid_ref_lengths = [
            len(words) for words in ref_texts_clean.values()
            if len(words) >= self.min_sequence_length
        ]

        if not valid_ref_lengths:
            self.logger.warning("No reference sources long enough for anchor detection")
            return []

        # Calculate max length using only valid reference sources
        max_length = min(len(trans_words), min(valid_ref_lengths))
        n_gram_lengths = range(max_length, self.min_sequence_length - 1, -1)

        # Process n-gram lengths in parallel
        process_length_partial = partial(
            self._process_ngram_length,
            trans_words=trans_words,
            all_words=all_words,  # Pass the Word objects
            ref_texts_clean=ref_texts_clean,
            ref_words=ref_words,
            min_sources=self.min_sources,
        )

        # Process n-gram lengths in parallel
        candidate_anchors = []
        with Pool(processes=max(cpu_count() - 1, 1)) as pool:
            results = list(
                tqdm(
                    pool.imap(process_length_partial, n_gram_lengths, chunksize=1),
                    total=len(n_gram_lengths),
                    desc="Processing n-gram lengths",
                )
            )
            for anchors in results:
                candidate_anchors.extend(anchors)

        self.logger.info(f"Found {len(candidate_anchors)} candidate anchors")
        filtered_anchors = self._remove_overlapping_sequences(candidate_anchors, transcribed, transcription_result)

        # Save to cache
        self._save_to_cache(cache_path, filtered_anchors)
        return filtered_anchors

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
        """Remove overlapping sequences using phrase analysis."""
        if not anchors:
            return []

        self.logger.info(f"Scoring {len(anchors)} anchors")

        # Create word map for scoring
        word_map = {w.id: w for s in transcription_result.result.segments for w in s.words}

        # Add word map to each anchor for scoring
        for anchor in anchors:
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

        # Try different pool sizes
        num_processes = max(cpu_count() - 1, 1)  # Leave one CPU free
        self.logger.info(f"Using {num_processes} processes")

        # Create a partial function with the context parameter fixed
        score_anchor_partial = partial(self._score_anchor_static, context=context)

        # Use multiprocessing to score anchors in parallel
        with Pool(processes=num_processes) as pool:
            scored_anchors = list(
                tqdm(
                    pool.imap(score_anchor_partial, anchors, chunksize=50),
                    total=len(anchors),
                    desc="Scoring anchors (parallel)",
                )
            )

        parallel_time = time.time() - start_time
        self.logger.info(f"Parallel scoring took {parallel_time:.2f} seconds")

        # Sort and filter as before
        scored_anchors.sort(key=self._get_sequence_priority, reverse=True)

        self.logger.info(f"Filtering {len(scored_anchors)} overlapping sequences")
        filtered_scored = []
        for scored_anchor in tqdm(scored_anchors, desc="Filtering overlaps"):
            overlaps = False
            for existing in filtered_scored:
                if self._sequences_overlap(scored_anchor.anchor, existing.anchor):
                    overlaps = True
                    break

            if not overlaps:
                filtered_scored.append(scored_anchor)

        self.logger.info(f"Filtered down to {len(filtered_scored)} non-overlapping anchors")
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
