from dataclasses import dataclass
import requests
import time
import os
from typing import Dict, Optional, Any, Union
from pathlib import Path
from lyrics_transcriber.types import TranscriptionData, LyricsSegment, Word
from lyrics_transcriber.transcribers.base_transcriber import BaseTranscriber, TranscriptionError
from lyrics_transcriber.utils.word_utils import WordUtils


@dataclass
class AudioShakeConfig:
    """Configuration for AudioShake transcription service."""

    api_token: Optional[str] = None
    base_url: str = "https://groovy.audioshake.ai"
    output_prefix: Optional[str] = None
    timeout_minutes: int = 10  # Added timeout configuration


class AudioShakeAPI:
    """Handles direct API interactions with AudioShake."""

    def __init__(self, config: AudioShakeConfig, logger):
        self.config = config
        self.logger = logger

    def _validate_config(self) -> None:
        """Validate API configuration."""
        if not self.config.api_token:
            raise ValueError("AudioShake API token must be provided")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        self._validate_config()  # Validate before making any API calls
        return {"Authorization": f"Bearer {self.config.api_token}", "Content-Type": "application/json"}

    def upload_file(self, filepath: str) -> str:
        """Upload audio file and return asset ID."""
        self.logger.info(f"Uploading {filepath} to AudioShake")
        self._validate_config()  # Validate before making API call

        url = f"{self.config.base_url}/upload/"
        with open(filepath, "rb") as file:
            files = {"file": (os.path.basename(filepath), file)}
            response = requests.post(url, headers={"Authorization": self._get_headers()["Authorization"]}, files=files)

        self.logger.debug(f"Upload response: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json()["id"]

    def create_job(self, asset_id: str) -> str:
        """Create transcription job and return job ID."""
        self.logger.info(f"Creating job for asset {asset_id}")

        url = f"{self.config.base_url}/job/"
        data = {
            "metadata": {"format": "json", "name": "alignment", "language": "en"},
            "callbackUrl": "https://example.com/webhook/alignment",
            "assetId": asset_id,
        }
        response = requests.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()["job"]["id"]

    def wait_for_job_result(self, job_id: str) -> Dict[str, Any]:
        """Poll for job completion and return results."""
        self.logger.info(f"Getting job result for job {job_id}")

        url = f"{self.config.base_url}/job/{job_id}"
        start_time = time.time()
        last_status_log = start_time
        timeout_seconds = self.config.timeout_minutes * 60
        
        # Add initial retry logic for 404 errors (job ID not yet available)
        initial_retry_count = 0
        max_initial_retries = 5
        initial_retry_delay = 2  # seconds

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Check for timeout
            if elapsed_time > timeout_seconds:
                raise TranscriptionError(f"Transcription timed out after {self.config.timeout_minutes} minutes")

            # Log status every minute
            if current_time - last_status_log >= 60:
                self.logger.info(f"Still waiting for transcription... " f"Elapsed time: {int(elapsed_time/60)} minutes")
                last_status_log = current_time

            try:
                response = requests.get(url, headers=self._get_headers())
                response.raise_for_status()
                job_data = response.json()["job"]

                if job_data["status"] == "completed":
                    return job_data
                elif job_data["status"] == "failed":
                    raise TranscriptionError(f"Job failed: {job_data.get('error', 'Unknown error')}")

                # Reset retry count on successful response
                initial_retry_count = 0
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404 and initial_retry_count < max_initial_retries:
                    # Job ID not yet available, retry with delay
                    initial_retry_count += 1
                    self.logger.info(f"Job ID not yet available (attempt {initial_retry_count}/{max_initial_retries}), retrying in {initial_retry_delay} seconds...")
                    time.sleep(initial_retry_delay)
                    continue
                else:
                    # Re-raise the error if it's not a 404 or we've exceeded retries
                    raise

            time.sleep(5)  # Wait before next poll


class AudioShakeTranscriber(BaseTranscriber):
    """Transcription service using AudioShake's API."""

    def __init__(
        self,
        cache_dir: Union[str, Path],
        config: Optional[AudioShakeConfig] = None,
        logger: Optional[Any] = None,
        api_client: Optional[AudioShakeAPI] = None,
    ):
        """Initialize AudioShake transcriber."""
        super().__init__(cache_dir=cache_dir, logger=logger)
        self.config = config or AudioShakeConfig(api_token=os.getenv("AUDIOSHAKE_API_TOKEN"))
        self.api = api_client or AudioShakeAPI(self.config, self.logger)

    def get_name(self) -> str:
        return "AudioShake"

    def _perform_transcription(self, audio_filepath: str) -> TranscriptionData:
        """Actually perform the transcription using AudioShake API."""
        self.logger.debug(f"Entering _perform_transcription() for {audio_filepath}")
        self.logger.info(f"Starting transcription for {audio_filepath}")

        try:
            # Start job and get results
            self.logger.debug("Calling start_transcription()")
            job_id = self.start_transcription(audio_filepath)
            self.logger.debug(f"Got job_id: {job_id}")

            self.logger.debug("Calling get_transcription_result()")
            result = self.get_transcription_result(job_id)
            self.logger.debug("Got transcription result")

            return result
        except Exception as e:
            self.logger.error(f"Error in _perform_transcription: {str(e)}")
            raise

    def start_transcription(self, audio_filepath: str) -> str:
        """Starts the transcription job and returns the job ID."""
        self.logger.debug(f"Entering start_transcription() for {audio_filepath}")

        # Upload file and create job
        asset_id = self.api.upload_file(audio_filepath)
        self.logger.debug(f"File uploaded successfully. Asset ID: {asset_id}")

        job_id = self.api.create_job(asset_id)
        self.logger.debug(f"Job created successfully. Job ID: {job_id}")

        return job_id

    def get_transcription_result(self, job_id: str) -> Dict[str, Any]:
        """Gets the raw results for a previously started job."""
        self.logger.debug(f"Entering get_transcription_result() for job ID: {job_id}")

        # Wait for job completion
        job_data = self.api.wait_for_job_result(job_id)
        self.logger.debug("Job completed. Getting results...")

        output_asset = next((asset for asset in job_data.get("outputAssets", []) if asset["name"] == "alignment.json"), None)
        if not output_asset:
            raise TranscriptionError("Required output not found in job results")

        # Fetch transcription data
        response = requests.get(output_asset["link"])
        response.raise_for_status()

        # Return combined raw data
        raw_data = {"job_data": job_data, "transcription": response.json()}

        self.logger.debug("Raw results retrieved successfully")
        return raw_data

    def _convert_result_format(self, raw_data: Dict[str, Any]) -> TranscriptionData:
        """Process raw Audioshake API response into standard format."""
        self.logger.debug(f"Processing result for job {raw_data['job_data']['id']}")

        transcription_data = raw_data["transcription"]
        job_data = raw_data["job_data"]

        segments = []
        all_words = []  # Collect all words across segments

        for line in transcription_data.get("lines", []):
            words = [
                Word(
                    id=WordUtils.generate_id(),  # Generate unique ID for each word
                    text=word["text"].strip(" "),
                    start_time=word.get("start", 0.0),
                    end_time=word.get("end", 0.0),
                )
                for word in line.get("words", [])
            ]
            all_words.extend(words)  # Add words to flat list

            segments.append(
                LyricsSegment(
                    id=WordUtils.generate_id(),  # Generate unique ID for each segment
                    text=line.get("text", " ".join(w.text for w in words)),
                    words=words,
                    start_time=min((w.start_time for w in words), default=0.0),
                    end_time=max((w.end_time for w in words), default=0.0),
                )
            )

        return TranscriptionData(
            text=transcription_data.get("text", ""),
            words=all_words,
            segments=segments,
            source=self.get_name(),
            metadata={
                "language": transcription_data.get("metadata", {}).get("language"),
                "job_id": job_data["id"],
                "duration": job_data.get("statusInfo", {}).get("duration"),
            },
        )

    def get_output_filename(self, suffix: str) -> str:
        """Generate consistent filename with (Purpose) suffix pattern."""
        return f"{self.config.output_prefix}{suffix}"
