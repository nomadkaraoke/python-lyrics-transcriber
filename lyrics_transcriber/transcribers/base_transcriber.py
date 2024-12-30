from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Protocol, List, Union
from pathlib import Path
import logging
import os
import json
import hashlib


@dataclass
class Word:
    """Represents a single word with its timing and confidence information."""

    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert Word to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class LyricsSegment:
    """Represents a segment/line of lyrics with timing information."""

    text: str
    words: List[Word]
    start_time: float
    end_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert LyricsSegment to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "words": [word.to_dict() for word in self.words],
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class TranscriptionData:
    """Structured container for transcription results."""

    segments: List[LyricsSegment]
    text: str
    source: str  # e.g., "whisper", "audioshake"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert TranscriptionData to dictionary for JSON serialization."""
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata,
        }


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

    def __init__(self, cache_dir: Union[str, Path], logger: Optional[LoggerProtocol] = None):
        """
        Initialize transcriber with cache directory and logger.

        Args:
            cache_dir: Directory to store cache files. Must be provided.
            logger: Logger instance to use. If None, creates a new logger.
        """
        self.cache_dir = Path(cache_dir)
        self.logger = logger or logging.getLogger(__name__)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Initialized {self.__class__.__name__} with cache dir: {self.cache_dir}")

    def _get_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file."""
        self.logger.debug(f"Calculating hash for file: {filepath}")
        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        hash_result = md5_hash.hexdigest()
        self.logger.debug(f"File hash: {hash_result}")
        return hash_result

    def _get_cache_path(self, file_hash: str) -> str:
        """Get the cache file path for a given file hash."""
        cache_path = os.path.join(self.cache_dir, f"{self.get_name().lower()}_{file_hash}.json")
        self.logger.debug(f"Cache path: {cache_path}")
        return cache_path

    def _save_to_cache(self, cache_path: str, data: TranscriptionData) -> None:
        """Save transcription data to cache."""
        self.logger.debug(f"Saving transcription to cache: {cache_path}")
        with open(cache_path, "w") as f:
            json.dump(data.to_dict(), f)
        self.logger.debug("Cache save completed")

    def _load_from_cache(self, cache_path: str) -> Optional[TranscriptionData]:
        """Load transcription data from cache if it exists."""
        self.logger.debug(f"Attempting to load from cache: {cache_path}")
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                self.logger.debug("Cache file loaded, reconstructing TranscriptionData")
                # Reconstruct Word objects
                segments = []
                for seg in data["segments"]:
                    words = [Word(**w) for w in seg["words"]]
                    segments.append(LyricsSegment(text=seg["text"], words=words, start_time=seg["start_time"], end_time=seg["end_time"]))
                result = TranscriptionData(segments=segments, text=data["text"], source=data["source"], metadata=data.get("metadata"))
                self.logger.debug("Cache data successfully reconstructed")
                return result
        except FileNotFoundError:
            self.logger.debug("Cache file not found")
            return None
        except json.JSONDecodeError:
            self.logger.warning(f"Cache file {cache_path} is corrupted")
            return None

    def transcribe(self, audio_filepath: str) -> TranscriptionData:
        """
        Transcribe an audio file, using cache if available.

        Args:
            audio_filepath: Path to the audio file to transcribe

        Returns:
            TranscriptionData containing segments, text, and metadata
        """
        self.logger.debug(f"Starting transcription for {audio_filepath}")

        try:
            self._validate_audio_file(audio_filepath)
            self.logger.debug("Audio file validation passed")

            # Check cache first
            file_hash = self._get_file_hash(audio_filepath)
            cache_path = self._get_cache_path(file_hash)

            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                self.logger.info(f"Using cached transcription for {audio_filepath}")
                return cached_data

            # If not in cache, perform transcription
            self.logger.info(f"No cache found, transcribing {audio_filepath}")
            result = self._perform_transcription(audio_filepath)
            self.logger.debug("Transcription completed")

            # Save to cache
            self._save_to_cache(cache_path, result)
            return result

        except Exception as e:
            self.logger.error(f"Error during transcription: {str(e)}")
            raise

    @abstractmethod
    def _perform_transcription(self, audio_filepath: str) -> TranscriptionData:
        """
        Actually perform the transcription (implemented by subclasses).

        Args:
            audio_filepath: Path to the audio file to transcribe

        Returns:
            TranscriptionData containing segments, text, and metadata
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this transcription service."""
        pass  # pragma: no cover

    def _validate_audio_file(self, audio_filepath: str) -> None:
        """Validate that the audio file exists and is accessible."""
        self.logger.debug(f"Validating audio file: {audio_filepath}")
        if not os.path.exists(audio_filepath):
            self.logger.error(f"Audio file not found: {audio_filepath}")
            raise FileNotFoundError(f"Audio file not found: {audio_filepath}")
        self.logger.debug("Audio file validation successful")