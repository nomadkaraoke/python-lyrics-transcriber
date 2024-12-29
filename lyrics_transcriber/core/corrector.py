import json
import logging
from typing import Dict, Optional


class LyricsTranscriptionCorrector:
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)

        # Initialize instance variables for input data
        self.spotify_lyrics_data_dict = None
        self.spotify_lyrics_text = None
        self.genius_lyrics_text = None
        self.transcription_data_dict_whisper = None
        self.transcription_data_dict_audioshake = None

    def set_input_data(
        self,
        spotify_lyrics_data_dict: Optional[Dict] = None,
        spotify_lyrics_text: Optional[str] = None,
        genius_lyrics_text: Optional[str] = None,
        transcription_data_dict_whisper: Optional[Dict] = None,
        transcription_data_dict_audioshake: Optional[Dict] = None,
    ) -> None:
        """Store the input data as instance variables"""
        self.spotify_lyrics_data_dict = spotify_lyrics_data_dict
        self.spotify_lyrics_text = spotify_lyrics_text
        self.genius_lyrics_text = genius_lyrics_text
        self.transcription_data_dict_whisper = transcription_data_dict_whisper
        self.transcription_data_dict_audioshake = transcription_data_dict_audioshake

    def run_corrector(self) -> Dict:
        """
        Test implementation that replaces every third word with 'YOLO' in the AudioShake transcription.
        """
        self.logger.info("Running corrector (test implementation - replacing every 3rd word with YOLO)")

        # Create a deep copy to avoid modifying the original
        modified_data = json.loads(json.dumps(self.transcription_data_dict_audioshake))

        # Process each segment
        for segment in modified_data["segments"]:
            # Replace every third word in the words list
            for i in range(2, len(segment["words"]), 3):
                segment["words"][i]["text"] = "YOLO"

            # Reconstruct the segment text from the modified words
            segment["text"] = " ".join(word["text"] for word in segment["words"])

        # Reconstruct the full text from all segments
        modified_data["text"] = "".join(segment["text"] for segment in modified_data["segments"])

        return modified_data
