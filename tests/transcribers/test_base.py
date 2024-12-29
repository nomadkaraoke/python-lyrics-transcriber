import pytest
import logging
from unittest.mock import Mock
from dataclasses import asdict
from lyrics_transcriber.transcribers.base import (
    BaseTranscriber,
    TranscriptionData,
    LyricsSegment,
    Word,
    TranscriptionError,
    LoggerProtocol,
)


class MockTranscriber(BaseTranscriber):
    """Mock implementation of BaseTranscriber for testing."""

    def transcribe(self, audio_filepath: str) -> TranscriptionData:
        self._validate_audio_file(audio_filepath)
        return TranscriptionData(
            segments=[
                LyricsSegment(
                    text="test",
                    words=[
                        Word(text="test", start_time=0.0, end_time=1.0)
                    ],
                    start_time=0.0,
                    end_time=1.0
                )
            ],
            text="test",
            source=self.get_name(),
            metadata={"language": "en"}
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
            segments=[
                LyricsSegment(
                    text="test",
                    words=[
                        Word(text="test", start_time=0.0, end_time=1.0)
                    ],
                    start_time=0.0,
                    end_time=1.0
                )
            ],
            text="test",
            source="test",
            metadata={"language": "en"}
        )

        assert result.text == "test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "test"
        assert result.source == "test"
        assert result.metadata == {"language": "en"}

    def test_data_optional_fields(self):
        result = TranscriptionData(
            segments=[],
            text="",
            source="test",
            metadata={}
        )

        assert result.text == ""
        assert len(result.segments) == 0
        assert result.source == "test"
        assert result.metadata == {}


class TestBaseTranscriber:
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
