from typing import List, Optional, Tuple, Dict, Any
import string
import Levenshtein
import logging

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class LevenshteinHandler(GapCorrectionHandler):
    """Handles corrections based on Levenshtein (edit distance) similarity between words.

    This handler looks for words that are similar in spelling to reference words in the same position.
    The similarity calculation includes:
    1. Basic Levenshtein ratio
    2. Bonus for words starting with the same letter
    3. Penalty for words starting with different letters
    4. Bonus for similar length words

    Examples:
        Gap: "wold" (misspelling)
        References:
            genius: ["world"]
            spotify: ["world"]
        Result:
            - Correct "wold" to "world" (high confidence due to small edit distance)

        Gap: "worde" (misspelling)
        References:
            genius: ["world"]
            spotify: ["words"]
        Result:
            - Correct "worde" to "world" (lower confidence due to disagreeing sources)
    """

    def __init__(self, similarity_threshold: float = 0.65, logger: Optional[logging.Logger] = None):
        self.similarity_threshold = similarity_threshold
        self.logger = logger or logging.getLogger(__name__)

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        """Check if we can handle this gap - we'll try if there are reference words."""
        if not gap.reference_words:
            self.logger.debug("No reference words available")
            return False, {}

        if not gap.words:
            self.logger.debug("No gap words available")
            return False, {}

        # Check if any word has sufficient similarity to reference
        for i, word in enumerate(gap.words):
            for ref_words in gap.reference_words.values():
                if i < len(ref_words):
                    similarity = self._get_string_similarity(word, ref_words[i])
                    if similarity >= self.similarity_threshold:
                        self.logger.debug(f"Found similar word: '{word}' -> '{ref_words[i]}' ({similarity:.2f})")
                        return True, {}

        self.logger.debug("No words meet similarity threshold")
        return False, {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Try to correct words based on string similarity."""
        corrections = []

        # Process each word in the gap
        for i, word in enumerate(gap.words):
            # Skip if word is empty or just punctuation
            if not word.strip():
                continue

            # Skip exact matches
            if any(i < len(ref_words) and word.lower() == ref_words[i].lower() for ref_words in gap.reference_words.values()):
                self.logger.debug(f"Skipping exact match: '{word}'")
                continue

            # Find matching reference words at this position
            matches = {}  # word -> (sources, similarity)
            for source, ref_words in gap.reference_words.items():
                ref_words_original = gap.reference_words_original[source]  # Get original formatted words
                if i >= len(ref_words):
                    continue

                ref_word = ref_words[i]
                ref_word_original = ref_words_original[i]  # Get original formatted word
                similarity = self._get_string_similarity(word, ref_word)

                if similarity >= self.similarity_threshold:
                    self.logger.debug(f"Found match: '{word}' -> '{ref_word}' ({similarity:.2f})")
                    if ref_word_original not in matches:  # Use original formatted word as key
                        matches[ref_word_original] = ([], similarity)
                    matches[ref_word_original][0].append(source)

            # Create correction for best match if any found
            if matches:
                best_match, (sources, similarity) = max(
                    matches.items(), key=lambda x: (len(x[1][0]), x[1][1])  # Sort by number of sources, then similarity
                )

                source_confidence = len(sources) / len(gap.reference_words)
                final_confidence = similarity * source_confidence

                # Calculate reference positions for matching sources
                reference_positions = WordOperations.calculate_reference_positions(gap, sources)

                self.logger.debug(f"Creating correction: {word} -> {best_match} (confidence: {final_confidence})")
                corrections.append(
                    WordOperations.create_word_replacement_correction(
                        original_word=word,
                        corrected_word=best_match,  # Using original formatted word
                        original_position=gap.transcription_position + i,
                        source=", ".join(sources),
                        confidence=final_confidence,
                        reason=f"LevenshteinHandler: String similarity ({final_confidence:.2f})",
                        reference_positions=reference_positions,
                    )
                )

        return corrections

    def _clean_word(self, word: str) -> str:
        """Remove punctuation and standardize for comparison."""
        return word.strip().lower().strip(string.punctuation)

    def _get_string_similarity(self, word1: str, word2: str) -> float:
        """Calculate string similarity using Levenshtein ratio with adjustments."""
        # Clean words
        w1, w2 = self._clean_word(word1), self._clean_word(word2)
        if not w1 or not w2:
            return 0.0

        # Calculate Levenshtein ratio
        similarity = Levenshtein.ratio(w1, w2)

        # Boost similarity for words starting with the same letter
        if w1[0] == w2[0]:
            similarity = (similarity + 1) / 2
        else:
            # Penalize words starting with different letters
            similarity = similarity * 0.9

        # Boost for similar length words
        length_ratio = min(len(w1), len(w2)) / max(len(w1), len(w2))
        similarity = (similarity + length_ratio) / 2

        return similarity
