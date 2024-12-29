import pytest
import requests
from unittest.mock import Mock, patch, mock_open
from lyrics_transcriber.transcribers.audioshake import (
    AudioShakeConfig,
    AudioShakeAPI,
    AudioShakeTranscriber,
)
from lyrics_transcriber.transcribers.base import (
    TranscriptionData,
    LyricsSegment,
    Word,
    TranscriptionError,
)


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

    def test_init_without_token(self, mock_logger):
        with pytest.raises(ValueError, match="AudioShake API token must be provided"):
            AudioShakeAPI(AudioShakeConfig(), mock_logger)

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
    def test_get_job_result_success(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"job": {"status": "completed", "data": "test"}}
        mock_get.return_value = mock_response

        result = api.get_job_result("job123")

        assert result == {"status": "completed", "data": "test"}
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_job_result_failure(self, mock_get, api):
        mock_response = Mock()
        mock_response.json.return_value = {"job": {"status": "failed", "error": "test error"}}
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Job failed: test error"):
            api.get_job_result("job123")

    @patch("requests.get")
    @patch("time.sleep")
    def test_get_job_result_polling(self, mock_sleep, mock_get, api):
        """Test polling behavior with in-progress status before completion"""
        mock_responses = [
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "in_progress"}}),
            Mock(json=lambda: {"job": {"status": "completed", "data": "test"}}),
        ]
        mock_get.side_effect = mock_responses

        result = api.get_job_result("job123")

        assert result == {"status": "completed", "data": "test"}
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(5)

    @patch("requests.get")
    def test_get_job_result_with_retries(self, mock_get, api):
        """Test job result polling with network errors"""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            api.get_job_result("job123")

        assert mock_get.call_count == 1  # Verify we don't retry on error


class TestAudioShakeTranscriber:
    @pytest.fixture
    def mock_api(self):
        return Mock()

    @pytest.fixture
    def transcriber(self, mock_logger, mock_api):
        return AudioShakeTranscriber(api_token="test_token", logger=mock_logger, api_client=mock_api)

    def test_init_with_token(self, transcriber):
        assert transcriber.config.api_token == "test_token"
        assert transcriber.api is not None

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
        mock_api.get_job_result.return_value = mock_job_data

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [{"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0, "confidence": 0.9}]}],
                "text": "test",
            }
            mock_get.return_value = mock_response

            result = transcriber._process_result(mock_job_data)

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"

    def test_process_result_missing_asset(self, transcriber):
        job_data = {"id": "job123", "outputAssets": [{"name": "wrong.json"}]}

        with pytest.raises(Exception, match="Required output not found in job results"):
            transcriber._process_result(job_data)

    def test_transcribe_full_flow(self, transcriber, mock_api):
        mock_api.upload_file.return_value = "asset123"
        mock_api.create_job.return_value = "job123"
        mock_api.get_job_result.return_value = {
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

            result = transcriber.transcribe("test.mp3")

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"

    def test_get_output_filename(self, transcriber):
        transcriber.config.output_prefix = "test"
        assert transcriber.get_output_filename(" (suffix)") == "test (suffix)"

    def test_process_result_empty_segments(self, transcriber):
        """Test processing result with empty segment data"""
        job_data = {"id": "job123", "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}]}

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "lines": [
                    {"text": "", "words": []},  # Empty words
                    {"text": "test", "words": [{"text": "test", "start": 0.0, "end": 1.0}]},  # Complete
                ],
                "text": "test",
            }
            mock_get.return_value = mock_response

            result = transcriber._process_result(job_data)

        assert isinstance(result, TranscriptionData)
        assert len(result.segments) == 2
        assert result.segments[0].text == ""
        assert result.segments[1].text == "test"
        assert result.source == "AudioShake"

    def test_process_result_malformed_response(self, transcriber):
        """Test handling of malformed API responses"""
        job_data = {"id": "job123", "outputAssets": [{"name": "alignment.json", "link": "http://test.com/result"}]}

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            # Missing both lines and text fields
            mock_response.json.return_value = {}
            mock_get.return_value = mock_response

            result = transcriber._process_result(job_data)

        assert isinstance(result, TranscriptionData)
        assert result.segments == []
        assert result.text == ""
        assert result.source == "AudioShake"
        assert result.metadata["language"] == "en"
        assert result.metadata["job_id"] == "job123"
