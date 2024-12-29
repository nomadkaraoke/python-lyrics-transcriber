import pytest
import logging
from unittest.mock import Mock, call
from dataclasses import asdict
import shutil
from lyrics_transcriber.transcribers.base import (
    BaseTranscriber,
    TranscriptionData,
    LyricsSegment,
    Word,
    TranscriptionError,
    LoggerProtocol,
)
import tempfile
import json
import os


class MockTranscriber(BaseTranscriber):
    """Mock implementation of BaseTranscriber for testing."""

    def _perform_transcription(self, audio_filepath: str) -> TranscriptionData:
        return TranscriptionData(
            segments=[LyricsSegment(text="test", words=[Word(text="test", start_time=0.0, end_time=1.0)], start_time=0.0, end_time=1.0)],
            text="test",
            source=self.get_name(),
            metadata={"language": "en"},
        )

    def get_name(self) -> str:
        return "MockTranscriber"


@pytest.fixture
def mock_logger():
    return Mock(spec=LoggerProtocol)


@pytest.fixture
def transcriber(mock_logger):
    return MockTranscriber(logger=mock_logger)


class TestTranscriptionData:
    def test_data_creation(self):
        result = TranscriptionData(
            segments=[LyricsSegment(text="test", words=[Word(text="test", start_time=0.0, end_time=1.0)], start_time=0.0, end_time=1.0)],
            text="test",
            source="test",
            metadata={"language": "en"},
        )

        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "test"
        assert result.metadata == {"language": "en"}

    def test_data_optional_fields(self):
        result = TranscriptionData(segments=[], text="", source="test", metadata={})

        assert result.text == ""
        assert len(result.segments) == 0
        assert result.source == "test"
        assert result.metadata == {}


class TestBaseTranscriber:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clean up the cache directory before and after each test."""
        cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-cache")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        yield
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

    def test_init_with_logger(self, mock_logger):
        transcriber = MockTranscriber(logger=mock_logger)
        assert transcriber.logger == mock_logger

    def test_init_without_logger(self):
        transcriber = MockTranscriber()
        assert isinstance(transcriber.logger, logging.Logger)

    def test_validate_audio_file_exists(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        transcriber._validate_audio_file(str(audio_file))
        # Should not raise any exception

    def test_validate_audio_file_not_exists(self, transcriber):
        with pytest.raises(FileNotFoundError):
            transcriber._validate_audio_file("nonexistent.mp3")
        transcriber.logger.error.assert_called_once()

    def test_transcribe_implementation(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        result = transcriber.transcribe(str(audio_file))

        assert isinstance(result, TranscriptionData)
        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "MockTranscriber"
        assert result.metadata["language"] == "en"

    def test_get_name_implementation(self, transcriber):
        assert transcriber.get_name() == "MockTranscriber"

    def test_caching_mechanism(self, transcriber, tmp_path):
        # Create a test audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("test content")

        # First transcription should perform the actual transcription
        result1 = transcriber.transcribe(str(audio_file))
        assert result1.text == "test"

        # Second transcription should use cache
        result2 = transcriber.transcribe(str(audio_file))
        assert result2.text == "test"

        # Verify logger messages
        transcriber.logger.info.assert_has_calls(
            [call(f"No cache found, transcribing {audio_file}"), call(f"Using cached transcription for {audio_file}")]
        )

    def test_cache_file_structure(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("test content")

        # Perform transcription
        result = transcriber.transcribe(str(audio_file))

        # Verify cache file exists and has correct structure
        file_hash = transcriber._get_file_hash(str(audio_file))
        cache_path = transcriber._get_cache_path(file_hash)
        assert os.path.exists(cache_path)

        with open(cache_path, "r") as f:
            cached_data = json.load(f)
            assert "text" in cached_data
            assert "segments" in cached_data
            assert "source" in cached_data

    def test_invalid_cache_handling(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("test content")

        # Create invalid cache file
        file_hash = transcriber._get_file_hash(str(audio_file))
        cache_path = transcriber._get_cache_path(file_hash)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write("invalid json")

        # Should perform transcription despite invalid cache
        result = transcriber.transcribe(str(audio_file))
        assert result.text == "test"
        transcriber.logger.info.assert_any_call(f"No cache found, transcribing {audio_file}")
