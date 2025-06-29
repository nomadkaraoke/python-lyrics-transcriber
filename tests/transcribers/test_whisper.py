import pytest
import os
import requests
import tempfile
from unittest.mock import Mock, patch, call, mock_open
from lyrics_transcriber.transcribers.whisper import (
    WhisperConfig,
    RunPodWhisperAPI,
    AudioProcessor,
    WhisperTranscriber,
    FileStorageProtocol,
    TranscriptionError,
    TranscriptionData,
    LyricsSegment,
    Word,
)
from tests.test_helpers import create_test_word, create_test_segment


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return WhisperConfig(
        runpod_api_key="test_key",
        endpoint_id="test_endpoint",
        dropbox_app_key="test_dropbox_key",
        dropbox_app_secret="test_dropbox_secret",
        dropbox_refresh_token="test_refresh_token",
    )


@pytest.fixture
def mock_storage():
    storage = Mock(spec=FileStorageProtocol)
    storage.file_exists.return_value = False
    storage.create_or_get_shared_link.return_value = "https://test.com/audio.mp3"
    return storage


class TestWhisperConfig:
    def test_default_config(self):
        config = WhisperConfig()
        assert config.runpod_api_key is None
        assert config.endpoint_id is None
        assert config.dropbox_app_key is None
        assert config.dropbox_app_secret is None
        assert config.dropbox_refresh_token is None

    def test_custom_config(self, config):
        assert config.runpod_api_key == "test_key"
        assert config.endpoint_id == "test_endpoint"
        assert config.dropbox_app_key == "test_dropbox_key"


class TestRunPodWhisperAPI:
    @pytest.fixture
    def api(self):
        """Create a RunPodWhisperAPI instance with mocked dependencies."""
        config = WhisperConfig(runpod_api_key="test_key", endpoint_id="test_endpoint")
        logger = Mock()
        api = RunPodWhisperAPI(config=config, logger=logger)
        return api

    def test_init_without_required_config(self, mock_logger):
        with pytest.raises(ValueError, match="RunPod API key and endpoint ID must be provided"):
            RunPodWhisperAPI(WhisperConfig(), mock_logger)

    @patch("requests.post")
    def test_submit_job(self, mock_post, api):
        mock_response = Mock()
        mock_response.json.return_value = {"id": "job123"}
        mock_post.return_value = mock_response

        job_id = api.submit_job("https://test.com/audio.mp3")

        assert job_id == "job123"
        mock_post.assert_called_once()
        api.logger.info.assert_called_with("Submitting transcription job...")

    @patch("requests.post")
    def test_submit_job_error(self, mock_post, api):
        mock_post.side_effect = requests.RequestException("API Error")

        with pytest.raises(requests.RequestException):
            api.submit_job("https://test.com/audio.mp3")

    @patch("requests.get")
    def test_get_job_status(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "COMPLETED"}
        mock_get.return_value = mock_response

        status = api.get_job_status("job123")

        assert status == {"status": "COMPLETED"}
        mock_get.assert_called_once()

    @patch("requests.post")
    def test_submit_job_invalid_json(self, mock_post, api):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid response"
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(TranscriptionError, match="Invalid JSON response: Invalid response"):
            api.submit_job("https://test.com/audio.mp3")

        api.logger.debug.assert_any_call("Raw response content: Invalid response")

    @patch("requests.get")
    @patch("time.sleep")
    def test_wait_for_job_result(self, mock_sleep, mock_get, api):
        """Test polling behavior with in-progress status before completion"""
        mock_responses = [
            Mock(json=lambda: {"status": "IN_PROGRESS"}),
            Mock(json=lambda: {"status": "IN_PROGRESS"}),
            Mock(json=lambda: {"status": "COMPLETED", "output": {"result": "test"}}),
        ]
        mock_get.side_effect = mock_responses

        result = api.wait_for_job_result("job123")

        assert result == {"result": "test"}
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(5)
        api.logger.info.assert_called_with("Getting job result for job job123")

    @patch("requests.get")
    @patch("time.time")
    def test_wait_for_job_result_timeout(self, mock_time, mock_get, api):
        """Test that job polling times out after configured duration"""
        mock_time.side_effect = [0, api.config.timeout_minutes * 60 + 1]  # Simulate timeout
        mock_get.return_value = Mock(json=lambda: {"status": "IN_PROGRESS"})

        with pytest.raises(TranscriptionError, match=f"Transcription timed out after {api.config.timeout_minutes} minutes"):
            api.wait_for_job_result("job123")

        api.cancel_job.assert_called_once_with("job123")

    @patch("requests.get")
    def test_wait_for_job_result_failure(self, mock_get, api):
        """Test handling of failed job status"""
        mock_get.return_value = Mock(json=lambda: {"status": "FAILED", "error": "Test error"})

        with pytest.raises(TranscriptionError, match="Transcription failed: Test error"):
            api.wait_for_job_result("job123")

    @patch("requests.post")
    def test_cancel_job(self, mock_post, api):
        """Test job cancellation"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        api.cancel_job("job123")

        # Verify the API call
        expected_url = f"https://api.runpod.ai/v2/{api.config.endpoint_id}/cancel/job123"
        expected_headers = {"Authorization": f"Bearer {api.config.runpod_api_key}"}
        mock_post.assert_called_once_with(expected_url, headers=expected_headers)

    @patch("requests.post")
    def test_cancel_job_error(self, mock_post, api):
        """Test error handling in cancel_job"""
        # Configure the mock to raise an exception
        mock_post.side_effect = requests.RequestException("API Error")

        # Should not raise exception
        api.cancel_job("job123")

        # Verify the warning was logged
        api.logger.warning.assert_called_once_with("Failed to cancel job job123: API Error")

    @patch("requests.post")
    def test_cancel_job_success(self, mock_post, api):
        """Test successful job cancellation"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        api.cancel_job("job123")

        # Verify no warnings were logged
        api.logger.warning.assert_not_called()

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_wait_for_job_result_periodic_logging(self, mock_sleep, mock_get, api):
        """Test periodic status logging during job polling"""
        # Set up mock responses
        mock_responses = [
            Mock(json=lambda: {"status": "IN_PROGRESS"}),
            Mock(json=lambda: {"status": "IN_PROGRESS"}),
            Mock(json=lambda: {"status": "COMPLETED", "output": {"result": "test"}}),
        ]
        mock_get.side_effect = mock_responses

        # Mock time to trigger periodic logging
        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 30, 61, 90]  # First log at 61 seconds
            result = api.wait_for_job_result("job123")

        assert result == {"result": "test"}
        # Verify periodic logging occurred
        api.logger.info.assert_has_calls(
            [call("Getting job result for job job123"), call("Still waiting for transcription... Elapsed time: 1 minutes")]
        )

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    @patch("time.time")
    def test_wait_for_job_result_timeout(self, mock_time, mock_sleep, mock_get, api):
        """Test job result timeout"""
        # Set up time to trigger timeout
        mock_time.side_effect = [0, 601]  # Start at 0, then jump past timeout
        api.config.timeout_minutes = 10

        # Set up status response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "IN_PROGRESS"}
        mock_get.return_value = mock_response

        with pytest.raises(TranscriptionError, match="Transcription timed out after 10 minutes"):
            api.wait_for_job_result("job123")

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_wait_for_job_result_failure(self, mock_sleep, mock_get, api):
        """Test handling of failed job"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "FAILED", "error": "Test error message"}
        mock_get.return_value = mock_response

        with pytest.raises(TranscriptionError, match="Transcription failed: Test error message"):
            api.wait_for_job_result("job123")

    @patch("requests.get")
    def test_get_job_status_error(self, mock_get, api):
        """Test error handling in get_job_status"""
        mock_get.side_effect = requests.RequestException("API Error")

        with pytest.raises(requests.RequestException):
            api.get_job_status("job123")


class TestAudioProcessor:
    @pytest.fixture
    def processor(self, mock_logger):
        return AudioProcessor(mock_logger)

    def test_get_file_md5(self, processor, tmp_path):
        test_file = tmp_path / "test.wav"
        test_file.write_text("test content")

        md5 = processor.get_file_md5(str(test_file))
        assert isinstance(md5, str)
        assert len(md5) == 32

    @patch("pydub.AudioSegment.from_wav")
    def test_convert_to_flac(self, mock_from_wav, processor):
        mock_audio = Mock()
        mock_from_wav.return_value = mock_audio

        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_wav:
            result = processor.convert_to_flac(temp_wav.name)

        assert result.endswith(".flac")
        mock_from_wav.assert_called_once()
        mock_audio.export.assert_called_once()

    def test_convert_to_flac_non_wav(self, processor):
        result = processor.convert_to_flac("test.mp3")
        assert result == "test.mp3"


class TestWhisperTranscriber:
    @pytest.fixture
    def mock_runpod(self):
        return Mock()

    @pytest.fixture
    def mock_audio_processor(self):
        processor = Mock()
        processor.get_file_md5.return_value = "test_hash"
        processor.convert_to_flac.return_value = "test.flac"
        return processor

    @pytest.fixture
    def transcriber(self, config, mock_logger, mock_runpod, mock_storage, mock_audio_processor, tmp_path):
        # Only create the transcriber with mocked external dependencies
        return WhisperTranscriber(
            config=config,
            logger=mock_logger,
            runpod_client=mock_runpod,
            storage_client=mock_storage,
            audio_processor=mock_audio_processor,
            cache_dir=tmp_path,
        )

    def test_init_with_env_vars(self, tmp_path):
        """Test initialization with environment variables."""
        with patch.dict(
            os.environ,
            {
                "RUNPOD_API_KEY": "env_key",
                "WHISPER_RUNPOD_ID": "env_endpoint",
                "WHISPER_DROPBOX_APP_KEY": "dropbox_key",
                "WHISPER_DROPBOX_APP_SECRET": "dropbox_secret",
                "WHISPER_DROPBOX_REFRESH_TOKEN": "dropbox_token",
            },
        ):
            transcriber = WhisperTranscriber(cache_dir=tmp_path)
            assert transcriber.config.runpod_api_key == "env_key"
            assert transcriber.config.endpoint_id == "env_endpoint"

    def test_get_name(self, transcriber):
        assert transcriber.get_name() == "Whisper"

    @patch("builtins.open", new_callable=mock_open, read_data="test data")
    def test_upload_and_get_link_new_file(self, mock_file, transcriber):
        """Test uploading a new file and getting its link"""
        transcriber.storage.file_exists.return_value = False
        transcriber.storage.create_or_get_shared_link.return_value = "https://test.com/audio.flac"

        result = transcriber._upload_and_get_link("test.flac", "/test/path.flac")

        assert result == "https://test.com/audio.flac"
        mock_file.assert_called_once_with("test.flac", "rb")
        transcriber.storage.upload_with_retry.assert_called_once()
        transcriber.storage.create_or_get_shared_link.assert_called_once_with("/test/path.flac")

    def test_upload_and_get_link_existing_file(self, transcriber):
        transcriber.storage.file_exists.return_value = True

        url = transcriber._upload_and_get_link("test.flac", "/test/path.flac")

        assert url == "https://test.com/audio.mp3"
        transcriber.storage.upload_with_retry.assert_not_called()
        transcriber.storage.create_or_get_shared_link.assert_called_once()

    def test_perform_transcription_success(self, transcriber):
        test_word = create_test_word(text="test", start_time=0.0, end_time=1.0, confidence=0.9)
        test_segment = create_test_segment(text="test", words=[test_word], start_time=0.0, end_time=1.0)
        transcriber.start_transcription = Mock(return_value="job123")
        transcriber.get_transcription_result = Mock(
            return_value=TranscriptionData(
                segments=[test_segment],
                words=[test_word],
                text="test",
                source="Whisper",
                metadata={"language": "en", "model": "medium", "job_id": "job123"},
            )
        )

        result = transcriber._perform_transcription("test.wav")

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert len(result.words) == 1
        transcriber.start_transcription.assert_called_once_with("test.wav")
        transcriber.get_transcription_result.assert_called_once_with("job123")

    def test_start_transcription(self, transcriber):
        # Mock _prepare_audio_url to avoid file system operations
        transcriber._prepare_audio_url = Mock()
        transcriber._prepare_audio_url.return_value = ("https://test.com/audio.mp3", None)

        # Mock runpod client
        transcriber.runpod.submit_job.return_value = "job123"

        # Test with a URL
        job_id = transcriber.start_transcription("test.wav")
        assert job_id == "job123"

        transcriber._prepare_audio_url.assert_called_once_with("test.wav")
        transcriber.runpod.submit_job.assert_called_once_with("https://test.com/audio.mp3")

    def test_start_transcription_error_cleanup(self, transcriber):
        # Mock methods to simulate error
        transcriber._prepare_audio_url = Mock()
        transcriber._prepare_audio_url.return_value = ("https://test.com/audio.mp3", "temp.flac")
        transcriber.runpod.submit_job.side_effect = Exception("API Error")
        transcriber._cleanup_temporary_files = Mock()

        with pytest.raises(TranscriptionError, match="Failed to submit job: API Error"):
            transcriber.start_transcription("test.wav")

        transcriber._cleanup_temporary_files.assert_called_once_with("temp.flac")

    def test_get_transcription_result(self, transcriber):
        # Mock the API response
        raw_data = {
            "segments": [
                {
                    "text": "test",
                    "start": 0.0,
                    "end": 1.0,
                    "words": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
                }
            ],
            "transcription": "test",
            "detected_language": "en",
            "word_timestamps": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
        }
        transcriber.runpod.wait_for_job_result.return_value = raw_data

        result = transcriber._convert_result_format(transcriber.get_transcription_result("job123"))

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        transcriber.runpod.wait_for_job_result.assert_called_once_with("job123")

    def test_prepare_audio_url(self, transcriber):
        # Test with HTTP URL
        url, temp_file = transcriber._prepare_audio_url("https://test.com/audio.mp3")
        assert url == "https://test.com/audio.mp3"
        assert temp_file is None

        # Test with local file
        transcriber.audio_processor.get_file_md5.return_value = "test_hash"
        transcriber.audio_processor.convert_to_flac.return_value = "test.flac"
        transcriber._upload_and_get_link = Mock(return_value="https://dropbox.com/test.flac")

        url, temp_file = transcriber._prepare_audio_url("test.wav")
        assert url == "https://dropbox.com/test.flac"
        assert temp_file == "test.flac"

        # Verify the correct path was used for upload
        transcriber._upload_and_get_link.assert_called_once_with("test.flac", "/transcription_temp/test_hash.flac")

    def test_cleanup_temporary_files(self, transcriber, tmp_path):
        # Create a temporary test file
        test_file = tmp_path / "test.flac"
        test_file.write_text("test content")

        # Test cleanup of existing file
        transcriber._cleanup_temporary_files(str(test_file))
        assert not test_file.exists()
        transcriber.logger.debug.assert_called_with(f"Cleaned up temporary file: {str(test_file)}")

        # Test cleanup of non-existent file
        transcriber._cleanup_temporary_files("nonexistent.flac")
        transcriber.logger.warning.assert_not_called()

        # Test cleanup with None
        transcriber._cleanup_temporary_files(None)
        transcriber.logger.warning.assert_not_called()

    def test_transcribe_full_flow(self, transcriber, tmp_path):
        # Create test files
        test_wav = tmp_path / "test.wav"
        test_wav.write_text("test content")
        test_flac = tmp_path / "test.flac"
        test_flac.write_text("test content")

        # Mock storage methods
        transcriber.storage.file_exists.return_value = False
        transcriber.storage.create_or_get_shared_link.return_value = "https://test.com/audio.mp3"

        # Mock audio processor
        transcriber.audio_processor.get_file_md5.return_value = "test_hash"
        transcriber.audio_processor.convert_to_flac.return_value = str(test_flac)

        # Mock RunPod responses
        transcriber.runpod.submit_job.return_value = "job123"
        transcriber.runpod.wait_for_job_result.return_value = {
            "segments": [
                {"text": "test", "start": 0.0, "end": 1.0, "words": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}]}
            ],
            "transcription": "test",
            "detected_language": "en",
            "word_timestamps": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
        }

        result = transcriber.transcribe(str(test_wav))

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1

    def test_initialize_storage_without_config(self, transcriber, mock_logger):
        """Test storage initialization without environment variables"""
        with patch.dict(os.environ, clear=True):
            with patch("lyrics_transcriber.storage.dropbox.DropboxHandler") as mock_handler:
                # Configure the mock to return itself when instantiated
                mock_instance = Mock()
                mock_handler.return_value = mock_instance

                storage = transcriber._initialize_storage()

                assert storage == mock_instance
                mock_handler.assert_called_once()

    @patch("requests.post")
    def test_transcribe_api_error(self, mock_post, transcriber, tmp_path):
        """Test transcription with API error"""
        # Create test file
        test_file = tmp_path / "test.wav"
        test_file.write_text("test content")

        # Mock audio processor methods
        transcriber.audio_processor.get_file_md5.return_value = "test_hash"
        transcriber.audio_processor.convert_to_flac.return_value = str(tmp_path / "test.flac")

        # Create the test FLAC file
        test_flac = tmp_path / "test.flac"
        test_flac.write_text("test flac content")

        # Mock storage methods
        transcriber.storage.file_exists.return_value = False
        transcriber.storage.create_or_get_shared_link.return_value = "https://test.com/audio.flac"

        # Mock RunPod API error
        transcriber.runpod.submit_job.side_effect = requests.RequestException("API Error")

        with pytest.raises(TranscriptionError, match="Failed to submit job: API Error"):
            transcriber.transcribe(str(test_file))

    def test_transcribe_invalid_response(self, transcriber, tmp_path):
        """Test transcription with invalid API response"""
        # Create test file
        test_file = tmp_path / "test.wav"
        test_file.write_text("test content")

        # Mock audio processor methods
        transcriber.audio_processor.get_file_md5.return_value = "test_hash"
        transcriber.audio_processor.convert_to_flac.return_value = str(tmp_path / "test.flac")

        # Create the test FLAC file
        test_flac = tmp_path / "test.flac"
        test_flac.write_text("test flac content")

        # Mock storage methods
        transcriber.storage.file_exists.return_value = False
        transcriber.storage.create_or_get_shared_link.return_value = "https://test.com/audio.flac"

        # Mock RunPod responses
        transcriber.runpod.submit_job.return_value = "job123"
        transcriber.runpod.wait_for_job_result.return_value = {"invalid": "response"}

        # Mock the result to be a proper dictionary
        mock_result = {"invalid": "response"}
        transcriber.runpod.wait_for_job_result.return_value = mock_result

        with pytest.raises(TranscriptionError, match="Response missing required 'segments' field"):
            transcriber.transcribe(str(test_file))

    @patch("os.remove")
    def test_cleanup_temporary_files_error(self, mock_remove, transcriber, tmp_path):
        """Test error handling during file cleanup"""
        test_file = tmp_path / "test.flac"
        test_file.write_text("test content")

        # Simulate permission error during removal
        mock_remove.side_effect = OSError("Permission denied")

        transcriber._cleanup_temporary_files(str(test_file))

        # Verify warning was logged
        transcriber.logger.warning.assert_called_once_with(f"Failed to clean up temporary file {str(test_file)}: Permission denied")

    def test_validate_response_missing_fields(self, transcriber):
        """Test validation of responses missing required fields"""
        # Test missing segments
        with pytest.raises(TranscriptionError, match="Response missing required 'segments' field"):
            transcriber._validate_response({"transcription": "test"})

        # Test missing transcription
        with pytest.raises(TranscriptionError, match="Response missing required 'transcription' field"):
            transcriber._validate_response({"segments": []})
