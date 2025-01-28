from typing import List, Tuple, Dict, Any
import spacy
import logging
import pyphen
import nltk
from nltk.corpus import cmudict
import syllables
from spacy_syllables import SpacySyllables

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class SyllablesMatchHandler(GapCorrectionHandler):
    """Handles gaps where number of syllables in reference text matches number of syllables in transcription."""

    def __init__(self):
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Marking SpacySyllables as used to prevent unused import warning
        _ = SpacySyllables

        # Load spacy model with syllables pipeline
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.info("Language model 'en_core_web_sm' not found. Attempting to download...")
            import subprocess

            try:
                subprocess.check_call(["python", "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")
                self.logger.info("Successfully downloaded and loaded en_core_web_sm")
            except subprocess.CalledProcessError as e:
                raise OSError(
                    "Language model 'en_core_web_sm' could not be downloaded. "
                    "Please install it manually with: python -m spacy download en_core_web_sm"
                ) from e

        # Add syllables component to pipeline if not already present
        if "syllables" not in self.nlp.pipe_names:
            self.nlp.add_pipe("syllables", after="tagger")

        # Initialize Pyphen for English
        self.dic = pyphen.Pyphen(lang="en_US")

        # Initialize NLTK's CMU dictionary
        try:
            self.cmudict = cmudict.dict()
        except LookupError:
            nltk.download("cmudict")
            self.cmudict = cmudict.dict()

    def _count_syllables_spacy(self, words: List[str]) -> int:
        """Count syllables using spacy_syllables."""
        text = " ".join(words)
        doc = self.nlp(text)
        total_syllables = sum(token._.syllables_count or 1 for token in doc)
        return total_syllables

    def _count_syllables_pyphen(self, words: List[str]) -> int:
        """Count syllables using pyphen."""
        total_syllables = 0
        for word in words:
            hyphenated = self.dic.inserted(word)
            syllables_count = len(hyphenated.split("-")) if hyphenated else 1
            total_syllables += syllables_count
        return total_syllables

    def _count_syllables_nltk(self, words: List[str]) -> int:
        """Count syllables using NLTK's CMU dictionary."""
        total_syllables = 0
        for word in words:
            word = word.lower()
            if word in self.cmudict:
                syllables_count = len([ph for ph in self.cmudict[word][0] if ph[-1].isdigit()])
                total_syllables += syllables_count
            else:
                total_syllables += 1
        return total_syllables

    def _count_syllables_lib(self, words: List[str]) -> int:
        """Count syllables using the syllables library."""
        total_syllables = 0
        for word in words:
            syllables_count = syllables.estimate(word)
            total_syllables += syllables_count
        return total_syllables

    def _count_syllables(self, words: List[str]) -> List[int]:
        """Count syllables using multiple methods."""
        spacy_count = self._count_syllables_spacy(words)
        pyphen_count = self._count_syllables_pyphen(words)
        nltk_count = self._count_syllables_nltk(words)
        syllables_count = self._count_syllables_lib(words)

        text = " ".join(words)
        self.logger.debug(
            f"Syllable counts for '{text}': spacy={spacy_count}, pyphen={pyphen_count}, nltk={nltk_count}, syllables={syllables_count}"
        )
        return [spacy_count, pyphen_count, nltk_count, syllables_count]

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        # Must have reference words
        if not gap.reference_words:
            self.logger.debug("No reference words available")
            return False, {}

        # Get syllable counts for gap text using different methods
        gap_syllables = self._count_syllables(gap.words)

        # Check if any reference source has matching syllable count with any method
        for source, words in gap.reference_words.items():
            ref_syllables = self._count_syllables(words)

            # If any counting method matches between gap and reference, we can handle it
            if any(gap_count == ref_count for gap_count in gap_syllables for ref_count in ref_syllables):
                self.logger.debug(f"Found matching syllable count in source '{source}'")
                return True, {
                    "gap_syllables": gap_syllables,
                    "matching_source": source,
                    "reference_words": words,
                    "reference_words_original": gap.reference_words_original[source],
                }

        self.logger.debug("No reference source had matching syllable count")
        return False, {}

    def handle(self, gap: GapSequence, data: Dict[str, Any]) -> List[WordCorrection]:
        corrections = []
        matching_source = data["matching_source"]
        reference_words = data["reference_words"]
        reference_words_original = data["reference_words_original"]

        # Use the centralized method to calculate reference positions
        reference_positions = WordOperations.calculate_reference_positions(gap, [matching_source])

        # Since we matched syllable counts for the entire gap, we should handle all words
        if len(gap.words) > len(reference_words):
            # Multiple transcribed words -> fewer reference words
            # Try to distribute the reference words across the gap words
            words_per_ref = len(gap.words) / len(reference_words)

            for ref_idx, ref_word_original in enumerate(reference_words_original):
                start_idx = int(ref_idx * words_per_ref)
                end_idx = int((ref_idx + 1) * words_per_ref)

                # Get the group of words to combine
                words_to_combine = gap.words[start_idx:end_idx]
                corrections.extend(
                    WordOperations.create_word_combine_corrections(
                        original_words=words_to_combine,
                        reference_word=ref_word_original,
                        original_position=gap.transcription_position + start_idx,
                        source=matching_source,
                        confidence=0.8,
                        combine_reason="SyllablesMatchHandler: Words combined based on syllable match",
                        delete_reason="SyllablesMatchHandler: Word removed as part of syllable match combination",
                        reference_positions=reference_positions,
                    )
                )

        elif len(gap.words) < len(reference_words):
            # Single transcribed word -> multiple reference words
            words_per_gap = len(reference_words) / len(gap.words)

            for i, orig_word in enumerate(gap.words):
                start_idx = int(i * words_per_gap)
                end_idx = int((i + 1) * words_per_gap)
                ref_words_original_for_orig = reference_words_original[start_idx:end_idx]

                corrections.extend(
                    WordOperations.create_word_split_corrections(
                        original_word=orig_word,
                        reference_words=ref_words_original_for_orig,
                        original_position=gap.transcription_position + i,
                        source=matching_source,
                        confidence=0.8,
                        reason="SyllablesMatchHandler: Split word based on syllable match",
                        reference_positions=reference_positions,
                    )
                )

        else:
            # One-to-one replacement
            for i, (orig_word, ref_word, ref_word_original) in enumerate(zip(gap.words, reference_words, reference_words_original)):
                if orig_word.lower() != ref_word.lower():
                    corrections.append(
                        WordOperations.create_word_replacement_correction(
                            original_word=orig_word,
                            corrected_word=ref_word_original,
                            original_position=gap.transcription_position + i,
                            source=matching_source,
                            confidence=0.8,
                            reason=f"SyllablesMatchHandler: Source '{matching_source}' had matching syllable count",
                            reference_positions=reference_positions,
                        )
                    )

        return corrections
