import pytest
import os
import json
import requests
import tempfile
from unittest.mock import Mock, patch, call
from lyrics_transcriber.transcribers.whisper import (
    WhisperConfig,
    RunPodAPI,
    AudioProcessor,
    WhisperTranscriber,
    FileStorageProtocol,
    TranscriptionError,
    TranscriptionData,
)


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


class TestRunPodAPI:
    @pytest.fixture
    def api(self, config, mock_logger):
        return RunPodAPI(config, mock_logger)

    def test_init_without_required_config(self, mock_logger):
        with pytest.raises(ValueError, match="RunPod API key and endpoint ID must be provided"):
            RunPodAPI(WhisperConfig(), mock_logger)

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

    def test_submit_job_invalid_json(self, api):
        """Test handling of invalid JSON response"""
        with patch("requests.post") as mock_post:
            # Create a mock response that will fail JSON parsing
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.text = "Invalid response"
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Should raise TranscriptionError with the raw response text
            with pytest.raises(TranscriptionError, match="Invalid JSON response: Invalid response"):
                api.submit_job("https://test.com/audio.mp3")

            # Verify that debug logging was called with raw text
            api.logger.debug.assert_any_call("Raw response content: Invalid response")


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
    def transcriber(self, config, mock_logger, mock_runpod, mock_storage, mock_audio_processor):
        return WhisperTranscriber(
            config=config, logger=mock_logger, runpod_client=mock_runpod, storage_client=mock_storage, audio_processor=mock_audio_processor
        )

    def test_init_with_env_vars(self):
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
            transcriber = WhisperTranscriber()
            assert transcriber.config.runpod_api_key == "env_key"
            assert transcriber.config.endpoint_id == "env_endpoint"

    def test_get_name(self, transcriber):
        assert transcriber.get_name() == "Whisper"

    def test_upload_and_get_link_new_file(self, transcriber, tmp_path):
        test_file = tmp_path / "test.flac"
        test_file.write_text("test content")

        url = transcriber._upload_and_get_link(str(test_file), "/test/path.flac")

        assert url == "https://test.com/audio.mp3"
        transcriber.storage.upload_with_retry.assert_called_once()
        transcriber.storage.create_or_get_shared_link.assert_called_once()

    def test_upload_and_get_link_existing_file(self, transcriber):
        transcriber.storage.file_exists.return_value = True

        url = transcriber._upload_and_get_link("test.flac", "/test/path.flac")

        assert url == "https://test.com/audio.mp3"
        transcriber.storage.upload_with_retry.assert_not_called()
        transcriber.storage.create_or_get_shared_link.assert_called_once()

    @patch("lyrics_transcriber.transcribers.whisper.sleep")
    def test_perform_transcription_success(self, mock_sleep, transcriber):
        # Set up the sequence of responses
        transcriber.runpod.submit_job.return_value = "job123"
        transcriber.runpod.get_job_status.side_effect = [
            {"status": "IN_PROGRESS"},
            {
                "status": "COMPLETED",
                "output": {
                    "segments": [
                        {
                            "text": "test",
                            "start": 0.0,
                            "end": 1.0,
                            "words": [{"text": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
                        }
                    ],
                    "transcription": "test",
                    "detected_language": "en",
                    "word_timestamps": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
                },
            },
        ]

        result = transcriber._perform_transcription("https://test.com/audio.mp3")

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "Whisper"
        assert result.metadata["language"] == "en"

    @patch("time.sleep")
    def test_perform_transcription_failure(self, mock_sleep, transcriber):
        transcriber.runpod.submit_job.return_value = "job123"
        transcriber.runpod.get_job_status.return_value = {"status": "FAILED", "error": "Test error"}

        with pytest.raises(TranscriptionError, match="Test error"):
            transcriber._perform_transcription("https://test.com/audio.mp3")

    def test_transcribe_full_flow(self, transcriber, tmp_path):
        # Create test files
        test_wav = tmp_path / "test.wav"
        test_wav.write_text("test content")
        test_flac = tmp_path / "test.flac"
        test_flac.write_text("test content")

        # Mock audio processor
        transcriber.audio_processor.get_file_md5.return_value = "test_hash"
        transcriber.audio_processor.convert_to_flac.return_value = str(test_flac)

        # Mock responses
        transcriber.runpod.submit_job.return_value = "job123"
        transcriber.runpod.get_job_status.return_value = {
            "status": "COMPLETED",
            "output": {
                "segments": [
                    {"text": "test", "start": 0.0, "end": 1.0, "words": [{"text": "test", "start": 0.0, "end": 1.0, "probability": 0.9}]}
                ],
                "transcription": "test",
                "detected_language": "en",
                "word_timestamps": [{"word": "test", "start": 0.0, "end": 1.0, "probability": 0.9}],
            },
        }

        result = transcriber.transcribe(str(test_wav))

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "Whisper"
        assert result.metadata["language"] == "en"
