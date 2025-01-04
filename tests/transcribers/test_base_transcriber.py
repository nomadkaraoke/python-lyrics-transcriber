import pytest
import logging
from unittest.mock import Mock, call
import shutil
from lyrics_transcriber.types import LyricsSegment, Word, TranscriptionData
from lyrics_transcriber.transcribers.base_transcriber import BaseTranscriber
import tempfile
import json
import os


class MockTranscriber(BaseTranscriber):
    """Mock implementation of BaseTranscriber for testing."""

    def _perform_transcription(self, audio_filepath: str) -> dict:
        # Now returns raw dictionary instead of TranscriptionData
        return {
            "segments": [
                {"text": "test", "words": [{"text": "test", "start_time": 0.0, "end_time": 1.0}], "start_time": 0.0, "end_time": 1.0}
            ],
            "text": "test",
            "source": self.get_name(),
            "metadata": {"language": "en"},
        }

    def _convert_result_format(self, raw_result: dict) -> TranscriptionData:
        """Convert raw API result to TranscriptionData format."""
        segments = []
        words = []  # Collect all words
        for seg in raw_result["segments"]:
            seg_words = [Word(**w) for w in seg["words"]]
            words.extend(seg_words)  # Add segment words to main words list
            segments.append(LyricsSegment(text=seg["text"], words=seg_words, start_time=seg["start_time"], end_time=seg["end_time"]))

        return TranscriptionData(
            segments=segments,
            words=words,  # Add words parameter
            text=raw_result["text"],
            source=raw_result["source"],
            metadata=raw_result.get("metadata", {}),
        )

    def get_name(self) -> str:
        return "MockTranscriber"


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


class TestTranscriptionData:
    def test_data_creation(self):
        test_word = Word(text="test", start_time=0.0, end_time=1.0)
        result = TranscriptionData(
            segments=[LyricsSegment(text="test", words=[test_word], start_time=0.0, end_time=1.0)],
            words=[test_word],  # Add words parameter
            text="test",
            source="test",
            metadata={"language": "en"},
        )

        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert len(result.words) == 1  # Add words assertion
        assert result.source == "test"
        assert result.metadata == {"language": "en"}

    def test_data_optional_fields(self):
        result = TranscriptionData(
            segments=[],
            words=[],  # Add empty words list
            text="",
            source="test",
            metadata={},
        )

        assert result.text == ""
        assert len(result.segments) == 0
        assert len(result.words) == 0  # Add words assertion
        assert result.source == "test"
        assert result.metadata == {}


class TestBaseTranscriber:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clean up the test cache directory before and after each test."""
        # Use a test-specific cache directory
        test_cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-test-cache")

        # Clean up before test
        if os.path.exists(test_cache_dir):
            print(f"Cleaning up existing cache dir: {test_cache_dir}")  # Debug print
            shutil.rmtree(test_cache_dir)

        # Set environment variable
        os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"] = test_cache_dir
        print(f"Set cache dir to: {test_cache_dir}")  # Debug print

        yield

        # Clean up after test
        if os.path.exists(test_cache_dir):
            print(f"Cleaning up cache dir after test: {test_cache_dir}")  # Debug print
            shutil.rmtree(test_cache_dir)

        # Clean up environment variable
        del os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]

    @pytest.fixture
    def transcriber(self, mock_logger):
        """Create a transcriber with explicit cache directory."""
        cache_dir = os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]
        transcriber = MockTranscriber(logger=mock_logger, cache_dir=cache_dir)
        print(f"Created transcriber with cache dir: {transcriber.cache_dir}")  # Debug print
        return transcriber

    def test_init_with_logger(self, mock_logger):
        """Test initialization with a logger."""
        cache_dir = os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]
        transcriber = MockTranscriber(cache_dir=cache_dir, logger=mock_logger)
        assert transcriber.logger == mock_logger
        assert str(transcriber.cache_dir) == cache_dir

    def test_init_without_logger(self):
        """Test initialization without a logger."""
        cache_dir = os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]
        transcriber = MockTranscriber(cache_dir=cache_dir)
        assert isinstance(transcriber.logger, logging.Logger)
        assert str(transcriber.cache_dir) == cache_dir

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

        # Get expected cache path before first transcription
        file_hash = transcriber._get_file_hash(str(audio_file))
        raw_cache_path = transcriber._get_cache_path(file_hash, "raw")

        # Verify cache doesn't exist initially
        assert not os.path.exists(raw_cache_path), f"Cache file already exists at {raw_cache_path}"

        # First transcription should perform the actual transcription
        result1 = transcriber.transcribe(str(audio_file))
        assert result1.text == "test"

        # Verify cache was created
        assert os.path.exists(raw_cache_path), f"Cache file was not created at {raw_cache_path}"

        # Second transcription should use cache
        result2 = transcriber.transcribe(str(audio_file))
        assert result2.text == "test"

        # Verify logger messages
        transcriber.logger.info.assert_has_calls(
            [call(f"No cache found, transcribing {audio_file}"), call(f"Using cached raw data for {audio_file}")]
        )

    def test_cache_file_structure(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("test content")

        # Perform transcription
        result = transcriber.transcribe(str(audio_file))

        # Verify cache file exists and has correct structure
        file_hash = transcriber._get_file_hash(str(audio_file))
        raw_cache_path = transcriber._get_cache_path(file_hash, "raw")
        assert os.path.exists(raw_cache_path)

        with open(raw_cache_path, "r") as f:
            cached_data = json.load(f)
            assert "text" in cached_data
            assert "segments" in cached_data
            assert "source" in cached_data

    def test_invalid_cache_handling(self, transcriber, tmp_path):
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("test content")

        # Create invalid cache file
        file_hash = transcriber._get_file_hash(str(audio_file))
        raw_cache_path = transcriber._get_cache_path(file_hash, "raw")
        os.makedirs(os.path.dirname(raw_cache_path), exist_ok=True)
        with open(raw_cache_path, "w") as f:
            f.write("invalid json")

        # Should perform transcription despite invalid cache
        result = transcriber.transcribe(str(audio_file))
        assert result.text == "test"
        transcriber.logger.info.assert_any_call(f"No cache found, transcribing {audio_file}")

    def test_transcribe_error_handling(self, transcriber, tmp_path):
        """Test that exceptions during transcription are properly logged and re-raised."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        # Mock _perform_transcription to raise an exception
        def raise_error(*args):
            raise ValueError("Test error")

        transcriber._perform_transcription = raise_error

        # Verify that the exception is logged and re-raised
        with pytest.raises(ValueError, match="Test error"):
            transcriber.transcribe(str(audio_file))

        transcriber.logger.error.assert_called_once_with("Error during transcription: Test error")
