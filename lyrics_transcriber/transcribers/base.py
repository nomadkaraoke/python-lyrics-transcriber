from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Protocol, List
import logging


@dataclass
class Word:
    """Represents a single word with its timing and confidence information."""

    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0


@dataclass
class LyricsSegment:
    """Represents a segment/line of lyrics with timing information."""

    text: str
    words: List[Word]
    start_time: float
    end_time: float


@dataclass
class TranscriptionData:
    """Structured container for transcription results."""

    segments: List[LyricsSegment]
    text: str
    source: str  # e.g., "whisper", "audioshake"
    metadata: Optional[Dict[str, Any]] = None


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def debug(self, msg: str) -> None: ...
    def info(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


class TranscriptionError(Exception):
    """Base exception for transcription errors."""

    pass


class BaseTranscriber(ABC):
    """Base class for all transcription services."""

    def __init__(self, logger: Optional[LoggerProtocol] = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def transcribe(self, audio_filepath: str) -> TranscriptionData:
        """
        Transcribe an audio file and return the results in a standardized format.

        Args:
            audio_filepath: Path to the audio file to transcribe

        Returns:
            TranscriptionData containing segments, text, and metadata

        Raises:
            TranscriptionError: If transcription fails
            FileNotFoundError: If audio file doesn't exist
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this transcription service."""
        pass

    def _validate_audio_file(self, audio_filepath: str) -> None:
        """Validate that the audio file exists and is accessible."""
        import os

        if not os.path.exists(audio_filepath):
            self.logger.error(f"Audio file not found: {audio_filepath}")
            raise FileNotFoundError(f"Audio file not found: {audio_filepath}")
