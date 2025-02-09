from typing import List, Optional, Tuple, Dict, Any
import logging
import json
from ollama import chat, ResponseError
from datetime import datetime

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations


class LLMHandler(GapCorrectionHandler):
    """Uses an LLM to analyze and correct gaps by comparing with reference lyrics."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.logger = logger or logging.getLogger(__name__)
        self.model = "deepseek-r1:7b"

    def _format_prompt(self, gap: GapSequence) -> str:
        """Format the prompt for the LLM with context about the gap and reference lyrics."""
        prompt = (
            "You are a lyrics correction expert. You will be given transcribed lyrics that may contain errors "
            "and reference lyrics from multiple sources. Your task is to analyze the transcribed text and suggest "
            "corrections based on the reference lyrics.\n\n"
            "Context:\n"
            f"Transcribed words: '{' '.join(gap.words)}'\n"
            "Reference lyrics from different sources:\n"
        )

        # Add each reference source
        for source, words in gap.reference_words_original.items():
            prompt += f"- {source}: '{' '.join(words)}'\n"

        # Add context about surrounding anchors if available
        if gap.preceding_anchor:
            prompt += f"\nPreceding correct words: '{' '.join(gap.preceding_anchor.words)}'"
        if gap.following_anchor:
            prompt += f"\nFollowing correct words: '{' '.join(gap.following_anchor.words)}'"

        prompt += (
            "\n\nProvide corrections in the following JSON format:\n"
            "{\n"
            '  "corrections": [\n'
            "    {\n"
            '      "type": "replace|split|combine|delete",\n'
            '      "original_word": "word to correct",\n'
            '      "corrected_word": "corrected word",\n'
            '      "position": 0,\n'
            '      "confidence": 0.9,\n'
            '      "reason": "explanation of correction"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Respond ONLY with the JSON object, no other text."
        )

        return prompt

    def can_handle(self, gap: GapSequence) -> Tuple[bool, Dict[str, Any]]:
        """LLM handler can attempt to handle any gap with reference words."""
        if not gap.reference_words:
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
        prompt = self._format_prompt(gap)

        # Get a unique index for this gap based on its position
        gap_index = gap.transcription_position

        try:
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

                    if correction["type"] == "replace":
                        corrections.append(
                            WordOperations.create_word_replacement_correction(
                                original_word=correction["original_word"],
                                corrected_word=correction["corrected_word"],
                                original_position=position,
                                source="llm",
                                confidence=correction["confidence"],
                                reason=correction["reason"],
                            )
                        )
                    elif correction["type"] == "split":
                        split_words = correction["corrected_word"].split()
                        corrections.extend(
                            WordOperations.create_word_split_corrections(
                                original_word=correction["original_word"],
                                reference_words=split_words,
                                original_position=position,
                                source="llm",
                                confidence=correction["confidence"],
                                reason=correction["reason"],
                            )
                        )
                    elif correction["type"] == "combine":
                        words_to_combine = gap.words[
                            correction["position"] : correction["position"] + len(correction["original_word"].split())
                        ]
                        corrections.extend(
                            WordOperations.create_word_combine_corrections(
                                original_words=words_to_combine,
                                reference_word=correction["corrected_word"],
                                original_position=position,
                                source="llm",
                                confidence=correction["confidence"],
                                combine_reason=correction["reason"],
                                delete_reason=f"Part of combining words: {correction['reason']}",
                            )
                        )
                    elif correction["type"] == "delete":
                        corrections.append(
                            WordCorrection(
                                original_word=correction["original_word"],
                                corrected_word="",
                                segment_index=0,
                                original_position=position,
                                confidence=correction["confidence"],
                                source="llm",
                                reason=correction["reason"],
                                alternatives={},
                                is_deletion=True,
                            )
                        )
            except (KeyError, ValueError, IndexError) as e:
                self.logger.error(f"Error processing corrections: {e}")
                self.logger.error(f"Problematic correction data: {corrections_data}")
                return []

            return corrections

        except Exception as e:
            self.logger.error(f"Unexpected error in LLM handler: {e}")
            return []
