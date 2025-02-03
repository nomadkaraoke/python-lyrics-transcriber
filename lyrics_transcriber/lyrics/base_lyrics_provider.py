from dataclasses import dataclass
import logging
from typing import Optional, Dict, Any
import json
import hashlib
from pathlib import Path
import os
from abc import ABC, abstractmethod
from lyrics_transcriber.types import LyricsData
from karaoke_lyrics_processor import KaraokeLyricsProcessor


@dataclass
class LyricsProviderConfig:
    """Configuration for lyrics providers."""

    genius_api_token: Optional[str] = None
    spotify_cookie: Optional[str] = None
    lyrics_file: Optional[str] = None
    cache_dir: Optional[str] = None
    audio_filepath: Optional[str] = None
    max_line_length: int = 36  # New config parameter for KaraokeLyricsProcessor


class BaseLyricsProvider(ABC):
    """Base class for lyrics providers."""

    def __init__(self, config: LyricsProviderConfig, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.cache_dir = Path(config.cache_dir) if config.cache_dir else None
        self.audio_filepath = config.audio_filepath
        self.max_line_length = config.max_line_length
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Initialized {self.__class__.__name__} with cache dir: {self.cache_dir}")

    def fetch_lyrics(self, artist: str, title: str) -> Optional[LyricsData]:
        """Fetch lyrics for a given artist and title, using cache if available."""
        if not self.cache_dir:
            return self._fetch_and_convert_result(artist, title)

        # Use artist and title for cache key instead of audio file hash
        cache_key = self._get_artist_title_hash(artist, title)
        raw_cache_path = self._get_cache_path(cache_key, "raw")

        # Try to load from cache first
        raw_data = self._load_from_cache(raw_cache_path)
        if raw_data is not None:
            self.logger.info(f"Using cached lyrics for {artist} - {title}")
            return self._save_and_convert_result(cache_key, raw_data)

        # If not in cache, fetch from source
        raw_result = self._fetch_data_from_source(artist, title)
        if raw_result:
            # Save raw API response
            self._save_to_cache(raw_cache_path, raw_result)
            return self._save_and_convert_result(cache_key, raw_result)

        return None

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

    def _get_artist_title_hash(self, artist: str, title: str) -> str:
        """Calculate MD5 hash of the artist and title."""
        combined = f"{artist.lower()}_{title.lower()}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str, suffix: str) -> str:
        """Get the cache file path for a given cache key and suffix."""
        return os.path.join(self.cache_dir, f"{self.get_name().lower()}_{cache_key}_{suffix}.json")

    def _save_to_cache(self, cache_path: str, data: Dict[str, Any]) -> None:
        """Save data to cache."""
        self.logger.debug(f"Saving lyrics to cache: {cache_path}")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.debug("Cache save completed")

    def _load_from_cache(self, cache_path: str) -> Optional[Dict[str, Any]]:
        """Load data from cache if it exists."""
        self.logger.debug(f"Attempting to load from cache: {cache_path}")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.logger.debug("Lyrics loaded from cache")
                return data
        except FileNotFoundError:
            self.logger.debug("Cache file not found")
            return None
        except json.JSONDecodeError:
            self.logger.warning(f"Cache file {cache_path} is corrupted")
            return None

    def _process_lyrics(self, lyrics_data: LyricsData) -> LyricsData:
        """Process lyrics using KaraokeLyricsProcessor."""
        processor = KaraokeLyricsProcessor(
            log_level=self.logger.getEffectiveLevel(),
            log_formatter=self.logger.handlers[0].formatter if self.logger.handlers else None,
            input_lyrics_text=lyrics_data.lyrics,
            max_line_length=self.max_line_length,
        )
        processed_text = processor.process()

        # Create new LyricsData with processed text
        return LyricsData(source=lyrics_data.source, lyrics=processed_text, segments=lyrics_data.segments, metadata=lyrics_data.metadata)

    def _save_and_convert_result(self, cache_key: str, raw_data: Dict[str, Any]) -> LyricsData:
        """Convert raw result to standardized format, process lyrics, save to cache, and return."""
        converted_cache_path = self._get_cache_path(cache_key, "converted")
        converted_result = self._convert_result_format(raw_data)

        # Process the lyrics
        processed_result = self._process_lyrics(converted_result)

        # Convert to dictionary before saving to cache
        self._save_to_cache(converted_cache_path, processed_result.to_dict())
        return processed_result

    def _fetch_and_convert_result(self, artist: str, title: str) -> Optional[LyricsData]:
        """Fetch and convert result when caching is disabled."""
        raw_result = self._fetch_data_from_source(artist, title)
        if raw_result:
            return self._convert_result_format(raw_result)
        return None

    @abstractmethod
    def _fetch_data_from_source(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Fetch raw data from the source (implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _fetch_data_from_source")  # pragma: no cover

    @abstractmethod
    def _convert_result_format(self, raw_data: Dict[str, Any]) -> LyricsData:
        """Convert raw API response to standardized format (implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _convert_result_format")  # pragma: no cover

    def get_name(self) -> str:
        """Return the name of this lyrics provider."""
        return self.__class__.__name__.replace("Provider", "")
