import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModel
from metaphone import doublemetaphone
from nltk.metrics import edit_distance

from lyrics_transcriber.types import (
    LyricsData,
    LyricsSegment,
    Word,
    TranscriptionResult,
    CorrectionResult,
    WordCorrection,
    GapSequence,
)
from lyrics_transcriber.correction.base_strategy import CorrectionStrategy
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder


@dataclass
class PhraseMatch:
    """Represents a match between transcribed and reference phrases."""

    transcribed_phrase: str
    reference_phrase: str
    phonetic_score: float
    semantic_score: float
    combined_score: float
    source: str


class PhoneticMatcher:
    """Improved phonetic matching using Double Metaphone."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def get_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity between two words."""
        # Get phonetic codes
        code1_primary, code1_secondary = doublemetaphone(word1)
        code2_primary, code2_secondary = doublemetaphone(word2)

        # Handle empty codes
        if not code1_primary or not code2_primary:
            return 0.0

        # Compare primary codes
        primary_similarity = 1 - (edit_distance(code1_primary, code2_primary) / max(len(code1_primary), len(code2_primary)))

        # Compare secondary codes if available
        if code1_secondary and code2_secondary:
            secondary_similarity = 1 - (edit_distance(code1_secondary, code2_secondary) / max(len(code1_secondary), len(code2_secondary)))
            return max(primary_similarity, secondary_similarity)

        return primary_similarity


class SemanticMatcher:
    """Semantic matching using transformer-based embeddings."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def get_embedding(self, text: str) -> torch.Tensor:
        """Get embedding for a piece of text."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling
            embedding = outputs.last_hidden_state.mean(dim=1)

        return embedding

    def get_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two pieces of text."""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)

        similarity = torch.nn.functional.cosine_similarity(emb1, emb2, dim=1)
        return similarity.item()


class SmartCorrectionStrategy(CorrectionStrategy):
    """Implements correction strategy using combined phonetic and semantic matching."""

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        anchor_finder: Optional[AnchorSequenceFinder] = None,
        phonetic_weight: float = 0.6,
        semantic_weight: float = 0.4,
        combined_threshold: float = 0.5,
        phonetic_threshold: float = 0.4,
        semantic_threshold: float = 0.3,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.anchor_finder = anchor_finder or AnchorSequenceFinder(logger=self.logger)
        self.phonetic_matcher = PhoneticMatcher()
        self.semantic_matcher = SemanticMatcher()
        self.phonetic_weight = phonetic_weight
        self.semantic_weight = semantic_weight
        self.combined_threshold = combined_threshold
        self.phonetic_threshold = phonetic_threshold
        self.semantic_threshold = semantic_threshold

    def _find_best_word_match(self, word: str, reference_words: List[str]) -> Optional[Tuple[str, float, float, float]]:
        """Find the best matching reference word."""
        best_match = None
        best_score = 0.0

        self.logger.debug(f"Trying to match word: '{word}'")
        self.logger.debug(f"Reference words: {reference_words}")

        for ref_word in reference_words:
            # Get phonetic similarity
            phonetic_score = self.phonetic_matcher.get_similarity(word, ref_word)

            # Get semantic similarity
            semantic_score = self.semantic_matcher.get_similarity(word, ref_word)

            # Calculate combined score
            combined_score = phonetic_score * self.phonetic_weight + semantic_score * self.semantic_weight

            self.logger.debug(f"Comparing '{word}' with '{ref_word}':")
            self.logger.debug(f"  Phonetic: {phonetic_score:.2f}")
            self.logger.debug(f"  Semantic: {semantic_score:.2f}")
            self.logger.debug(f"  Combined: {combined_score:.2f}")

            # Check if this is a better match
            if combined_score > best_score and phonetic_score >= self.phonetic_threshold and semantic_score >= self.semantic_threshold:
                best_score = combined_score
                best_match = (ref_word, phonetic_score, semantic_score, combined_score)

        return best_match

    def handle_gap(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Process a gap and return a correction if possible."""
        print(f"\nDebug: Handling gap for word '{word.text}'")

        # Find best matching phrase
        match = self._find_best_phrase_match(gap, {})  # We don't need reference_texts here

        if match:
            # Get the position of the current word in the gap
            gap_pos = current_word_idx - gap.transcription_position
            print(f"Word position in gap: {gap_pos}")

            # Split phrases into words
            ref_words = match.reference_phrase.split()

            # Make sure we have a corresponding reference word
            if gap_pos < len(ref_words):
                ref_word = ref_words[gap_pos]
                print(f"Corresponding reference word: '{ref_word}'")

                # Don't correct if words are the same
                if ref_word.lower() == word.text.lower():
                    print("Words match exactly, no correction needed")
                    return None

                print(f"Creating correction: {word.text} -> {ref_word}")
                return WordCorrection(
                    original_word=word.text,
                    corrected_word=ref_word,
                    segment_index=segment_idx,
                    word_index=current_word_idx,
                    confidence=match.combined_score,
                    source=match.source,
                    reason=f"Combined matching (phonetic: {match.phonetic_score:.2f}, semantic: {match.semantic_score:.2f})",
                    alternatives={},
                )

        print("No correction made")
        return None

    def correct(
        self,
        transcription_results: List[TranscriptionResult],
        lyrics_results: List[LyricsData],
    ) -> CorrectionResult:
        """Apply corrections using combined phonetic and semantic matching."""
        self.logger.info("Starting smart correction")

        # Get primary transcription
        primary_transcription = sorted(transcription_results, key=lambda x: x.priority)[0].result
        transcribed_text = " ".join(" ".join(w.text for w in segment.words) for segment in primary_transcription.segments)
        reference_texts = {lyrics.source: lyrics.lyrics for lyrics in lyrics_results}

        self.logger.debug(f"Transcribed text: {transcribed_text}")
        self.logger.debug(f"Reference texts: {reference_texts}")

        # Find anchor sequences and gaps
        anchor_sequences = self.anchor_finder.find_anchors(transcribed_text, reference_texts)
        gap_sequences = self.anchor_finder.find_gaps(transcribed_text, anchor_sequences, reference_texts)

        corrections: List[WordCorrection] = []
        corrected_segments = []
        corrections_made = 0
        current_word_idx = 0

        # Process each segment
        for segment_idx, segment in enumerate(primary_transcription.segments):
            corrected_words = []

            # Process each word in the segment
            for word in segment.words:
                self.logger.debug(f"Processing word: '{word.text}' at position {current_word_idx}")

                # Find if this word is part of a gap
                gap = next(
                    (g for g in gap_sequences if g.transcription_position <= current_word_idx < g.transcription_position + len(g.words)),
                    None,
                )

                if gap and gap.reference_words:
                    self.logger.debug(f"Found gap: {gap.words}")
                    # Get all reference words for this position
                    word_position = current_word_idx - gap.transcription_position
                    reference_words = []

                    for source, words in gap.reference_words.items():
                        if words and word_position < len(words):
                            reference_words.append(words[word_position])

                    if reference_words:
                        match = self._find_best_word_match(word.text.rstrip(), reference_words)  # Strip trailing whitespace/newlines

                        if match:
                            ref_word, phonetic_score, semantic_score, combined_score = match
                            self.logger.debug(f"Found match: {word.text} -> {ref_word}")
                            self.logger.debug(
                                f"Scores - Phonetic: {phonetic_score:.2f}, Semantic: {semantic_score:.2f}, Combined: {combined_score:.2f}"
                            )

                            if combined_score >= self.combined_threshold:
                                self.logger.info(f"Correcting word: '{word.text}' -> '{ref_word}' (confidence: {combined_score:.2f})")
                                # Create correction
                                correction = WordCorrection(
                                    original_word=word.text,
                                    corrected_word=ref_word,
                                    segment_index=segment_idx,
                                    word_index=current_word_idx,
                                    confidence=combined_score,
                                    source=list(gap.reference_words.keys())[0],
                                    reason=f"Combined matching (phonetic: {phonetic_score:.2f}, semantic: {semantic_score:.2f})",
                                    alternatives={},
                                )
                                corrections.append(correction)
                                gap.corrections.append(correction)  # Add the correction to the gap sequence
                                word = Word(text=ref_word, start_time=word.start_time, end_time=word.end_time, confidence=combined_score)
                                corrections_made += 1
                            else:
                                self.logger.debug(f"Score below threshold ({self.combined_threshold}), keeping original word")
                        else:
                            self.logger.debug("No suitable match found, keeping original word")
                    else:
                        self.logger.debug("No reference words for this position, keeping original word")
                else:
                    self.logger.debug("No gap found or empty reference words, keeping original word")

                corrected_words.append(word)
                current_word_idx += 1

            # Create corrected segment
            corrected_segment = LyricsSegment(
                text=" ".join(w.text for w in corrected_words),
                words=corrected_words,
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
            corrected_segments.append(corrected_segment)

        # Calculate confidence
        total_words = sum(len(segment.words) for segment in corrected_segments)
        correction_ratio = 1 - (corrections_made / total_words if total_words > 0 else 0)

        self.logger.info(f"Correction completed. Made {corrections_made} corrections with confidence {correction_ratio:.2f}")

        return CorrectionResult(
            original_segments=primary_transcription.segments,
            corrected_segments=corrected_segments,
            corrected_text="\n".join(segment.text for segment in corrected_segments) + "\n",
            corrections=corrections,
            corrections_made=corrections_made,
            confidence=correction_ratio,
            transcribed_text=transcribed_text,
            reference_texts=reference_texts,
            anchor_sequences=anchor_sequences,
            gap_sequences=gap_sequences,
            metadata={
                "correction_strategy": "smart",
                "anchor_sequences_count": len(anchor_sequences),
                "gap_sequences_count": len(gap_sequences),
                "total_words": total_words,
                "correction_ratio": correction_ratio,
                "phonetic_weight": self.phonetic_weight,
                "semantic_weight": self.semantic_weight,
            },
        )
