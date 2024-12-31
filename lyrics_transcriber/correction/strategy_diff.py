import logging
import difflib
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from ..transcribers.base_transcriber import TranscriptionData, LyricsSegment, Word, TranscriptionResult
from ..lyrics.base_lyrics_provider import LyricsData
from .base_strategy import CorrectionResult, CorrectionStrategy, WordCorrection


@dataclass
class CorrectionEntry:
    """Stores information about potential corrections for a word."""

    sources: Set[str] = field(default_factory=set)
    frequencies: Dict[str, int] = field(default_factory=dict)
    cases: Dict[str, Dict[str, int]] = field(default_factory=lambda: {})

    def add_correction(self, correction: str, source: str, preserve_case: bool = False) -> None:
        """Add a correction instance."""
        self.sources.add(source)

        # Update frequency count
        if correction not in self.frequencies:
            self.frequencies[correction] = 0
        self.frequencies[correction] += 1

        # Track case variations if requested
        if preserve_case:
            if correction not in self.cases:
                self.cases[correction] = {}
            if correction not in self.cases[correction]:
                self.cases[correction][correction] = 0
            self.cases[correction][correction] += 1


class DiffBasedCorrector(CorrectionStrategy):
    """
    Implements word-diff based correction strategy using anchor words
    to align and correct transcribed lyrics.

    Key Features:
    - Uses multiple reference sources (internet lyrics + optional second transcription)
    - Preserves timing information from original transcription
    - Provides detailed metadata about corrections made
    - Falls back to original words when corrections aren't confident

    Potential Improvements:
    1. Add phonetic matching for better word alignment (e.g., Soundex or Metaphone)
    2. Implement context-aware corrections using surrounding words
    3. Use more sophisticated alignment algorithms (e.g., Smith-Waterman)
    4. Add validation using language models to ensure semantic consistency
    5. Implement word normalization (e.g., handling contractions, punctuation)
    """

    def __init__(self, logger: Optional[logging.Logger] = None, min_source_agreement: float = 0.5):
        self.logger = logger or logging.getLogger(__name__)
        self.min_source_agreement = min_source_agreement  # Minimum ratio of sources that must agree
        self.corrections: Dict[str, CorrectionEntry] = {}

    def _find_anchor_words(self, segments: List[LyricsSegment]) -> Set[str]:
        """
        Identify potential anchor words from transcribed segments.

        Since we don't have confidence values, we'll use these heuristics:
        1. Words that are longer (more likely to be distinctive)
        2. Words that aren't common stop words
        3. Words that appear multiple times in the same position
        """
        self.logger.debug("Starting anchor word identification")

        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "were",
            "will",
            "with",
        }
        self.logger.debug(f"Using {len(stop_words)} stop words for filtering")

        anchors = set()
        word_positions = {}  # Track words and their relative positions

        for segment_idx, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {segment_idx}: '{segment.text}'")

            for i, word in enumerate(segment.words):
                word_lower = word.text.lower().strip(",. ")

                # Log word analysis
                if len(word_lower) <= 2:
                    # self.logger.debug(f"Skipping short word: '{word_lower}'")
                    continue
                if word_lower in stop_words:
                    # self.logger.debug(f"Skipping stop word: '{word_lower}'")
                    continue

                if word_lower not in word_positions:
                    word_positions[word_lower] = []
                word_positions[word_lower].append(i)

                # Log anchor word selection criteria
                if len(word_positions[word_lower]) >= 2:
                    self.logger.debug(f"Adding repeated word as anchor: '{word_lower}' (positions: {word_positions[word_lower]})")
                    anchors.add(word_lower)
                elif len(word_lower) >= 4:
                    self.logger.debug(f"Adding long word as anchor: '{word_lower}'")
                    anchors.add(word_lower)

        self.logger.debug(f"Final anchor words: {sorted(anchors)}")
        return anchors

    def _clean_word(self, word: str) -> str:
        """Clean word for comparison by removing punctuation and extra spaces."""
        return word.strip(',.!? \n')

    def _align_texts(
        self, source_text: str, target_text: str, anchor_words: Set[str]
    ) -> Tuple[List[Tuple[str, str]], List[str], List[str]]:
        """Align two texts using difflib with anchor word guidance."""
        self.logger.debug(f"\nStarting alignment between texts:")
        self.logger.debug(f"Source text: {source_text}")
        self.logger.debug(f"Target text: {target_text}")

        # Split into words, preserving original form for output but using cleaned version for comparison
        source_words_orig = source_text.split()
        target_words_orig = target_text.split()
        
        source_words_clean = [self._clean_word(w) for w in source_words_orig]
        target_words_clean = [self._clean_word(w) for w in target_words_orig]
        
        # Create anchor positions using cleaned words
        source_anchors = {word: i for i, word in enumerate(source_words_clean) if self._clean_word(word) in anchor_words}
        target_anchors = {word: i for i, word in enumerate(target_words_clean) if self._clean_word(word) in anchor_words}

        self.logger.debug(f"Anchor positions in source: {source_anchors}")
        self.logger.debug(f"Anchor positions in target: {target_anchors}")

        common_anchors = set(source_anchors.keys()) & set(target_anchors.keys())
        self.logger.debug(f"Common anchors found: {common_anchors}")

        alignment_points = [(source_anchors[w], target_anchors[w]) for w in common_anchors]
        alignment_points.sort()
        self.logger.debug(f"Alignment points: {alignment_points}")

        alignments = []
        matched_anchors = []
        prev_s = prev_t = 0

        # Process each section between anchor points
        for s_idx, t_idx in alignment_points:
            # Align all words between previous anchor and this one
            s_section = source_words_orig[prev_s:s_idx]
            t_section = target_words_orig[prev_t:t_idx]

            # If sections have different lengths, align them word by word
            max_len = max(len(s_section), len(t_section))
            for i in range(max_len):
                s_word = s_section[i] if i < len(s_section) else None
                t_word = t_section[i] if i < len(t_section) else None
                if s_word is not None and t_word is not None:
                    alignments.append((s_word, t_word))
                    if s_word in anchor_words:
                        matched_anchors.append(s_word)

            # Add the anchor word itself
            anchor_word = source_words_orig[s_idx]
            alignments.append((anchor_word, target_words_orig[t_idx]))
            matched_anchors.append(anchor_word)

            prev_s = s_idx + 1
            prev_t = t_idx + 1

        # Handle remaining words after last anchor
        s_remaining = source_words_orig[prev_s:]
        t_remaining = target_words_orig[prev_t:]
        max_remaining = max(len(s_remaining), len(t_remaining))
        for i in range(max_remaining):
            s_word = s_remaining[i] if i < len(s_remaining) else None
            t_word = t_remaining[i] if i < len(t_remaining) else None
            if s_word is not None and t_word is not None:
                alignments.append((s_word, t_word))
                if s_word in anchor_words:
                    matched_anchors.append(s_word)

        # Track unmatched anchor words
        unmatched_anchors = [w for w in anchor_words if w not in matched_anchors]

        self.logger.debug(f"Final alignments: {alignments}")
        self.logger.debug(f"Unmatched words in source: {[w for w in source_words_orig if w not in [a[0] for a in alignments]]}")
        self.logger.debug(f"Unmatched words in target: {[w for w in target_words_orig if w not in [a[1] for a in alignments]]}")

        return alignments, matched_anchors, unmatched_anchors

    def _create_correction_mapping(self, primary_text: str, lyrics_results: Dict[str, str], anchor_words: Set[str]) -> None:
        """Create correction mapping from multiple lyrics sources."""
        self.logger.debug("\nStarting correction mapping creation")

        for source, lyrics in lyrics_results.items():
            self.logger.debug(f"\nProcessing lyrics from source: {source}")

            # Get alignments for this source
            alignments, matched_anchors, unmatched_anchors = self._align_texts(primary_text, lyrics, anchor_words)

            # Process aligned words
            for source_word, target_word in alignments:
                if source_word != target_word:
                    self.logger.debug(f"Found difference: '{source_word}' -> '{target_word}'")

                    # Skip if either word is None (unmatched)
                    if source_word is None or target_word is None:
                        continue

                    # Create new correction entry if needed
                    if source_word not in self.corrections:
                        self.corrections[source_word] = CorrectionEntry()
                        self.logger.debug(f"Created new correction entry for '{source_word}'")

                    # Update correction counts
                    entry = self.corrections[source_word]
                    entry.add_correction(target_word, source, preserve_case=True)

                    self.logger.debug(f"Updated counts for '{source_word}' -> '{target_word}':")
                    self.logger.debug(f"  Sources: {entry.sources}")
                    self.logger.debug(f"  Cases: {entry.cases}")
                    self.logger.debug(f"  Frequencies: {entry.frequencies}")

            # Process unmatched words separately
            unmatched_pairs = self._find_unmatched_pairs(alignments)
            for source_word, target_word in unmatched_pairs:
                if source_word and target_word:  # Both words exist
                    self.logger.debug(f"Processing unmatched pair: '{source_word}' -> '{target_word}'")
                    if source_word not in self.corrections:
                        self.corrections[source_word] = CorrectionEntry()
                    entry = self.corrections[source_word]
                    entry.add_correction(target_word, source, preserve_case=True)

    def _find_unmatched_pairs(self, alignments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Find potential corrections from unmatched words."""
        source_words = [a[0] for a in alignments if a[0] is not None]
        target_words = [a[1] for a in alignments if a[1] is not None]

        # Find words that appear in one text but not the other
        source_only = set(source_words) - set(target_words)
        target_only = set(target_words) - set(source_words)

        # Try to pair unmatched words based on position
        pairs = []
        for s_word in source_only:
            s_indices = [i for i, (w, _) in enumerate(alignments) if w == s_word]
            for s_idx in s_indices:
                # Look for nearby unmatched target words
                for t_word in target_only:
                    t_indices = [i for i, (_, w) in enumerate(alignments) if w == t_word]
                    for t_idx in t_indices:
                        if abs(s_idx - t_idx) <= 2:  # Allow for small position differences
                            pairs.append((s_word, t_word))
                            break

        return pairs

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply diff-based correction algorithm with detailed output."""
        self.logger.info("Starting diff-based correction")

        # Sort transcription results by priority
        sorted_results = sorted(transcription_results, key=lambda x: x.priority)
        primary_transcription = sorted_results[0].result

        # Find anchor words
        anchor_words = self._find_anchor_words(primary_transcription.segments)
        self.logger.debug(f"Found {len(anchor_words)} anchor words: {anchor_words}")

        # Create correction mapping
        self._create_correction_mapping(
            " ".join(w.text.lower().strip(",. ") for segment in primary_transcription.segments for w in segment.words),
            {lyrics.source: lyrics.lyrics.lower() for lyrics in lyrics_results},
            anchor_words,
        )

        # Select corrections that meet confidence thresholds
        corrections_made = 0
        corrections: List[WordCorrection] = []
        corrected_segments = []

        for segment_idx, segment in enumerate(primary_transcription.segments):
            corrected_words = []

            for word_idx, word in enumerate(segment.words):
                word_lower = word.text.lower().strip(",. ")

                if word_lower in self.corrections:
                    entry = self.corrections[word_lower]

                    # Calculate confidence based on source agreement and frequency
                    total_sources = len(lyrics_results)
                    source_ratio = len(entry.sources) / total_sources

                    if source_ratio >= 0.5:  # At least half of sources agree
                        # Find most frequent correction
                        total_freq = sum(entry.frequencies.values())
                        best_correction, freq = max(entry.frequencies.items(), key=lambda x: x[1])
                        freq_ratio = freq / total_freq

                        if freq_ratio >= 0.6 and freq >= 2:  # 60% agreement and seen twice
                            # Get best case variant
                            case_variants = entry.cases[best_correction]
                            best_case = max(case_variants.items(), key=lambda x: x[1])[0]

                            confidence = (source_ratio + freq_ratio) / 2

                            corrected_word = Word(
                                text=best_case,
                                start_time=word.start_time,
                                end_time=word.end_time,
                                confidence=confidence,
                            )
                            corrected_words.append(corrected_word)

                            # Track correction
                            correction = WordCorrection(
                                original_word=word.text,
                                corrected_word=best_case,
                                segment_index=segment_idx,
                                word_index=word_idx,
                                confidence=confidence,
                                source=", ".join(entry.sources),
                                reason=f"Found in {len(entry.sources)} of {total_sources} sources ({freq} times)",
                                alternatives={
                                    k: {"count": v, "sources": list(entry.sources)}
                                    for k, v in entry.frequencies.items()
                                    if k != best_correction
                                },
                            )
                            corrections.append(correction)
                            corrections_made += 1
                            continue

                # Keep original word if no confident correction
                corrected_words.append(word)

            # Create corrected segment
            corrected_segment = LyricsSegment(
                text=" ".join(w.text for w in corrected_words),
                words=corrected_words,
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
            corrected_segments.append(corrected_segment)

        # Join segments with newlines, maintaining consistency with input format
        corrected_text = "\n".join(segment.text for segment in corrected_segments) + "\n"
        original_text = "\n".join(segment.text.rstrip(",. ") for segment in primary_transcription.segments) + "\n"

        # Since we don't have confidence values, use a simpler metric
        # based on how many corrections were needed
        total_words = sum(len(segment.words) for segment in corrected_segments)
        correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

        return CorrectionResult(
            original_segments=primary_transcription.segments,
            original_text=original_text,
            corrected_segments=corrected_segments,
            corrected_text=corrected_text,
            corrections=corrections,
            corrections_made=corrections_made,
            confidence=correction_ratio,
            anchor_words=anchor_words,
            metadata={
                "correction_strategy": "diff_based",
                "anchor_words_count": len(anchor_words),
                "total_words": total_words,
                "correction_ratio": correction_ratio,
                "primary_source": sorted_results[0].name,
                "sources_processed": [lyrics.source for lyrics in lyrics_results],
            },
        )
