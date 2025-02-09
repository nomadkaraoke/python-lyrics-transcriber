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

    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON content from between triple backticks in the response."""
        import re

        # Look for content between ```json and ``` markers
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if not json_match:
            # Try without the 'json' marker in case it's just using plain backticks
            json_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)

        if json_match:
            return json_match.group(1)

        self.logger.error("No JSON content found between backticks")
        self.logger.error(f"Full response: {response_text}")
        raise ValueError("No JSON content found in LLM response")

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Process the gap using the LLM and create corrections based on its response."""
        prompt = self._format_prompt(gap)

        # Get a unique index for this gap based on its position
        gap_index = gap.transcription_position

        try:
            response = chat(model=self.model, messages=[{"role": "user", "content": prompt}])

            # Write debug info to files
            self._write_debug_info(prompt, response.message.content, gap_index)

            try:
                # Extract JSON content from response
                json_content = self._extract_json_from_response(response.message.content)
                corrections_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Extracted JSON content: {json_content}")
                raise
            except ValueError as e:
                self.logger.error(str(e))
                raise

            # Convert LLM suggestions into WordCorrection objects
            corrections = []
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
                    # Assume corrected_word is a space-separated string of words to split into
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
                    # Get the words to combine based on position and length
                    words_to_combine = gap.words[correction["position"] : correction["position"] + len(correction["original_word"].split())]
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

            return corrections

        except ResponseError as e:
            self.logger.error(f"LLM response error: {e}")
            raise
