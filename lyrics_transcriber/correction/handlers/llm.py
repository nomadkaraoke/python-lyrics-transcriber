from typing import List, Optional, Tuple, Dict, Any, Union
import logging
import json
from datetime import datetime
from pathlib import Path

from lyrics_transcriber.types import GapSequence, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
from lyrics_transcriber.correction.handlers.word_operations import WordOperations
from lyrics_transcriber.correction.handlers.llm_providers import LLMProvider


class LLMHandler(GapCorrectionHandler):
    """Uses an LLM to analyze and correct gaps by comparing with reference lyrics."""

    def __init__(
        self, provider: LLMProvider, name: str, logger: Optional[logging.Logger] = None, cache_dir: Optional[Union[str, Path]] = None
    ):
        super().__init__(logger)
        self.logger = logger or logging.getLogger(__name__)
        self.provider = provider
        self.name = name
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def _format_prompt(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> str:
        """Format the prompt for the LLM with context about the gap and reference lyrics."""
        word_map = data.get("word_map", {})
        metadata = data.get("metadata", {}) if data else {}

        if not word_map:
            self.logger.error("No word_map provided in data")
            return ""

        # Format transcribed words with their IDs
        transcribed_words = [{"id": word_id, "text": word_map[word_id].text} for word_id in gap.transcribed_word_ids if word_id in word_map]

        prompt = (
            "You are a lyrics correction expert. You will be given transcribed lyrics that may contain errors "
            "and reference lyrics from multiple sources. Your task is to analyze each word in the transcribed text "
            "and suggest specific corrections based on the reference lyrics.\n\n"
            "Each word has a unique ID. When suggesting corrections, you must specify the ID of the word being corrected. "
            "This ensures accuracy in applying your corrections.\n\n"
            "For each correction, specify:\n"
            "1. The word ID being corrected\n"
            "2. The correction type ('replace', 'split', 'combine', or 'delete')\n"
            "3. The corrected text\n"
            "4. Your confidence level\n"
            "5. The reason for the correction\n\n"
        )

        # Add song context if available
        if metadata and metadata.get("artist") and metadata.get("title"):
            prompt += f"Song: {metadata['title']}\nArtist: {metadata['artist']}\n\n"

        # Format transcribed words with IDs
        prompt += "Transcribed words:\n"
        for word in transcribed_words:
            prompt += f"- ID: {word['id']}, Text: '{word['text']}'\n"

        prompt += "\nReference lyrics from different sources:\n"

        # Add each reference source with words and their IDs
        for source, word_ids in gap.reference_word_ids.items():
            reference_words = [{"id": word_id, "text": word_map[word_id].text} for word_id in word_ids if word_id in word_map]
            prompt += f"\n{source} immediate context:\n"
            for word in reference_words:
                prompt += f"- ID: {word['id']}, Text: '{word['text']}'\n"

            # Add full lyrics if available
            if metadata and metadata.get("full_reference_texts", {}).get(source):
                prompt += f"\nFull {source} lyrics:\n{metadata['full_reference_texts'][source]}\n"

        # Add context about surrounding anchors if available
        if gap.preceding_anchor_id:
            preceding_anchor = next((a.anchor for a in data.get("anchor_sequences", []) if a.anchor.id == gap.preceding_anchor_id), None)
            if preceding_anchor:
                anchor_words = [
                    {"id": word_id, "text": word_map[word_id].text}
                    for word_id in preceding_anchor.transcribed_word_ids
                    if word_id in word_map
                ]
                prompt += "\nPreceding correct words:\n"
                for word in anchor_words:
                    prompt += f"- ID: {word['id']}, Text: '{word['text']}'\n"

        prompt += (
            "\nProvide corrections in the following JSON format:\n"
            "{\n"
            '  "corrections": [\n'
            "    {\n"
            '      "word_id": "id_of_word_to_correct",\n'
            '      "type": "replace|split|combine|delete",\n'
            '      "corrected_text": "new text",\n'
            '      "reference_word_id": "id_from_reference_lyrics",  // Optional, use when matching a specific reference word\n'
            '      "confidence": 0.9,\n'
            '      "reason": "explanation of correction"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Important rules:\n"
            "1. Always include the word_id for each correction\n"
            "2. For 'split' type, corrected_text should contain the space-separated words\n"
            "3. For 'combine' type, word_id should be the first word to combine\n"
            "4. Include reference_word_id when the correction matches a specific reference word\n"
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

    def _write_debug_info(self, prompt: str, response: str, gap_index: int, audio_file_hash: Optional[str] = None) -> None:
        """Write prompt and response to debug files."""
        if not self.cache_dir:
            self.logger.warning("No cache directory provided, skipping LLM debug output")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = self.cache_dir / "llm_debug"
        debug_dir.mkdir(exist_ok=True, parents=True)

        hash_prefix = f"{audio_file_hash}_" if audio_file_hash else ""
        filename = debug_dir / f"llm_debug_{hash_prefix}{gap_index}_{timestamp}.txt"

        debug_content = "=== LLM PROMPT ===\n" f"{prompt}\n\n" "=== LLM RESPONSE ===\n" f"{response}\n"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(debug_content)
        except IOError as e:
            self.logger.error(f"Failed to write LLM debug file: {e}")

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        """Process the gap using the LLM and create corrections based on its response."""
        if not data or "word_map" not in data:
            self.logger.error("No word_map provided in data")
            return []

        word_map = data["word_map"]
        transcribed_words = [word_map[word_id].text for word_id in gap.transcribed_word_ids if word_id in word_map]

        # Calculate reference positions using the centralized method
        reference_positions = (
            WordOperations.calculate_reference_positions(gap, anchor_sequences=data.get("anchor_sequences", [])) or {}
        )  # Ensure empty dict if None

        prompt = self._format_prompt(gap, data)
        if not prompt:
            return []

        # Get a unique index for this gap based on its position
        gap_index = gap.transcription_position

        try:
            self.logger.debug(f"Processing gap words: {transcribed_words}")
            self.logger.debug(f"Reference word IDs: {gap.reference_word_ids}")

            response = self.provider.generate_response(prompt)

            # Write debug info to files
            self._write_debug_info(prompt, response, gap_index, audio_file_hash=data.get("audio_file_hash"))

            try:
                corrections_data = json.loads(response)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Raw response content: {response}")
                return []

            # Check if corrections exist and are non-empty
            if not corrections_data.get("corrections"):
                self.logger.debug("No corrections suggested by LLM")
                return []

            corrections = []
            for correction in corrections_data["corrections"]:
                # Validate word_id exists in gap
                if correction["word_id"] not in gap.transcribed_word_ids:
                    self.logger.error(f"LLM suggested correction for word_id {correction['word_id']} which is not in the gap")
                    continue

                # Get original word from word map
                original_word = word_map[correction["word_id"]]
                position = gap.transcription_position + gap.transcribed_word_ids.index(correction["word_id"])

                self.logger.debug(f"Processing correction: {correction}")

                if correction["type"] == "replace":
                    self.logger.debug(
                        f"Creating replacement: '{original_word.text}' -> '{correction['corrected_text']}' " f"at position {position}"
                    )
                    corrections.append(
                        WordOperations.create_word_replacement_correction(
                            original_word=original_word.text,
                            corrected_word=correction["corrected_text"],
                            original_position=position,
                            source="LLM",
                            confidence=correction["confidence"],
                            reason=correction["reason"],
                            handler=self.name,
                            reference_positions=reference_positions,
                            original_word_id=correction["word_id"],
                            corrected_word_id=correction.get("reference_word_id"),
                        )
                    )
                elif correction["type"] == "split":
                    split_words = correction["corrected_text"].split()
                    self.logger.debug(f"Creating split: '{original_word.text}' -> {split_words} " f"at position {position}")

                    # Get reference word IDs if provided
                    reference_word_ids = correction.get("reference_word_ids", [None] * len(split_words))

                    corrections.extend(
                        WordOperations.create_word_split_corrections(
                            original_word=original_word.text,
                            reference_words=split_words,
                            original_position=position,
                            source="LLM",
                            confidence=correction["confidence"],
                            reason=correction["reason"],
                            handler=self.name,
                            reference_positions=reference_positions,
                            original_word_id=correction["word_id"],
                            corrected_word_ids=reference_word_ids,
                        )
                    )
                elif correction["type"] == "combine":
                    # Get all word IDs to combine
                    word_ids_to_combine = []
                    current_idx = gap.transcribed_word_ids.index(correction["word_id"])
                    words_needed = len(correction["corrected_text"].split())

                    if current_idx + words_needed <= len(gap.transcribed_word_ids):
                        word_ids_to_combine = gap.transcribed_word_ids[current_idx : current_idx + words_needed]
                    else:
                        self.logger.error(f"Not enough words available to combine at position {position}")
                        continue

                    words_to_combine = [word_map[word_id].text for word_id in word_ids_to_combine]

                    self.logger.debug(
                        f"Creating combine: {words_to_combine} -> '{correction['corrected_text']}' " f"at position {position}"
                    )

                    corrections.extend(
                        WordOperations.create_word_combine_corrections(
                            original_words=words_to_combine,
                            reference_word=correction["corrected_text"],
                            original_position=position,
                            source="LLM",
                            confidence=correction["confidence"],
                            combine_reason=correction["reason"],
                            delete_reason=f"Part of combining words: {correction['reason']}",
                            handler=self.name,
                            reference_positions=reference_positions,
                            original_word_ids=word_ids_to_combine,
                            corrected_word_id=correction.get("reference_word_id"),
                        )
                    )
                elif correction["type"] == "delete":
                    self.logger.debug(f"Creating deletion: '{original_word.text}' at position {position}")
                    corrections.append(
                        WordCorrection(
                            original_word=original_word.text,
                            corrected_word="",
                            segment_index=0,
                            original_position=position,
                            confidence=correction["confidence"],
                            source="LLM",
                            reason=correction["reason"],
                            alternatives={},
                            is_deletion=True,
                            handler=self.name,
                            reference_positions=reference_positions,
                            word_id=correction["word_id"],
                            corrected_word_id=None,
                        )
                    )

            self.logger.debug(f"Created {len(corrections)} corrections: {[f'{c.original_word}->{c.corrected_word}' for c in corrections]}")
            return corrections

        except Exception as e:
            self.logger.error(f"Unexpected error in LLM handler: {e}")
            return []
