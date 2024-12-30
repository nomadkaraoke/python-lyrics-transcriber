import logging
from typing import Optional, Dict
import requests
from .base_lyrics_provider import BaseLyricsProvider


class SpotifyProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Spotify."""

    def __init__(self, cookie: Optional[str], logger: Optional[logging.Logger] = None):
        super().__init__(logger)
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
