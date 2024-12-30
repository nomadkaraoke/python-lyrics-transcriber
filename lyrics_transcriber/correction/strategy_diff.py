import logging
import difflib
from typing import Any, Dict, List, Optional, Set, Tuple

from ..transcribers.base_transcriber import TranscriptionData, LyricsSegment, Word, TranscriptionResult
from ..lyrics.base_lyrics_provider import LyricsData
from .base_strategy import CorrectionResult, CorrectionStrategy


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

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def _find_anchor_words(self, segments: List[LyricsSegment]) -> Set[str]:
        """
        Identify potential anchor words from transcribed segments.

        Since we don't have confidence values, we'll use these heuristics:
        1. Words that are longer (more likely to be distinctive)
        2. Words that aren't common stop words
        3. Words that appear multiple times in the same position
        """
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

        anchors = set()
        word_positions = {}  # Track words and their relative positions

        for segment in segments:
            for i, word in enumerate(segment.words):
                word_lower = word.text.lower().strip()

                # Skip very short words and stop words
                if len(word_lower) <= 2 or word_lower in stop_words:
                    continue

                # Track position of this word
                if word_lower not in word_positions:
                    word_positions[word_lower] = []
                word_positions[word_lower].append(i)

                # If word appears multiple times in similar positions, it's a good anchor
                if len(word_positions[word_lower]) >= 2:
                    anchors.add(word_lower)

                # Longer words (4+ chars) are more likely to be distinctive
                if len(word_lower) >= 4:
                    anchors.add(word_lower)

        return anchors

    def _align_texts(self, source_text: str, target_text: str) -> List[Tuple[str, str]]:
        """
        Align two texts using difflib and return word pairs.

        Uses Python's difflib for fuzzy string matching to find the best
        alignment between transcribed text and reference lyrics.

        Returns both matching and non-matching word pairs.
        """
        # Split into words and convert to lowercase for matching
        source_words = source_text.lower().split()
        target_words = target_text.lower().split()

        # Use SequenceMatcher to find matching blocks
        matcher = difflib.SequenceMatcher(None, source_words, target_words)

        # Create alignment pairs for both matching and non-matching sections
        alignments = []
        i = j = 0

        for block in matcher.get_matching_blocks():
            # Add non-matching pairs before this block
            while i < block.a and j < block.b:
                alignments.append((source_words[i], target_words[j]))
                i += 1
                j += 1

            # Add matching pairs from this block
            for _ in range(block.size):
                alignments.append((source_words[i], target_words[j]))
                i += 1
                j += 1

        # Add any remaining non-matching pairs
        while i < len(source_words) and j < len(target_words):
            alignments.append((source_words[i], target_words[j]))
            i += 1
            j += 1

        return alignments

    def _create_correction_mapping(
        self, transcription: TranscriptionData, lyrics_results: List[LyricsData], anchor_words: Set[str]
    ) -> Dict[str, Dict[str, int]]:
        """
        Create a mapping of potential corrections based on aligned texts.

        Strategy:
        1. Use anchor words to establish alignment points
        2. Look at words between anchor points in both sources
        3. Build frequency map of potential corrections
        4. Consider timing information when available
        """
        correction_counts: Dict[str, Dict[str, int]] = {}

        # Get transcription text as list of words
        trans_words = [w.text.lower().strip() for segment in transcription.segments for w in segment.words]

        # Process each lyrics source
        for lyrics in lyrics_results:
            # Split lyrics into words
            lyrics_words = lyrics.lyrics.lower().split()

            # Get alignments between transcription and lyrics
            alignments = self._align_texts(transcription.text, lyrics.lyrics)

            # Process aligned word pairs
            for trans_word, lyrics_word in alignments:
                trans_word = trans_word.strip()
                lyrics_word = lyrics_word.strip()

                # Skip if words are identical
                if trans_word == lyrics_word:
                    continue

                # Initialize correction mapping for this word if needed
                if trans_word not in correction_counts:
                    correction_counts[trans_word] = {}

                # Count this correction
                correction_counts[trans_word][lyrics_word] = correction_counts[trans_word].get(lyrics_word, 0) + 1

        return correction_counts

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply diff-based correction algorithm."""
        self.logger.info("Starting diff-based correction")

        # Sort transcription results by priority
        sorted_results = sorted(transcription_results, key=lambda x: x.priority)
        if not sorted_results:
            raise ValueError("No transcription results available")

        # Use highest priority transcription as primary source
        primary_transcription = sorted_results[0].result

        # Find anchor words from all transcriptions
        anchor_words = self._find_anchor_words(primary_transcription.segments)
        for result in sorted_results[1:]:
            anchor_words.update(self._find_anchor_words(result.result.segments))

        # Create correction mapping
        corrections = self._create_correction_mapping(primary_transcription, lyrics_results, anchor_words)

        # Apply corrections while preserving timing
        corrected_segments = []
        corrections_made = 0
        source_mapping = {}

        for segment in primary_transcription.segments:
            corrected_words = []

            for word in segment.words:
                word_lower = word.text.lower().strip()

                # Check if we have a correction for this word
                if word_lower in corrections:
                    # Get the most common correction
                    possible_corrections = corrections[word_lower]
                    if possible_corrections:
                        best_correction = max(possible_corrections.items(), key=lambda x: x[1])[0]

                        # Create corrected word with preserved timing
                        corrected_word = Word(
                            text=best_correction,
                            start_time=word.start_time,
                            end_time=word.end_time,
                            confidence=None,  # We don't have confidence values
                        )
                        corrected_words.append(corrected_word)
                        corrections_made += 1
                        source_mapping[best_correction] = "internet_lyrics"
                        continue

                # If no correction made, keep original word
                corrected_words.append(word)

            # Create new segment with corrected words
            corrected_segment = LyricsSegment(
                text=" ".join(w.text for w in corrected_words),
                words=corrected_words,
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
            corrected_segments.append(corrected_segment)

        # Since we don't have confidence values, use a simpler metric
        # based on how many corrections were needed
        total_words = sum(len(segment.words) for segment in corrected_segments)
        correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

        return CorrectionResult(
            segments=corrected_segments,
            text=" ".join(segment.text for segment in corrected_segments),
            confidence=correction_ratio,  # Use correction ratio as confidence
            corrections_made=corrections_made,
            source_mapping=source_mapping,
            metadata={
                "correction_strategy": "diff_based",
                "anchor_words_count": len(anchor_words),
                "total_words": total_words,
                "correction_ratio": correction_ratio,
                "primary_source": sorted_results[0].name,
            },
        )
