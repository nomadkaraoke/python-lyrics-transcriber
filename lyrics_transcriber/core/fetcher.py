from dataclasses import dataclass
import logging
import os
from typing import Optional, Dict, Any, Protocol
import lyricsgenius
import requests


@dataclass
class LyricsFetcherConfig:
    """Configuration for lyrics fetching services."""

    genius_api_token: Optional[str] = None
    spotify_cookie: Optional[str] = None


class LyricsProvider(Protocol):
    """Interface for lyrics providers."""

    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics for a given artist and title."""
        ...  # pragma: no cover


class GeniusProvider:
    """Handles fetching lyrics from Genius."""

    def __init__(self, api_token: Optional[str], logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.api_token = api_token
        self.client = None
        if self.api_token:
            self.client = lyricsgenius.Genius(self.api_token)
            self.client.verbose = False
            self.client.remove_section_headers = True

    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics from Genius."""
        if not self.client:
            self.logger.warning("No Genius API token provided")
            return None

        self.logger.info(f"Searching Genius for {artist} - {title}")
        try:
            song = self.client.search_song(title, artist)
            if song:
                self.logger.info("Found lyrics on Genius")
                return song.lyrics
        except Exception as e:
            self.logger.error(f"Error fetching from Genius: {str(e)}")
        return None


class SpotifyProvider:
    """Handles fetching lyrics from Spotify."""

    def __init__(self, cookie: Optional[str], logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.cookie = cookie

    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics from Spotify."""
        if not self.cookie:
            self.logger.warning("No Spotify cookie provided")
            return None

        try:
            track_id = self._search_track(artist, title)
            if not track_id:
                return None
            return self._fetch_track_lyrics(track_id)
        except Exception as e:
            self.logger.error(f"Error fetching from Spotify: {str(e)}")
            return None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Spotify API requests."""
        return {
            "Cookie": f"sp_dc={self.cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "App-Platform": "WebPlayer",
        }

    def _search_track(self, artist: str, title: str) -> Optional[str]:
        """Search for a track on Spotify."""
        search_url = "https://api.spotify.com/v1/search"
        params = {"q": f"artist:{artist} track:{title}", "type": "track", "limit": 1}

        self.logger.debug("Making Spotify search request")
        response = requests.get(search_url, headers=self._get_headers(), params=params)
        response.raise_for_status()

        search_data = response.json()
        items = search_data.get("tracks", {}).get("items", [])
        return items[0]["id"] if items else None

    def _fetch_track_lyrics(self, track_id: str) -> Optional[str]:
        """Fetch lyrics for a specific track."""
        lyrics_url = f"https://api.spotify.com/v1/tracks/{track_id}/lyrics"

        self.logger.debug("Making Spotify lyrics request")
        response = requests.get(lyrics_url, headers=self._get_headers())
        response.raise_for_status()

        lyrics_data = response.json()
        lyrics_lines = lyrics_data.get("lyrics", {}).get("lines", [])
        if not lyrics_lines:
            return None

        lyrics = "\n".join(line["words"] for line in lyrics_lines if line.get("words"))
        self.logger.info("Successfully fetched lyrics from Spotify")
        return lyrics


class LyricsFetcher:
    """Orchestrates fetching lyrics from various providers."""

    def __init__(
        self,
        config: Optional[LyricsFetcherConfig] = None,
        genius_provider: Optional[LyricsProvider] = None,
        spotify_provider: Optional[LyricsProvider] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or LyricsFetcherConfig()

        # Initialize providers (with dependency injection support)
        self.genius = genius_provider or GeniusProvider(self.config.genius_api_token or os.getenv("GENIUS_API_TOKEN"), self.logger)
        self.spotify = spotify_provider or SpotifyProvider(self.config.spotify_cookie or os.getenv("SPOTIFY_COOKIE"), self.logger)

    def fetch_lyrics(self, artist: str, title: str) -> Dict[str, Any]:
        """Fetch lyrics from all available sources."""
        self.logger.info(f"Fetching lyrics for {artist} - {title}")

        result = {
            "genius_lyrics": None,
            "spotify_lyrics": None,
            "source": None,
            "lyrics": None,
            "spotify_lyrics_data": None,  # Maintained for backward compatibility
        }

        # Try Genius first
        result["genius_lyrics"] = self.genius.fetch_lyrics(artist, title)
        if result["genius_lyrics"]:
            result["source"] = "genius"
            result["lyrics"] = result["genius_lyrics"]
            return result

        # Try Spotify if Genius failed
        result["spotify_lyrics"] = self.spotify.fetch_lyrics(artist, title)
        if result["spotify_lyrics"]:
            result["source"] = "spotify"
            result["lyrics"] = result["spotify_lyrics"]

        return result
