#! /usr/bin/env python3
import os
import sys
import json
import requests
import hashlib
import tempfile
from time import sleep
from pydub import AudioSegment
from .base import BaseTranscriber
from ..storage.dropbox import DropboxHandler


class WhisperTranscriber(BaseTranscriber):
    """Transcription service using Whisper API via RunPod."""

    def __init__(
        self,
        logger=None,
        runpod_api_key=None,
        endpoint_id=None,
        dropbox_app_key=None,
        dropbox_app_secret=None,
        dropbox_refresh_token=None,
        dropbox_access_token=None,
    ):
        super().__init__(logger)
        self.runpod_api_key = runpod_api_key or os.getenv("RUNPOD_API_KEY")
        self.endpoint_id = endpoint_id or os.getenv("WHISPER_RUNPOD_ID")

        if not self.runpod_api_key or not self.endpoint_id:
            raise ValueError("RunPod API key and endpoint ID must be provided either directly or via environment variables")

        self.dbx = DropboxHandler(
            app_key=dropbox_app_key or os.getenv("WHISPER_DROPBOX_APP_KEY"),
            app_secret=dropbox_app_secret or os.getenv("WHISPER_DROPBOX_APP_SECRET"),
            refresh_token=dropbox_refresh_token or os.getenv("WHISPER_DROPBOX_REFRESH_TOKEN"),
            access_token=dropbox_access_token or os.getenv("WHISPER_DROPBOX_ACCESS_TOKEN"),
        )

    def get_name(self) -> str:
        return "Whisper"

    def transcribe(self, audio_filepath: str) -> dict:
        """
        Transcribe an audio file using Whisper API via RunPod.

        Args:
            audio_filepath: Path to the audio file to transcribe

        Returns:
            Dict containing:
                - segments: List of segments with start/end times and word-level data
                - text: Full text transcription
                - metadata: Dict of additional info
        """
        self.logger.info(f"Starting transcription for {audio_filepath} using Whisper API")

        # Calculate MD5 hash and prepare file
        file_hash = self._get_file_md5(audio_filepath)
        processed_filepath = self._convert_to_flac(audio_filepath)

        try:
            # Upload to Dropbox and get URL
            dropbox_path = f"/transcription_temp/{file_hash}{os.path.splitext(processed_filepath)[1]}"
            audio_url = self._upload_and_get_link(processed_filepath, dropbox_path)

            # Get transcription from API
            result = self._run_transcription(audio_url)

            # Add metadata
            result["metadata"] = {
                "service": self.get_name(),
                "model": "large-v2",
                "language": "en",
            }

            return result

        finally:
            # Clean up temporary FLAC file if one was created
            if processed_filepath != audio_filepath:
                self.logger.debug(f"Cleaning up temporary file: {processed_filepath}")
                os.unlink(processed_filepath)

    def _convert_to_flac(self, filepath: str) -> str:
        """Convert WAV to FLAC if needed for faster upload."""
        if not filepath.lower().endswith(".wav"):
            return filepath

        self.logger.info("Converting WAV to FLAC for faster upload...")
        audio = AudioSegment.from_wav(filepath)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as temp_flac:
            flac_path = temp_flac.name
            audio.export(flac_path, format="flac")

        return flac_path

    def _get_file_md5(self, filepath: str) -> str:
        """Calculate MD5 hash of a file."""
        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _upload_and_get_link(self, filepath: str, dropbox_path: str) -> str:
        """Upload file to Dropbox and return shared link."""
        if not self.dbx.file_exists(dropbox_path):
            self.logger.info("Uploading file to Dropbox...")
            with open(filepath, "rb") as f:
                self.dbx.upload_with_retry(f, dropbox_path)
        else:
            self.logger.info("File already exists in Dropbox, skipping upload...")

        audio_url = self.dbx.create_or_get_shared_link(dropbox_path)
        self.logger.debug(f"Using shared link: {audio_url}")
        return audio_url

    def _run_transcription(self, audio_url: str) -> dict:
        """Submit transcription job to RunPod and get results."""
        run_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/run"
        status_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status"
        headers = {"Authorization": f"Bearer {self.runpod_api_key}"}

        payload = {
            "input": {
                "audio": audio_url,
                "word_timestamps": True,
                "model": "large-v2",
                "temperature": 0.2,
                "best_of": 5,
                "compression_ratio_threshold": 2.8,
                "no_speech_threshold": 1,
                "condition_on_previous_text": True,
                "enable_vad": True,
            }
        }

        # Submit job
        self.logger.info("Submitting transcription job...")
        response = requests.post(run_url, json=payload, headers=headers)

        self.logger.debug(f"Response status code: {response.status_code}")
        try:
            self.logger.debug(f"Response content: {json.dumps(response.json(), indent=2)}")
        except:
            self.logger.debug(f"Raw response content: {response.text}")

        response.raise_for_status()
        job_id = response.json()["id"]

        # Poll for results
        self.logger.info("Waiting for results...")
        while True:
            status_response = requests.get(f"{status_url}/{job_id}", headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()

            if status_data["status"] == "COMPLETED":
                return status_data["output"]
            elif status_data["status"] == "FAILED":
                raise Exception(f"Transcription failed: {status_data.get('error', 'Unknown error')}")

            sleep(2)  # Wait 2 seconds before checking again


if __name__ == "__main__":
    # Example usage
    import logging

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        audio_file = input("Enter the path to your audio file: ")

    transcriber = WhisperTranscriber()
    results = transcriber.transcribe(audio_file)

    output_file = f"transcription_results_{WhisperTranscriber._get_file_md5(audio_file)}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Transcription completed! Results saved to {output_file}")
