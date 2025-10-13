import pytest
import requests
from unittest.mock import Mock, patch, mock_open
from lyrics_transcriber.types import TranscriptionData
from lyrics_transcriber.transcribers.audioshake import (
    AudioShakeConfig,
    AudioShakeAPI,
    AudioShakeTranscriber,
)
from lyrics_transcriber.transcribers.base_transcriber import TranscriptionError
import os


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return AudioShakeConfig(api_token="test_token")


class TestAudioShakeConfig:
    def test_default_config(self):
        config = AudioShakeConfig()
        assert config.api_token is None
        assert config.base_url == "https://groovy.audioshake.ai"
        assert config.output_prefix is None

    def test_custom_config(self):
        config = AudioShakeConfig(api_token="test_token", base_url="https://custom.url", output_prefix="test_prefix")
        assert config.api_token == "test_token"
        assert config.base_url == "https://custom.url"
        assert config.output_prefix == "test_prefix"


class TestAudioShakeAPI:
    @pytest.fixture
    def api(self, config, mock_logger):
        return AudioShakeAPI(config, mock_logger)

    def test_api_calls_without_token(self, mock_logger):
        """Test that API calls fail when no token is provided"""
        api = AudioShakeAPI(AudioShakeConfig(), mock_logger)

        # Test upload_file
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            api.upload_file("test.mp3")

        # Test create_task
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            api.create_task("https://example.com/file.mp3")

        # Test wait_for_task_result
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            api.wait_for_task_result("task123")

    def test_get_headers(self, api):
        headers = api._get_headers()
        assert headers["x-api-key"] == "test_token"
        assert headers["Content-Type"] == "application/json"

    @patch("requests.post")
    def test_upload_file(self, mock_post, api):
        mock_response = Mock()
        mock_response.json.return_value = {"id": "asset123", "link": "https://example.com/file.mp3"}
        mock_post.return_value = mock_response

        with patch("builtins.open", mock_open(read_data="test data")):
            file_url = api.upload_file("test.mp3")

        assert file_url == "https://example.com/file.mp3"
        mock_post.assert_called_once()
        api.logger.info.assert_called_with("Uploading test.mp3 to AudioShake")

    @patch("requests.post")
    def test_create_task(self, mock_post, api):
        mock_response = Mock()
        mock_response.json.return_value = {"id": "task123"}
        mock_post.return_value = mock_response

        task_id = api.create_task("https://example.com/file.mp3")

        assert task_id == "task123"
        mock_post.assert_called_once()
        api.logger.info.assert_called_with("Creating task for file https://example.com/file.mp3")

    @patch("requests.get")
    def test_wait_for_task_result_success(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "completed", "data": "test"}
        mock_get.return_value = mock_response

        result = api.wait_for_task_result("task123")

        assert result == {"status": "completed", "data": "test"}
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_wait_for_task_result_failure(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "failed", "error": "test error"}
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Task failed: test error"):
            api.wait_for_task_result("task123")

    @patch("requests.get")
    @patch("time.sleep")
    def test_wait_for_task_result_polling(self, mock_sleep, mock_get, api):
        """Test polling behavior with in-progress status before completion"""
        mock_responses = [
            Mock(json=lambda: {"status": "in_progress"}),
            Mock(json=lambda: {"status": "in_progress"}),
            Mock(json=lambda: {"status": "completed", "data": "test"}),
        ]
        mock_get.side_effect = mock_responses

        result = api.wait_for_task_result("task123")

        assert result == {"status": "completed", "data": "test"}
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(5)

    @patch("requests.get")
    def test_wait_for_task_result_with_retries(self, mock_get, api):
        """Test task result polling with network errors"""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            api.wait_for_task_result("task123")

        assert mock_get.call_count == 1  # Verify we don't retry on error

    @patch("requests.get")
    @patch("time.time")
    def test_wait_for_task_result_timeout(self, mock_time, mock_get, api):
        """Test that task polling times out after configured duration"""
        mock_time.side_effect = [0, api.config.timeout_minutes * 60 + 1]  # Simulate timeout
        mock_get.return_value = Mock(json=lambda: {"status": "in_progress"})

        with pytest.raises(TranscriptionError, match=f"Transcription timed out after {api.config.timeout_minutes} minutes"):
            api.wait_for_task_result("task123")

    @patch("requests.get")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_task_result_logs_status(self, mock_sleep, mock_time, mock_get, api):
        """Test that task polling logs status periodically"""
        mock_time.side_effect = [0, 30, 61, 90]  # Simulate time passing
        mock_get.side_effect = [
            Mock(json=lambda: {"status": "in_progress"}),
            Mock(json=lambda: {"status": "in_progress"}),
            Mock(json=lambda: {"status": "completed", "data": "test"}),
        ]

        result = api.wait_for_task_result("task123")

        # Verify periodic status logging
        api.logger.info.assert_any_call("Still waiting for transcription... Elapsed time: 1 minutes")

    @patch("requests.post")
    @patch("builtins.open", mock_open(read_data="test data"))
    def test_upload_file_failure(self, mock_post, api):
        """Test upload file with API error"""
        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            api.upload_file("test.mp3")

        api.logger.info.assert_called_with("Uploading test.mp3 to AudioShake")

    @patch("requests.post")
    def test_create_task_failure(self, mock_post, api):
        """Test create task with API error"""
        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            api.create_task("https://example.com/file.mp3")

        api.logger.info.assert_called_with("Creating task for file https://example.com/file.mp3")


class TestAudioShakeTranscriber:
    @pytest.fixture
    def mock_api(self):
        return Mock()

    @pytest.fixture
    def transcriber(self, mock_logger, mock_api, tmp_path):
        config = AudioShakeConfig(api_token="test_token")
        return AudioShakeTranscriber(config=config, logger=mock_logger, api_client=mock_api, cache_dir=tmp_path)

    def test_init_with_token(self, transcriber):
        assert transcriber.config.api_token == "test_token"
        assert transcriber.api is not None

    def test_init_with_env_var(self, mock_logger, tmp_path):
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"AUDIOSHAKE_API_TOKEN": "env_token"}):
            transcriber = AudioShakeTranscriber(cache_dir=tmp_path, logger=mock_logger)
            assert transcriber.config.api_token == "env_token"

    def test_init_without_token(self, mock_logger, tmp_path):
        """Test initialization without token."""
        with patch.dict(os.environ, clear=True):
            transcriber = AudioShakeTranscriber(cache_dir=tmp_path, logger=mock_logger)
            assert transcriber.config.api_token is None
            # API initialization will fail when actually used

    def test_get_name(self, transcriber):
        assert transcriber.get_name() == "AudioShake"

    def test_start_transcription(self, transcriber, mock_api):
        mock_api.upload_file.return_value = "https://example.com/file.mp3"
        mock_api.create_task.return_value = "task123"

        task_id = transcriber.start_transcription("test.mp3")

        assert task_id == "task123"
        mock_api.upload_file.assert_called_once_with("test.mp3")
        mock_api.create_task.assert_called_once_with("https://example.com/file.mp3")

    def test_get_transcription_result(self, transcriber, mock_api):
        mock_task_data = {
            "id": "task123",
            "targets": [
                {
                    "model": "alignment",
                    "outputs": [{"link": "http://test.com/result"}]
                }
            ],
            "duration": 60.0,
        }
        mock_api.wait_for_task_result.return_value = mock_task_data

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [{"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0, "confidence": 0.9}]}],
                "text": "test",
                "metadata": {"language": "en"},
            }
            mock_get.return_value = mock_response

            raw_data = {"task_data": mock_task_data, "transcription": mock_response.json()}
            result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["task_id"] == "task123"

    def test_convert_result_format_missing_asset(self, transcriber, mock_api):
        """Test that transcription fails when the required output asset is missing"""
        task_data = {"id": "task123", "targets": [{"model": "vocals", "outputs": [{"link": "http://test.com/wrong"}]}]}

        raw_data = {"task_data": task_data, "transcription": {"metadata": {"language": "en"}}}

        result = transcriber._convert_result_format(raw_data)
        assert isinstance(result, TranscriptionData)
        assert result.segments == []
        assert result.text == ""
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["task_id"] == "task123"

    def test_transcribe_full_flow(self, transcriber, mock_api, tmp_path):
        # Clear the cache directory first
        cache_dir = transcriber.cache_dir
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                os.remove(os.path.join(cache_dir, file))

        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.write_text("test content")

        # Set up mock API responses
        mock_api.upload_file.return_value = "https://example.com/file.mp3"
        mock_api.create_task.return_value = "task123"
        mock_api.wait_for_task_result.return_value = {
            "id": "task123",
            "targets": [
                {
                    "model": "alignment",
                    "outputs": [{"link": "http://test.com/result"}]
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [{"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0, "confidence": 0.9}]}],
                "text": "test",
            }
            mock_get.return_value = mock_response

            result = transcriber.transcribe(str(test_file))

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "AudioShake"
        mock_api.upload_file.assert_called_once_with(str(test_file))

    def test_get_output_filename(self, transcriber):
        transcriber.config.output_prefix = "test"
        assert transcriber.get_output_filename(" (suffix)") == "test (suffix)"

    def test_convert_result_format_empty_segments(self, transcriber):
        """Test processing result with empty segment data"""
        task_data = {"id": "task123"}
        transcription_data = {
            "lines": [
                {"text": "", "words": []},  # Empty words
                {"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0}]},  # Complete
            ],
            "text": "test",
        }
        raw_data = {"task_data": task_data, "transcription": transcription_data}

        result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert len(result.segments) == 2
        assert result.segments[0].text == ""
        assert result.segments[1].text == "test"
        assert result.source == "AudioShake"

    def test_convert_result_format_malformed_response(self, transcriber):
        """Test handling of malformed API responses"""
        task_data = {"id": "task123"}
        raw_data = {"task_data": task_data, "transcription": {"metadata": {"language": "en"}}}

        result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert result.segments == []
        assert result.text == ""
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["task_id"] == "task123"

    def test_transcribe_with_cache(self, transcriber, mock_api, tmp_path):
        # Clear the cache directory first
        cache_dir = transcriber.cache_dir
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                os.remove(os.path.join(cache_dir, file))

        # Create test file
        test_file = tmp_path / "test.mp3"
        test_file.write_text("test content")

        # Set up mock API responses
        mock_api.upload_file.return_value = "https://example.com/file.mp3"
        mock_api.create_task.return_value = "task123"
        mock_api.wait_for_task_result.return_value = {
            "id": "task123",
            "targets": [
                {
                    "model": "alignment",
                    "outputs": [{"link": "http://test.com/result"}]
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [{"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0}]}],
                "text": "test",
            }
            mock_get.return_value = mock_response

            # First transcription
            result1 = transcriber.transcribe(str(test_file))
            assert isinstance(result1, TranscriptionData)

            # Second transcription should use cache
            result2 = transcriber.transcribe(str(test_file))
            assert isinstance(result2, TranscriptionData)

        # Verify API was only called once
        mock_api.upload_file.assert_called_once_with(str(test_file))

    @pytest.fixture(autouse=True)
    def clear_cache(self, transcriber):
        """Clear the cache directory before each test."""
        cache_dir = transcriber.cache_dir
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                os.remove(os.path.join(cache_dir, file))
        yield

    def test_perform_transcription_error(self, transcriber, mock_api):
        """Test _perform_transcription with API error"""
        mock_api.upload_file.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            transcriber._perform_transcription("test.mp3")

        transcriber.logger.error.assert_called()  # Verify error logging

    def test_get_transcription_result_error(self, transcriber, mock_api):
        """Test get_transcription_result with missing output asset"""
        mock_api.wait_for_task_result.return_value = {
            "id": "task123",
            "targets": [{"model": "vocals", "outputs": [{"link": "http://test.com/wrong"}]}],
        }

        with pytest.raises(TranscriptionError, match="Required output not found"):
            transcriber.get_transcription_result("task123")

    @patch("requests.get")
    def test_get_transcription_result_network_error(self, mock_get, transcriber, mock_api):
        """Test get_transcription_result with network error"""
        mock_api.wait_for_task_result.return_value = {
            "id": "task123",
            "targets": [
                {
                    "model": "alignment",
                    "outputs": [{"link": "http://test.com/result"}]
                }
            ],
        }
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            transcriber.get_transcription_result("task123")

    def test_convert_result_format_with_empty_data(self, transcriber):
        """Test _convert_result_format with minimal data"""
        raw_data = {
            "task_data": {"id": "task123"},
            "transcription": {},
        }

        result = transcriber._convert_result_format(raw_data)
        assert isinstance(result, TranscriptionData)
        assert result.text == ""
        assert result.segments == []
        assert result.words == []
        assert result.metadata["task_id"] == "task123"
        assert result.metadata["duration"] is None

    def test_perform_transcription_debug_logging(self, transcriber, mock_api, caplog):
        """Test debug logging in _perform_transcription"""
        mock_api.upload_file.return_value = "https://example.com/file.mp3"
        mock_api.create_task.return_value = "task123"
        mock_api.wait_for_task_result.return_value = {
            "id": "task123",
            "targets": [
                {
                    "model": "alignment",
                    "outputs": [{"link": "http://test.com/result"}]
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                json=lambda: {
                    "lines": [],
                    "text": "",
                    "metadata": {"language": "en"},
                }
            )
            transcriber.logger.debug = Mock()  # Mock debug logger
            transcriber._perform_transcription("test.mp3")

        # Verify debug logging calls
        transcriber.logger.debug.assert_any_call("Entering _perform_transcription() for test.mp3")
        transcriber.logger.debug.assert_any_call("Calling start_transcription()")
        transcriber.logger.debug.assert_any_call("Got task_id: task123")
