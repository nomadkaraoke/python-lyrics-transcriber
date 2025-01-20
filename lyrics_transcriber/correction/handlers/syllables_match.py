from typing import List
import spacy_syllables
import spacy
import logging
import pyphen
import nltk
from nltk.corpus import cmudict
import syllables

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class SyllablesMatchHandler(GapCorrectionHandler):
    """Handles gaps where number of syllables in reference text matches number of syllables in transcription."""

    def __init__(self):
        # Load spacy model with syllables pipeline
        self.nlp = spacy.load("en_core_web_sm")
        # Add syllables component to pipeline if not already present
        if "syllables" not in self.nlp.pipe_names:
            self.nlp.add_pipe("syllables")
        # Initialize Pyphen for English
        self.dic = pyphen.Pyphen(lang="en_US")
        # Initialize NLTK's CMU dictionary
        try:
            self.cmudict = cmudict.dict()
        except LookupError:
            nltk.download("cmudict")
            self.cmudict = cmudict.dict()
        self.logger = logging.getLogger(__name__)

    def _count_syllables_spacy(self, words: List[str]) -> int:
        """Count syllables using spacy_syllables."""
        text = " ".join(words)
        doc = self.nlp(text)
        total_syllables = sum(token._.syllables_count or 1 for token in doc)
        self.logger.debug(f"Spacy syllable count for '{text}': {total_syllables}")
        for token in doc:
            self.logger.debug(f"  Word '{token.text}': {token._.syllables_count or 1} syllables")
        return total_syllables

    def _count_syllables_pyphen(self, words: List[str]) -> int:
        """Count syllables using pyphen."""
        total_syllables = 0
        for word in words:
            # Count hyphens in hyphenated word + 1 to get syllable count
            hyphenated = self.dic.inserted(word)
            syllables_count = len(hyphenated.split("-")) if hyphenated else 1
            total_syllables += syllables_count
            self.logger.debug(f"  Pyphen word '{word}': {syllables_count} syllables (hyphenated: {hyphenated})")
        self.logger.debug(f"Pyphen syllable count for '{' '.join(words)}': {total_syllables}")
        return total_syllables

    def _count_syllables_nltk(self, words: List[str]) -> int:
        """Count syllables using NLTK's CMU dictionary."""
        total_syllables = 0
        for word in words:
            word = word.lower()
            # Try to get pronunciation from CMU dict
            if word in self.cmudict:
                # Count number of stress markers in first pronunciation
                syllables_count = len([ph for ph in self.cmudict[word][0] if ph[-1].isdigit()])
                total_syllables += syllables_count
                self.logger.debug(f"  NLTK word '{word}': {syllables_count} syllables")
            else:
                # Fallback to 1 syllable if word not in dictionary
                total_syllables += 1
                self.logger.debug(f"  NLTK word '{word}': 1 syllable (not in dictionary)")
        self.logger.debug(f"NLTK syllable count for '{' '.join(words)}': {total_syllables}")
        return total_syllables

    def _count_syllables_lib(self, words: List[str]) -> int:
        """Count syllables using the syllables library."""
        total_syllables = 0
        for word in words:
            syllables_count = syllables.estimate(word)
            total_syllables += syllables_count
            self.logger.debug(f"  Syllables lib word '{word}': {syllables_count} syllables")
        self.logger.debug(f"Syllables lib count for '{' '.join(words)}': {total_syllables}")
        return total_syllables

    def _count_syllables(self, words: List[str]) -> List[int]:
        """Count syllables using multiple methods."""
        spacy_count = self._count_syllables_spacy(words)
        pyphen_count = self._count_syllables_pyphen(words)
        nltk_count = self._count_syllables_nltk(words)
        syllables_count = self._count_syllables_lib(words)
        return [spacy_count, pyphen_count, nltk_count, syllables_count]

    def can_handle(self, gap: GapSequence) -> bool:
        # Must have reference words
        if not gap.reference_words:
            self.logger.debug("No reference words available")
            return False

        # Get syllable counts for gap text using different methods
        gap_syllables = self._count_syllables(gap.words)
        self.logger.debug(f"Gap '{' '.join(gap.words)}' has syllable counts: {gap_syllables}")

        # Check if any reference source has matching syllable count with any method
        for source, words in gap.reference_words.items():
            ref_syllables = self._count_syllables(words)
            self.logger.debug(f"Reference source '{source}' has syllable counts: {ref_syllables}")

            # If any counting method matches between gap and reference, we can handle it
            if any(gap_count == ref_count for gap_count in gap_syllables for ref_count in ref_syllables):
                self.logger.debug(f"Found matching syllable count in source '{source}'")
                return True

        self.logger.debug("No reference source had matching syllable count")
        return False

    def handle(self, gap: GapSequence) -> List[WordCorrection]:
        corrections = []

        # Find the matching source
        gap_syllables = self._count_syllables(gap.words)
        matching_source = None
        reference_words = None
        reference_words_original = None

        for source, words in gap.reference_words.items():
            ref_syllables = self._count_syllables(words)
            if any(gap_count == ref_count for gap_count in gap_syllables for ref_count in ref_syllables):
                matching_source = source
                reference_words = words
                reference_words_original = gap.reference_words_original[source]  # Get original formatted words
                break

        # Handle word splits (one transcribed word -> multiple reference words)
        if len(gap.words) < len(reference_words):
            # Simple case: distribute reference words evenly across gap words
            words_per_gap = len(reference_words) / len(gap.words)

            for i, orig_word in enumerate(gap.words):
                start_idx = int(i * words_per_gap)
                end_idx = int((i + 1) * words_per_gap)
                ref_words_for_orig = reference_words[start_idx:end_idx]
                ref_words_original_for_orig = reference_words_original[start_idx:end_idx]  # Get original formatted words

                # Create a correction for each reference word
                for split_idx, (ref_word, ref_word_original) in enumerate(zip(ref_words_for_orig, ref_words_original_for_orig)):
                    corrections.append(
                        WordCorrection(
                            original_word=orig_word,
                            corrected_word=ref_word_original,  # Use original formatted word
                            segment_index=0,
                            word_index=gap.transcription_position + i,
                            confidence=0.8,
                            source=matching_source,
                            reason=f"SyllablesMatchHandler: Split word based on syllable match",
                            alternatives={},
                            split_index=split_idx,
                            split_total=len(ref_words_for_orig),
                        )
                    )
        else:
            # One-to-one replacement
            for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
                if orig_word.lower() != ref_word.lower():
                    corrections.append(
                        WordCorrection(
                            original_word=orig_word,
                            corrected_word=ref_word_original,  # Use original formatted word
                            segment_index=0,
                            word_index=gap.transcription_position + i,
                            confidence=0.8,
                            source=matching_source,
                            reason=f"SyllablesMatchHandler: Source '{matching_source}' had matching syllable count",
                            alternatives={},
                        )
                    )

        return corrections
