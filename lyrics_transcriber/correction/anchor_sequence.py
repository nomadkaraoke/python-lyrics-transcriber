from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
import time
from pathlib import Path
import json
import hashlib

from lyrics_transcriber.types import PhraseScore, AnchorSequence, GapSequence, ScoredAnchor
from lyrics_transcriber.correction.phrase_analyzer import PhraseAnalyzer
from lyrics_transcriber.correction.text_utils import clean_text


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
            anchor = AnchorSequence(
                words=ngram, transcription_position=trans_pos, reference_positions=matching_sources, confidence=confidence
            )
            self.logger.debug(f"Found anchor sequence: '{' '.join(ngram)}' (confidence: {confidence:.2f})")
            return anchor
        return None

    def _get_cache_key(self, transcribed: str, references: Dict[str, str]) -> str:
        """Generate a unique cache key for the input combination."""
        # Create a string that uniquely identifies the inputs
        input_str = f"{transcribed}|{'|'.join(f'{k}:{v}' for k,v in sorted(references.items()))}"
        return hashlib.md5(input_str.encode()).hexdigest()

    def _save_to_cache(self, cache_path: Path, data: Any) -> None:
        """Save results to cache file."""
        self.logger.debug(f"Saving to cache: {cache_path}")
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_from_cache(self, cache_path: Path) -> Optional[Any]:
        """Load results from cache if available."""
        try:
            self.logger.debug(f"Attempting to load from cache: {cache_path}")
            with open(cache_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.debug("Cache miss or invalid cache file")
            return None

    def _process_ngram_length(
        self, n: int, trans_words: List[str], ref_texts_clean: Dict[str, List[str]], min_sources: int
    ) -> List[AnchorSequence]:
        """Process a single n-gram length to find matching sequences."""
        candidate_anchors = []
        used_positions = {source: set() for source in ref_texts_clean.keys()}
        used_trans_positions = set()

        # Try each position in the transcribed text multiple times
        # to catch repeated phrases
        found_new_match = True
        while found_new_match:
            found_new_match = False

            # Generate n-grams from transcribed text
            trans_ngrams = self._find_ngrams(trans_words, n)

            for ngram, trans_pos in trans_ngrams:
                # Skip if we've already used this transcription position
                if trans_pos in used_trans_positions:
                    continue

                matches = self._find_matching_sources(ngram, ref_texts_clean, n)
                if len(matches) >= min_sources:
                    # Mark positions as used
                    for source, pos in matches.items():
                        used_positions[source].add(pos)
                    used_trans_positions.add(trans_pos)

                    anchor = AnchorSequence(ngram, trans_pos, matches, len(matches) / len(ref_texts_clean))
                    candidate_anchors.append(anchor)
                    found_new_match = True
                    break  # Start over to try finding more matches

        return candidate_anchors

    def find_anchors(self, transcribed: str, references: Dict[str, str]) -> List[ScoredAnchor]:
        """Find anchor sequences that appear in both transcription and references."""
        cache_key = self._get_cache_key(transcribed, references)
        cache_path = self.cache_dir / f"anchors_{cache_key}.json"

        # Try to load from cache
        if cached_data := self._load_from_cache(cache_path):
            self.logger.info("Loading anchors from cache")
            try:
                return [ScoredAnchor.from_dict(anchor) for anchor in cached_data]
            except KeyError as e:
                self.logger.warning(f"Cache format mismatch: {e}. Recomputing.")

        # If not in cache or cache format invalid, perform the computation
        self.logger.info("Cache miss - computing anchors")
        self.logger.info(f"Finding anchor sequences for transcription with length {len(transcribed)}")

        # Clean and split texts
        trans_words = self._clean_text(transcribed).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in references.items()}

        max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))
        n_gram_lengths = range(max_length, self.min_sequence_length - 1, -1)

        # Set up parallel processing
        num_processes = max(cpu_count() - 1, 1)  # Leave one CPU free
        self.logger.info(f"Processing {len(n_gram_lengths)} n-gram lengths using {num_processes} processes")

        # Create partial function with fixed arguments
        process_length_partial = partial(
            self._process_ngram_length, trans_words=trans_words, ref_texts_clean=ref_texts_clean, min_sources=self.min_sources
        )

        # Process n-gram lengths in parallel
        candidate_anchors = []
        with Pool(processes=num_processes) as pool:
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
        filtered_anchors = self._remove_overlapping_sequences(candidate_anchors, transcribed)

        # Before returning, save to cache with correct format
        self._save_to_cache(
            cache_path, [{"anchor": anchor.anchor.to_dict(), "phrase_score": anchor.phrase_score.to_dict()} for anchor in filtered_anchors]
        )

        return filtered_anchors

    def _score_sequence(self, words: List[str], context: str) -> PhraseScore:
        """Score a sequence based on its phrase quality"""
        self.logger.debug(f"_score_sequence called for: '{' '.join(words)}'")
        return self.phrase_analyzer.score_phrase(words, context)

    def _score_anchor(self, anchor: AnchorSequence, context: str) -> ScoredAnchor:
        """Score an anchor sequence based on phrase quality and line breaks.

        Args:
            anchor: The anchor sequence to score
            context: The original transcribed text
        """
        # Let phrase_analyzer handle all scoring including line breaks
        phrase_score = self.phrase_analyzer.score_phrase(anchor.words, context)

        # self.logger.debug(f"_score_anchor called for sequence: '{anchor.text}'")
        return ScoredAnchor(anchor=anchor, phrase_score=phrase_score)

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
        length_bonus = len(scored_anchor.anchor.words) * 0.2  # Add bonus for longer sequences

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
        seq1_trans_range = range(seq1.transcription_position, seq1.transcription_position + len(seq1.words))
        seq2_trans_range = range(seq2.transcription_position, seq2.transcription_position + len(seq2.words))
        trans_overlap = bool(set(seq1_trans_range) & set(seq2_trans_range))

        # Check reference overlap - only consider positions in shared sources
        shared_sources = set(seq1.reference_positions.keys()) & set(seq2.reference_positions.keys())
        ref_overlap = any(seq1.reference_positions[source] == seq2.reference_positions[source] for source in shared_sources)

        # self.logger.debug(f"Checking overlap between '{seq1.text}' and '{seq2.text}'")
        return trans_overlap or ref_overlap

    def _remove_overlapping_sequences(self, anchors: List[AnchorSequence], context: str) -> List[ScoredAnchor]:
        """Remove overlapping sequences using phrase analysis."""
        if not anchors:
            return []

        self.logger.info(f"Scoring {len(anchors)} anchors")

        # Benchmark both approaches
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
                    pool.imap(score_anchor_partial, anchors, chunksize=50),  # Added chunksize
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

        phrase_score = AnchorSequenceFinder._score_anchor_static._phrase_analyzer.score_phrase(anchor.words, context)
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

    def find_gaps(self, transcribed: str, anchors: List[ScoredAnchor], references: Dict[str, str]) -> List[GapSequence]:
        """Find gaps between anchor sequences in the transcribed text."""
        cache_key = self._get_cache_key(transcribed, references)
        cache_path = self.cache_dir / f"gaps_{cache_key}.json"

        # Try to load from cache
        if cached_data := self._load_from_cache(cache_path):
            self.logger.info("Loading gaps from cache")
            return [GapSequence.from_dict(gap) for gap in cached_data]

        # If not in cache, perform the computation
        self.logger.info("Cache miss - computing gaps")
        words = self._clean_text(transcribed).split()
        ref_texts_clean = {source: self._clean_text(text).split() for source, text in references.items()}
        # Store original reference texts split into words
        ref_texts_original = {source: text.split() for source, text in references.items()}

        gaps = []
        sorted_anchors = sorted(anchors, key=lambda x: x.anchor.transcription_position)

        # Handle initial gap
        if initial_gap := self._create_initial_gap(
            words, sorted_anchors[0] if sorted_anchors else None, ref_texts_clean, ref_texts_original
        ):
            gaps.append(initial_gap)

        # Handle gaps between anchors
        for i in range(len(sorted_anchors) - 1):
            if between_gap := self._create_between_gap(
                words, sorted_anchors[i], sorted_anchors[i + 1], ref_texts_clean, ref_texts_original
            ):
                gaps.append(between_gap)

        # Handle final gap
        if sorted_anchors and (final_gap := self._create_final_gap(words, sorted_anchors[-1], ref_texts_clean, ref_texts_original)):
            gaps.append(final_gap)

        # Save to cache
        self._save_to_cache(cache_path, [gap.to_dict() for gap in gaps])
        return gaps

    def _create_initial_gap(
        self,
        words: List[str],
        first_anchor: Optional[ScoredAnchor],
        ref_texts_clean: Dict[str, List[str]],
        ref_texts_original: Dict[str, List[str]],
    ) -> Optional[GapSequence]:
        """Create gap sequence before the first anchor."""
        if not first_anchor:
            ref_words = {source: words for source, words in ref_texts_clean.items()}
            ref_words_original = {source: words for source, words in ref_texts_original.items()}
            return GapSequence(words, 0, None, None, ref_words, ref_words_original)

        if first_anchor.anchor.transcription_position > 0:
            ref_words = {}
            ref_words_original = {}
            for source in ref_texts_clean:
                end_pos = first_anchor.anchor.reference_positions.get(source)
                ref_words[source] = self._get_reference_words(source, ref_texts_clean[source], None, end_pos)
                ref_words_original[source] = self._get_reference_words(source, ref_texts_original[source], None, end_pos)

            return GapSequence(
                words[: first_anchor.anchor.transcription_position], 0, None, first_anchor.anchor, ref_words, ref_words_original
            )
        return None

    def _create_between_gap(
        self,
        words: List[str],
        current_anchor: ScoredAnchor,
        next_anchor: ScoredAnchor,
        ref_texts_clean: Dict[str, List[str]],
        ref_texts_original: Dict[str, List[str]],
    ) -> Optional[GapSequence]:
        """Create gap sequence between two anchors."""
        gap_start = current_anchor.anchor.transcription_position + current_anchor.anchor.length
        gap_end = next_anchor.anchor.transcription_position

        if gap_end > gap_start:
            ref_words = {}
            ref_words_original = {}
            shared_sources = set(current_anchor.anchor.reference_positions.keys()) & set(next_anchor.anchor.reference_positions.keys())

            # Check for large position differences in next_anchor
            if len(next_anchor.anchor.reference_positions) > 1:
                positions = list(next_anchor.anchor.reference_positions.values())
                max_diff = max(positions) - min(positions)
                if max_diff > 20:
                    earliest_source = min(next_anchor.anchor.reference_positions.items(), key=lambda x: x[1])[0]
                    self.logger.warning(
                        f"Large position difference ({max_diff} words) in next anchor. Using only earliest source: {earliest_source}"
                    )
                    shared_sources &= {earliest_source}

            for source in shared_sources:
                start_pos = current_anchor.anchor.reference_positions[source] + current_anchor.anchor.length
                end_pos = next_anchor.anchor.reference_positions[source]
                ref_words[source] = self._get_reference_words(source, ref_texts_clean[source], start_pos, end_pos)
                ref_words_original[source] = self._get_reference_words(source, ref_texts_original[source], start_pos, end_pos)

            return GapSequence(
                words[gap_start:gap_end], gap_start, current_anchor.anchor, next_anchor.anchor, ref_words, ref_words_original
            )
        return None

    def _create_final_gap(
        self, words: List[str], last_anchor: ScoredAnchor, ref_texts_clean: Dict[str, List[str]], ref_texts_original: Dict[str, List[str]]
    ) -> Optional[GapSequence]:
        """Create gap sequence after the last anchor."""
        last_pos = last_anchor.anchor.transcription_position + last_anchor.anchor.length
        if last_pos < len(words):
            ref_words = {}
            ref_words_original = {}
            for source in ref_texts_clean:
                if source in last_anchor.anchor.reference_positions:
                    start_pos = last_anchor.anchor.reference_positions[source] + last_anchor.anchor.length
                    ref_words[source] = self._get_reference_words(source, ref_texts_clean[source], start_pos, None)
                    ref_words_original[source] = self._get_reference_words(source, ref_texts_original[source], start_pos, None)

            return GapSequence(words[last_pos:], last_pos, last_anchor.anchor, None, ref_words, ref_words_original)
        return None
