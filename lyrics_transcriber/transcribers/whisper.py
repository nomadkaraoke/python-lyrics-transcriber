#! /usr/bin/env python3
from dataclasses import dataclass
import os
import json
import requests
import hashlib
import tempfile
from time import sleep
from typing import Optional, Dict, Any, Protocol
from pydub import AudioSegment
from .base import BaseTranscriber, TranscriptionData, LyricsSegment, Word, TranscriptionError


@dataclass
class WhisperConfig:
    """Configuration for Whisper transcription service."""

    runpod_api_key: Optional[str] = None
    endpoint_id: Optional[str] = None
    dropbox_app_key: Optional[str] = None
    dropbox_app_secret: Optional[str] = None
    dropbox_refresh_token: Optional[str] = None
    dropbox_access_token: Optional[str] = None


class FileStorageProtocol(Protocol):
    """Protocol for file storage operations."""

    def file_exists(self, path: str) -> bool: ...  # pragma: no cover
    def upload_with_retry(self, file: Any, path: str) -> None: ...  # pragma: no cover
    def create_or_get_shared_link(self, path: str) -> str: ...  # pragma: no cover


class RunPodAPI:
    """Handles interactions with RunPod API."""

    def __init__(self, config: WhisperConfig, logger):
        self.config = config
        self.logger = logger
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate API configuration."""
        if not self.config.runpod_api_key or not self.config.endpoint_id:
            raise ValueError("RunPod API key and endpoint ID must be provided")

    def submit_job(self, audio_url: str) -> str:
        """Submit transcription job and return job ID."""
        run_url = f"https://api.runpod.ai/v2/{self.config.endpoint_id}/run"
        headers = {"Authorization": f"Bearer {self.config.runpod_api_key}"}

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

        self.logger.info("Submitting transcription job...")
        response = requests.post(run_url, json=payload, headers=headers)

        self.logger.debug(f"Response status code: {response.status_code}")

        # Try to parse and log the JSON response
        try:
            response_json = response.json()
            self.logger.debug(f"Response content: {json.dumps(response_json, indent=2)}")
        except ValueError:
            self.logger.debug(f"Raw response content: {response.text}")
            # Re-raise if we can't parse the response at all
            raise TranscriptionError(f"Invalid JSON response: {response.text}")

        response.raise_for_status()
        return response_json["id"]

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and results."""
        status_url = f"https://api.runpod.ai/v2/{self.config.endpoint_id}/status/{job_id}"
        headers = {"Authorization": f"Bearer {self.config.runpod_api_key}"}

        response = requests.get(status_url, headers=headers)
        response.raise_for_status()
        return response.json()


class AudioProcessor:
    """Handles audio file processing."""

    def __init__(self, logger):
        self.logger = logger

    def get_file_md5(self, filepath: str) -> str:
        """Calculate MD5 hash of a file."""
        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def convert_to_flac(self, filepath: str) -> str:
        """Convert WAV to FLAC if needed for faster upload."""
        if not filepath.lower().endswith(".wav"):
            return filepath

        self.logger.info("Converting WAV to FLAC for faster upload...")
        audio = AudioSegment.from_wav(filepath)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as temp_flac:
            flac_path = temp_flac.name
            audio.export(flac_path, format="flac")

        return flac_path


class WhisperTranscriber(BaseTranscriber):
    """Transcription service using Whisper API via RunPod."""

    def __init__(
        self,
        config: Optional[WhisperConfig] = None,
        logger=None,
        runpod_client: Optional[RunPodAPI] = None,
        storage_client: Optional[FileStorageProtocol] = None,
        audio_processor: Optional[AudioProcessor] = None,
    ):
        super().__init__(logger)

        # Initialize configuration
        self.config = config or WhisperConfig(
            runpod_api_key=os.getenv("RUNPOD_API_KEY"),
            endpoint_id=os.getenv("WHISPER_RUNPOD_ID"),
            dropbox_app_key=os.getenv("WHISPER_DROPBOX_APP_KEY"),
            dropbox_app_secret=os.getenv("WHISPER_DROPBOX_APP_SECRET"),
            dropbox_refresh_token=os.getenv("WHISPER_DROPBOX_REFRESH_TOKEN"),
            dropbox_access_token=os.getenv("WHISPER_DROPBOX_ACCESS_TOKEN"),
        )

        # Initialize components (with dependency injection)
        self.runpod = runpod_client or RunPodAPI(self.config, self.logger)
        self.storage = storage_client or self._initialize_storage()
        self.audio_processor = audio_processor or AudioProcessor(self.logger)

    def _initialize_storage(self) -> FileStorageProtocol:
        """Initialize storage client."""
        from ..storage.dropbox import DropboxHandler, DropboxConfig

        config = DropboxConfig(
            app_key=self.config.dropbox_app_key,
            app_secret=self.config.dropbox_app_secret,
            refresh_token=self.config.dropbox_refresh_token,
            access_token=self.config.dropbox_access_token,
        )
        return DropboxHandler(config=config)

    def get_name(self) -> str:
        return "Whisper"

    def _perform_transcription(self, audio_filepath: str) -> TranscriptionData:
        """Actually perform the transcription using Whisper API."""
        self.logger.info(f"Starting transcription for {audio_filepath}")
        processed_filepath = None

        try:
            # If input is already a URL, use it directly
            if audio_filepath.startswith(("http://", "https://")):
                audio_url = audio_filepath
            else:
                # Process and upload local file
                file_hash = self.audio_processor.get_file_md5(audio_filepath)
                processed_filepath = self.audio_processor.convert_to_flac(audio_filepath)

                # Upload and get URL
                dropbox_path = f"/transcription_temp/{file_hash}{os.path.splitext(processed_filepath)[1]}"
                audio_url = self._upload_and_get_link(processed_filepath, dropbox_path)

            # Run transcription
            try:
                job_id = self.runpod.submit_job(audio_url)
            except Exception as e:
                raise TranscriptionError(f"Failed to submit job: {str(e)}") from e

            while True:
                status_data = self.runpod.get_job_status(job_id)

                if status_data["status"] == "COMPLETED":
                    raw_data = status_data["output"]

                    # Convert to standard format
                    segments = []
                    for seg in raw_data.get("segments", []):
                        words = [
                            Word(text=word["text"], start_time=word["start"], end_time=word["end"], confidence=word.get("probability", 1.0))
                            for word in seg.get("words", [])
                        ]
                        segments.append(LyricsSegment(text=seg["text"], words=words, start_time=seg["start"], end_time=seg["end"]))

                    return TranscriptionData(
                        segments=segments,
                        text=raw_data["text"],
                        source=self.get_name(),
                        metadata={"language": raw_data.get("language", "en"), "model": "large-v2", "job_id": job_id},
                    )

                elif status_data["status"] == "FAILED":
                    raise TranscriptionError(f"Transcription failed: {status_data.get('error', 'Unknown error')}")

                sleep(2)

        except Exception as e:
            if not isinstance(e, TranscriptionError):
                raise TranscriptionError(f"Whisper transcription failed: {str(e)}") from e
            raise

        finally:
            # Clean up temporary FLAC file if it exists and is different from input
            if processed_filepath and processed_filepath != audio_filepath:
                try:
                    if os.path.exists(processed_filepath):
                        self.logger.debug(f"Cleaning up temporary file: {processed_filepath}")
                        os.unlink(processed_filepath)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary file: {e}")

    def _upload_and_get_link(self, filepath: str, dropbox_path: str) -> str:
        """Upload file to storage and return shared link."""
        if not self.storage.file_exists(dropbox_path):
            self.logger.info("Uploading file to storage...")
            with open(filepath, "rb") as f:
                self.storage.upload_with_retry(f, dropbox_path)
        else:
            self.logger.info("File already exists in storage, skipping upload...")

        audio_url = self.storage.create_or_get_shared_link(dropbox_path)
        self.logger.debug(f"Using shared link: {audio_url}")
        return audio_url
