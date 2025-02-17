from typing import List, Optional, Tuple, Dict, Any
import logging
import json
from ollama import chat, ResponseError
from datetime import datetime
import string

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class LLMHandler(GapCorrectionHandler):
    """Uses an LLM to analyze and correct gaps by comparing with reference lyrics."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.logger = logger or logging.getLogger(__name__)
        self.model = "deepseek-r1:7b"

    def _format_prompt(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> str:
        """Format the prompt for the LLM with context about the gap and reference lyrics."""
        # Get word map and metadata from data
        word_map = data.get("word_map", {})
        metadata = data.get("metadata", {}) if data else {}

        if not word_map:
            self.logger.error("No word_map provided in data")
            return ""

        # Get transcribed words
        transcribed_words = [word_map[word_id].text for word_id in gap.transcribed_word_ids if word_id in word_map]

        prompt = (
            "You are a lyrics correction expert. You will be given transcribed lyrics that may contain errors "
            "and reference lyrics from multiple sources. Your task is to analyze each word in the transcribed text "
            "and suggest specific corrections based on the reference lyrics.\n\n"
            "For each word that needs correction:\n"
            "1. If it should be replaced with a different word, use type='replace'\n"
            "2. If it should be split into multiple words, use type='split'\n"
            "3. If it and following words should be combined, use type='combine'\n"
            "4. If it should be removed entirely, use type='delete'\n\n"
        )

        # Add song context if available
        if metadata and metadata.get("artist") and metadata.get("title"):
            prompt += f"Song: {metadata['title']}\n" f"Artist: {metadata['artist']}\n\n"

        prompt += "Context:\n" f"Transcribed words: '{' '.join(transcribed_words)}'\n" "Reference lyrics from different sources:\n"

        # Add each reference source with words
        for source, word_ids in gap.reference_word_ids.items():
            reference_words = [word_map[word_id].text for word_id in word_ids if word_id in word_map]
            prompt += f"- {source} immediate context: '{' '.join(reference_words)}'\n"

            # Add full lyrics if available
            if metadata and metadata.get("full_reference_texts", {}).get(source):
                prompt += f"Full {source} lyrics:\n{metadata['full_reference_texts'][source]}\n\n"

        # Add context about surrounding anchors if available
        anchor_sequences = data.get("anchor_sequences", [])
        if gap.preceding_anchor_id:
            preceding_anchor = next((a.anchor for a in anchor_sequences if a.anchor.id == gap.preceding_anchor_id), None)
            if preceding_anchor:
                anchor_words = [word_map[word_id].text for word_id in preceding_anchor.transcribed_word_ids if word_id in word_map]
                prompt += f"\nPreceding correct words: '{' '.join(anchor_words)}'"

        if gap.following_anchor_id:
            following_anchor = next((a.anchor for a in anchor_sequences if a.anchor.id == gap.following_anchor_id), None)
            if following_anchor:
                anchor_words = [word_map[word_id].text for word_id in following_anchor.transcribed_word_ids if word_id in word_map]
                prompt += f"\nFollowing correct words: '{' '.join(anchor_words)}'"

        prompt += (
            "\n\nProvide corrections in the following JSON format:\n"
            "{\n"
            '  "corrections": [\n'
            "    {\n"
            '      "type": "replace|split|combine|delete",\n'
            '      "original_word": "word to correct",\n'
            '      "corrected_word": "corrected word",\n'
            '      "position": 0,  // position of word in transcribed sequence\n'
            '      "confidence": 0.9,\n'
            '      "reason": "explanation of correction"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Important rules:\n"
            "1. Create one correction object per word that needs changing\n"
            "2. The position must be the index of the word in the transcribed sequence (0-based)\n"
            "3. For 'split' type, corrected_word should contain the space-separated words\n"
            "4. For 'combine' type, original_word should be the first word to combine\n"
            "5. Only suggest corrections when you're confident they improve the lyrics\n"
            "6. Preserve any existing words that match the reference lyrics\n"
            "7. Respond ONLY with the JSON object, no other text"
        )

        return prompt

    def can_handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """LLM handler can attempt to handle any gap with reference words."""
        if not gap.reference_word_ids:
            self.logger.debug("No reference words available")
            return False, {}

        return True, {}

    def _write_debug_info(self, prompt: str, response: str, gap_index: int) -> None:
        """Write prompt and response to debug files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_debug/llm_debug_{gap_index}_{timestamp}.txt"

        debug_content = "=== LLM PROMPT ===\n" f"{prompt}\n\n" "=== LLM RESPONSE ===\n" f"{response}\n"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(debug_content)

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Process the gap using the LLM and create corrections based on its response."""
        if not data or "word_map" not in data:
            self.logger.error("No word_map provided in data")
            return []

        word_map = data["word_map"]
        transcribed_words = [word_map[word_id].text for word_id in gap.transcribed_word_ids if word_id in word_map]

        # Calculate reference positions using the centralized method
        reference_positions = WordOperations.calculate_reference_positions(gap, anchor_sequences=data.get("anchor_sequences", []))

        prompt = self._format_prompt(gap, data)
        if not prompt:
            return []

        # Get a unique index for this gap based on its position
        gap_index = gap.transcription_position

        try:
            self.logger.debug(f"Processing gap words: {transcribed_words}")
            self.logger.debug(f"Reference word IDs: {gap.reference_word_ids}")

            response = chat(model=self.model, messages=[{"role": "user", "content": prompt}], format="json")

            # Write debug info to files
            self._write_debug_info(prompt, response.message.content, gap_index)

            try:
                corrections_data = json.loads(response.message.content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Raw response content: {response.message.content}")
                return []

            # Check if corrections exist and are non-empty
            if not corrections_data.get("corrections"):
                self.logger.debug("No corrections suggested by LLM")
                return []

            corrections = []
            try:
                for correction in corrections_data["corrections"]:
                    position = gap.transcription_position + correction["position"]
                    self.logger.debug(f"Processing correction: {correction}")

                    # Validate the position is within the gap
                    if correction["position"] >= len(gap.transcribed_word_ids):
                        self.logger.error(f"Invalid position {correction['position']} for gap of length {len(gap.transcribed_word_ids)}")
                        continue

                    # Get original word ID and object
                    original_word_id = gap.transcribed_word_ids[correction["position"]]
                    original_word = word_map[original_word_id]

                    # Clean words for comparison by removing punctuation and whitespace
                    cleaned_original = original_word.text.strip().strip(string.punctuation)
                    cleaned_correction = correction["original_word"].strip().strip(string.punctuation)

                    # Validate the original word matches
                    if cleaned_correction.lower() != cleaned_original.lower():
                        self.logger.error(
                            f"Original word mismatch: LLM says '{correction['original_word']}' "
                            f"but gap has '{original_word.text}' at position {correction['position']} "
                            f"(cleaned: '{cleaned_correction}' vs '{cleaned_original}')"
                        )
                        continue

                    if correction["type"] == "replace":
                        self.logger.debug(
                            f"Creating replacement: '{correction['original_word']}' -> '{correction['corrected_word']}' "
                            f"at position {position}"
                        )
                        corrections.append(
                            WordOperations.create_word_replacement_correction(
                                original_word=correction["original_word"],
                                corrected_word=correction["corrected_word"],
                                original_position=position,
                                source="LLM",
                                confidence=correction["confidence"],
                                reason=correction["reason"],
                                handler="LLMHandler",
                                reference_positions=reference_positions,
                                original_word_id=original_word_id,
                            )
                        )
                    elif correction["type"] == "split":
                        split_words = correction["corrected_word"].split()
                        self.logger.debug(f"Creating split: '{correction['original_word']}' -> {split_words} " f"at position {position}")
                        corrections.extend(
                            WordOperations.create_word_split_corrections(
                                original_word=correction["original_word"],
                                reference_words=split_words,
                                original_position=position,
                                source="LLM",
                                confidence=correction["confidence"],
                                reason=correction["reason"],
                                handler="LLMHandler",
                                reference_positions=reference_positions,
                                original_word_id=original_word_id,
                            )
                        )
                    elif correction["type"] == "combine":
                        words_to_combine = [
                            word_map[word_id].text
                            for word_id in gap.transcribed_word_ids[
                                correction["position"] : correction["position"] + len(correction["original_word"].split())
                            ]
                        ]
                        self.logger.debug(
                            f"Creating combine: {words_to_combine} -> '{correction['corrected_word']}' " f"at position {position}"
                        )
                        corrections.extend(
                            WordOperations.create_word_combine_corrections(
                                original_words=words_to_combine,
                                reference_word=correction["corrected_word"],
                                original_position=position,
                                source="LLM",
                                confidence=correction["confidence"],
                                combine_reason=correction["reason"],
                                delete_reason=f"Part of combining words: {correction['reason']}",
                                handler="LLMHandler",
                                reference_positions=reference_positions,
                            )
                        )
                    elif correction["type"] == "delete":
                        self.logger.debug(f"Creating deletion: '{correction['original_word']}' at position {position}")
                        corrections.append(
                            WordCorrection(
                                original_word=correction["original_word"],
                                corrected_word="",
                                segment_index=0,
                                original_position=position,
                                confidence=correction["confidence"],
                                source="LLM",
                                reason=correction["reason"],
                                alternatives={},
                                is_deletion=True,
                                handler="LLMHandler",
                                reference_positions=reference_positions,
                                word_id=original_word_id,
                            )
                        )

            except (KeyError, ValueError, IndexError) as e:
                self.logger.error(f"Error processing corrections: {e}")
                self.logger.error(f"Problematic correction data: {corrections_data}")
                return []

            self.logger.debug(f"Created {len(corrections)} corrections: {[f'{c.original_word}->{c.corrected_word}' for c in corrections]}")
            return corrections

        except Exception as e:
            self.logger.error(f"Unexpected error in LLM handler: {e}")
            return []
