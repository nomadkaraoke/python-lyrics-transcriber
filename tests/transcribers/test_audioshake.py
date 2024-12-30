import pytest
import requests
from unittest.mock import Mock, patch, mock_open
from lyrics_transcriber.transcribers.audioshake import (
    AudioShakeConfig,
    AudioShakeAPI,
    AudioShakeTranscriber,
)
from lyrics_transcriber.transcribers.base_transcriber import (
    TranscriptionData,
    LyricsSegment,
    Word,
    TranscriptionError,
)
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

        # Test create_job
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            api.create_job("asset123")

        # Test wait_for_job_result
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            api.wait_for_job_result("job123")

    def test_get_headers(self, api):
        headers = api._get_headers()
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"

    @patch("requests.post")
    def test_upload_file(self, mock_post, api):
        mock_response = Mock()
        mock_response.json.return_value = {"id": "asset123"}
        mock_post.return_value = mock_response

        with patch("builtins.open", mock_open(read_data="test data")):
            asset_id = api.upload_file("test.mp3")

        assert asset_id == "asset123"
        mock_post.assert_called_once()
        api.logger.info.assert_called_with("Uploading test.mp3 to AudioShake")

    @patch("requests.post")
    def test_create_job(self, mock_post, api):
        mock_response = Mock()
        mock_response.json.return_value = {"job": {"id": "job123"}}
        mock_post.return_value = mock_response

        job_id = api.create_job("asset123")

        assert job_id == "job123"
        mock_post.assert_called_once()
        api.logger.info.assert_called_with("Creating job for asset asset123")

    @patch("requests.get")
    def test_wait_for_job_result_success(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"job": {"status": "completed", "data": "test"}}
        mock_get.return_value = mock_response

        result = api.wait_for_job_result("job123")

        assert result == {"status": "completed", "data": "test"}
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_wait_for_job_result_failure(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"job": {"status": "failed", "error": "test error"}}
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Job failed: test error"):
            api.wait_for_job_result("job123")

    @patch("requests.get")
    @patch("time.sleep")
    def test_wait_for_job_result_polling(self, mock_sleep, mock_get, api):
        """Test polling behavior with in-progress status before completion"""
        mock_responses = [
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "completed", "data": "test"}}),
        ]
        mock_get.side_effect = mock_responses

        result = api.wait_for_job_result("job123")

        assert result == {"status": "completed", "data": "test"}
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(5)

    @patch("requests.get")
    def test_wait_for_job_result_with_retries(self, mock_get, api):
        """Test job result polling with network errors"""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            api.wait_for_job_result("job123")

        assert mock_get.call_count == 1  # Verify we don't retry on error

    @patch("requests.get")
    @patch("time.time")
    def test_wait_for_job_result_timeout(self, mock_time, mock_get, api):
        """Test that job polling times out after configured duration"""
        mock_time.side_effect = [0, api.config.timeout_minutes * 60 + 1]  # Simulate timeout
        mock_get.return_value = Mock(json=lambda: {"job": {"status": "in_progress"}})

        with pytest.raises(TranscriptionError, match=f"Transcription timed out after {api.config.timeout_minutes} minutes"):
            api.wait_for_job_result("job123")

    @patch("requests.get")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_job_result_logs_status(self, mock_sleep, mock_time, mock_get, api):
        """Test that job polling logs status periodically"""
        mock_time.side_effect = [0, 30, 61, 90]  # Simulate time passing
        mock_get.side_effect = [
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "completed", "data": "test"}}),
        ]

        result = api.wait_for_job_result("job123")

        # Verify periodic status logging
        api.logger.info.assert_any_call("Still waiting for transcription... Elapsed time: 1 minutes")


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
        mock_api.upload_file.return_value = "asset123"
        mock_api.create_job.return_value = "job123"

        job_id = transcriber.start_transcription("test.mp3")

        assert job_id == "job123"
        mock_api.upload_file.assert_called_once_with("test.mp3")
        mock_api.create_job.assert_called_once_with("asset123")

    def test_get_transcription_result(self, transcriber, mock_api):
        mock_job_data = {"id": "job123", "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}]}
        mock_api.wait_for_job_result.return_value = mock_job_data

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [{"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0, "confidence": 0.9}]}],
                "text": "test",
            }
            mock_get.return_value = mock_response

            raw_data = {
                "job_data": mock_job_data,
                "transcription": mock_response.json()
            }
            result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"

    def test_convert_result_format_missing_asset(self, transcriber, mock_api):
        """Test that transcription fails when the required output asset is missing"""
        # Mock a job response without the required 'alignment.json' asset
        job_data = {
            "id": "job123",
            "outputAssets": [
                {"name": "wrong.json", "link": "http://test.com/wrong"}
            ]
        }
        
        # Setup mock API response
        mock_api.wait_for_job_result.return_value = job_data
        
        # First test: get_transcription_result should raise the error
        with pytest.raises(TranscriptionError, match="Required output not found in job results"):
            transcriber.get_transcription_result("job123")

        # Second test: even if we bypass that and call _convert_result_format directly,
        # it should still handle the missing data gracefully
        raw_data = {
            "job_data": job_data,
            "transcription": {}
        }
        
        # Should return empty TranscriptionData rather than raise an error
        result = transcriber._convert_result_format(raw_data)
        assert isinstance(result, TranscriptionData)
        assert result.segments == []
        assert result.text == ""
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"

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
        mock_api.upload_file.return_value = "asset123"
        mock_api.create_job.return_value = "job123"
        mock_api.wait_for_job_result.return_value = {
            "id": "job123",
            "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}],
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
        job_data = {"id": "job123", "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}]}
        transcription_data = {
            "lines": [
                {"text": "", "words": []},  # Empty words
                {"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0}]},  # Complete
            ],
            "text": "test",
        }
        raw_data = {
            "job_data": job_data,
            "transcription": transcription_data
        }

        result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert len(result.segments) == 2
        assert result.segments[0].text == ""
        assert result.segments[1].text == "test"
        assert result.source == "AudioShake"

    def test_convert_result_format_malformed_response(self, transcriber):
        """Test handling of malformed API responses"""
        job_data = {"id": "job123", "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}]}
        raw_data = {
            "job_data": job_data,
            "transcription": {}  # Empty transcription data
        }

        result = transcriber._convert_result_format(raw_data)

        assert isinstance(result, TranscriptionData)
        assert result.segments == []
        assert result.text == ""
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"

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
        mock_api.upload_file.return_value = "asset123"
        mock_api.create_job.return_value = "job123"
        mock_api.wait_for_job_result.return_value = {
            "id": "job123",
            "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}],
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
