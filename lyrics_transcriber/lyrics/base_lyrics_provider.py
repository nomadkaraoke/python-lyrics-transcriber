from dataclasses import dataclass
import logging
from typing import Optional


@dataclass
class LyricsProviderConfig:
    """Configuration for lyrics providers."""

    genius_api_token: Optional[str] = None
    spotify_cookie: Optional[str] = None


class BaseLyricsProvider:
    """Base class for lyrics providers."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics for a given artist and title."""
        raise NotImplementedError("Subclasses must implement fetch_lyrics")
