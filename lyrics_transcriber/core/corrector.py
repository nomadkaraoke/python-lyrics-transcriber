from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set
import logging
import difflib
from ..transcribers.base import TranscriptionData, LyricsSegment, Word


@dataclass
class InternetLyrics:
    """Container for lyrics fetched from internet sources."""

    text: str
    source: str  # e.g., "genius", "spotify"
    structured_data: Optional[Dict] = None  # For Spotify's JSON format


@dataclass
class CorrectionResult:
    """Container for correction results."""

    segments: List[LyricsSegment]
    text: str
    confidence: float
    corrections_made: int
    source_mapping: Dict[str, str]  # Maps corrected words to their source
    metadata: Dict[str, Any]


class CorrectionStrategy(Protocol):
    """Interface for different lyrics correction strategies."""

    def correct(
        self,
        primary_transcription: TranscriptionData,
        reference_transcription: Optional[TranscriptionData],
        internet_lyrics: List[InternetLyrics],
    ) -> CorrectionResult:
        """Apply correction strategy to transcribed lyrics."""
        ...  # pragma: no cover


class DiffBasedCorrector:
    """
    Implements word-diff based correction strategy using anchor words
    to align and correct transcribed lyrics.

    Key Features:
    - Configurable confidence thresholds for corrections
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

    def __init__(self, logger: Optional[logging.Logger] = None, confidence_threshold: float = 0.8, min_anchor_confidence: float = 0.95):
        self.logger = logger or logging.getLogger(__name__)
        self.confidence_threshold = confidence_threshold
        self.min_anchor_confidence = min_anchor_confidence

    def _find_anchor_words(self, segments: List[LyricsSegment]) -> Set[str]:
        """
        Identify high-confidence words that can serve as alignment anchors.

        Anchor words are used as reliable reference points when aligning
        transcribed text with internet lyrics. Only words with very high
        confidence scores are used as anchors to minimize alignment errors.
        """
        anchors = set()
        for segment in segments:
            for word in segment.words:
                if word.confidence >= self.min_anchor_confidence:
                    # Convert to lowercase for matching
                    anchors.add(word.text.lower())
        return anchors

    def _align_texts(self, source_text: str, target_text: str) -> List[Tuple[str, str]]:
        """
        Align two texts using difflib and return word pairs.

        Uses Python's difflib for fuzzy string matching to find the best
        alignment between transcribed text and reference lyrics. This helps
        handle cases where words might be missing, inserted, or slightly
        different between sources.

        Future improvements could include:
        - Using more sophisticated alignment algorithms
        - Adding phonetic similarity matching
        - Implementing word normalization
        """
        # Split into words and convert to lowercase for matching
        source_words = source_text.lower().split()
        target_words = target_text.lower().split()

        # Use SequenceMatcher to find matching blocks
        matcher = difflib.SequenceMatcher(None, source_words, target_words)

        # Create alignment pairs
        alignments = []
        for a, b, size in matcher.get_matching_blocks():
            for i in range(size):
                alignments.append((source_words[a + i], target_words[b + i]))

        return alignments

    def _create_correction_mapping(
        self, transcription: TranscriptionData, internet_lyrics: List[InternetLyrics], anchor_words: Set[str]
    ) -> Dict[str, Dict[str, int]]:
        """
        Create a mapping of potential corrections based on aligned texts.

        Uses anchor words to establish reliable alignment points, then
        builds a frequency map of potential corrections for each word.
        This helps identify the most likely corrections when multiple
        sources disagree.
        """
        correction_counts: Dict[str, Dict[str, int]] = {}

        # Process each lyrics source
        for lyrics in internet_lyrics:
            # Get alignments between transcription and lyrics
            alignments = self._align_texts(transcription.text, lyrics.text)

            # Process each word in the transcription
            for trans_word, lyrics_word in alignments:
                # Initialize correction mapping for this word if needed
                if trans_word not in correction_counts:
                    correction_counts[trans_word] = {}

                # Count this correction
                correction_counts[trans_word][lyrics_word] = correction_counts[trans_word].get(lyrics_word, 0) + 1

            # Also process words around anchor points
            for segment in transcription.segments:
                for i, word in enumerate(segment.words):
                    word_lower = word.text.lower()

                    # If this is a low-confidence word next to an anchor
                    if word.confidence < self.confidence_threshold:
                        # Look for this word's position in lyrics
                        try:
                            lyrics_words = lyrics.text.lower().split()
                            trans_words = transcription.text.lower().split()
                            trans_idx = trans_words.index(word_lower)

                            # Check if we have anchor words nearby
                            for offset in [-1, 1]:  # Check previous and next words
                                neighbor_idx = trans_idx + offset
                                if 0 <= neighbor_idx < len(trans_words) and trans_words[neighbor_idx] in anchor_words:
                                    # Found an anchor word - use it to align
                                    lyrics_anchor_idx = lyrics_words.index(trans_words[neighbor_idx])
                                    correction_idx = lyrics_anchor_idx - offset

                                    if 0 <= correction_idx < len(lyrics_words):
                                        correction = lyrics_words[correction_idx]
                                        if word_lower not in correction_counts:
                                            correction_counts[word_lower] = {}
                                        correction_counts[word_lower][correction] = correction_counts[word_lower].get(correction, 0) + 1
                        except ValueError:
                            continue  # Word not found in lyrics

        return correction_counts

    def correct(
        self,
        primary_transcription: TranscriptionData,
        reference_transcription: Optional[TranscriptionData],
        internet_lyrics: List[InternetLyrics],
    ) -> CorrectionResult:
        """
        Apply diff-based correction algorithm using anchor words for alignment.

        Algorithm Overview:
        1. Identify high-confidence anchor words from transcriptions
        2. Align texts using fuzzy matching and anchor words
        3. Build correction mapping from multiple sources
        4. Apply corrections only to low-confidence words
        5. Preserve timing information and segment structure
        6. Track correction sources and maintain metadata

        Future Improvements:
        - Add context-aware corrections using surrounding words
        - Implement confidence scoring for corrections
        - Add language model validation
        - Handle special cases (numbers, proper nouns, etc.)
        - Add support for multi-word corrections

        Args:
            primary_transcription: Main transcription to correct
            reference_transcription: Optional secondary transcription for validation
            internet_lyrics: List of lyrics from internet sources for correction

        Returns:
            CorrectionResult containing corrected segments and metadata
        """
        self.logger.info("Starting diff-based correction")

        # Find anchor words from high-confidence transcriptions
        anchor_words = self._find_anchor_words(primary_transcription.segments)
        if reference_transcription:
            anchor_words.update(self._find_anchor_words(reference_transcription.segments))

        # Create correction mapping using anchor words
        corrections = self._create_correction_mapping(primary_transcription, internet_lyrics, anchor_words)

        # Apply corrections to segments
        corrected_segments = []
        corrections_made = 0
        source_mapping = {}

        for segment in primary_transcription.segments:
            corrected_words = []

            for word in segment.words:
                word_lower = word.text.lower()

                # Only correct low-confidence words
                if word.confidence < self.confidence_threshold:
                    # Check if we have a correction for this word
                    if word_lower in corrections:
                        # Get the most common correction
                        possible_corrections = corrections[word_lower]
                        if possible_corrections:
                            best_correction = max(possible_corrections.items(), key=lambda x: x[1])[0]

                            # Create corrected word
                            corrected_word = Word(
                                text=best_correction,
                                start_time=word.start_time,
                                end_time=word.end_time,
                                confidence=0.8,  # Moderate confidence in correction
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

        # Calculate overall confidence
        avg_confidence = sum(word.confidence for segment in corrected_segments for word in segment.words) / sum(
            len(segment.words) for segment in corrected_segments
        )

        return CorrectionResult(
            segments=corrected_segments,
            text=" ".join(segment.text for segment in corrected_segments),
            confidence=avg_confidence,
            corrections_made=corrections_made,
            source_mapping=source_mapping,
            metadata={
                "correction_strategy": "diff_based",
                "anchor_words_count": len(anchor_words),
                "confidence_threshold": self.confidence_threshold,
                "min_anchor_confidence": self.min_anchor_confidence,
            },
        )


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

        # Input data containers
        self.primary_transcription: Optional[TranscriptionData] = None
        self.reference_transcription: Optional[TranscriptionData] = None
        self.internet_lyrics: List[InternetLyrics] = []

    def set_input_data(
        self,
        spotify_lyrics_data_dict: Optional[Dict] = None,
        spotify_lyrics_text: Optional[str] = None,
        genius_lyrics_text: Optional[str] = None,
        transcription_data_whisper: Optional[TranscriptionData] = None,
        transcription_data_audioshake: Optional[TranscriptionData] = None,
    ) -> None:
        """Process and store input data in structured format."""
        # Store internet lyrics sources
        if spotify_lyrics_text:
            self.internet_lyrics.append(
                InternetLyrics(text=spotify_lyrics_text, source="spotify", structured_data=spotify_lyrics_data_dict)
            )
        if genius_lyrics_text:
            self.internet_lyrics.append(InternetLyrics(text=genius_lyrics_text, source="genius"))

        # Store transcription data
        if transcription_data_audioshake:
            self.primary_transcription = transcription_data_audioshake
        if transcription_data_whisper:
            self.reference_transcription = transcription_data_whisper

    def run_corrector(self) -> CorrectionResult:
        """Execute the correction process using configured strategy."""
        if not self.primary_transcription:
            raise ValueError("No primary transcription data available")

        try:
            result = self.correction_strategy.correct(
                primary_transcription=self.primary_transcription,
                reference_transcription=self.reference_transcription,
                internet_lyrics=self.internet_lyrics,
            )
            return result

        except Exception as e:
            self.logger.error(f"Correction failed: {str(e)}")
            # Return uncorrected transcription as fallback
            return CorrectionResult(
                segments=self.primary_transcription.segments,
                text=self.primary_transcription.text,
                confidence=1.0,
                corrections_made=0,
                source_mapping={},
                metadata=self.primary_transcription.metadata or {},
            )
