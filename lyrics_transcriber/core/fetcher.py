import os
import logging
import lyricsgenius
import requests
from typing import Optional, Dict, Any


class LyricsFetcher:
    """Handles fetching lyrics from various online sources."""

    def __init__(
        self, genius_api_token: Optional[str] = None, spotify_cookie: Optional[str] = None, logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.genius_api_token = genius_api_token or os.getenv("GENIUS_API_TOKEN")
        self.spotify_cookie = spotify_cookie or os.getenv("SPOTIFY_COOKIE")

        # Initialize Genius API client if token provided
        self.genius = None
        if self.genius_api_token:
            self.genius = lyricsgenius.Genius(self.genius_api_token)
            self.genius.verbose = False
            self.genius.remove_section_headers = True

    def fetch_lyrics(self, artist: str, title: str) -> Dict[str, Any]:
        """
        Fetch lyrics from all available sources.

        Args:
            artist: Name of the artist
            title: Title of the song

        Returns:
            Dict containing:
                - genius_lyrics: Lyrics from Genius (if available)
                - spotify_lyrics: Lyrics from Spotify (if available)
                - source: The preferred source ("genius" or "spotify")
                - lyrics: The best lyrics found from any source
        """
        self.logger.info(f"Fetching lyrics for {artist} - {title}")

        result = {"genius_lyrics": None, "spotify_lyrics": None, "source": None, "lyrics": None}

        # Try Genius first
        if self.genius:
            try:
                result["genius_lyrics"] = self._fetch_from_genius(artist, title)
                if result["genius_lyrics"]:
                    result["source"] = "genius"
                    result["lyrics"] = result["genius_lyrics"]
            except Exception as e:
                self.logger.error(f"Failed to fetch lyrics from Genius: {str(e)}")

        # Try Spotify if Genius failed or wasn't available
        if self.spotify_cookie and not result["lyrics"]:
            try:
                result["spotify_lyrics"] = self._fetch_from_spotify(artist, title)
                if result["spotify_lyrics"]:
                    result["source"] = "spotify"
                    result["lyrics"] = result["spotify_lyrics"]
            except Exception as e:
                self.logger.error(f"Failed to fetch lyrics from Spotify: {str(e)}")

        return result

    def _fetch_from_genius(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics from Genius."""
        self.logger.info(f"Searching Genius for {artist} - {title}")

        try:
            song = self.genius.search_song(title, artist)
            if song:
                self.logger.info("Found lyrics on Genius")
                return song.lyrics
        except Exception as e:
            self.logger.error(f"Error fetching from Genius: {str(e)}")

        return None

    def _fetch_from_spotify(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics from Spotify.

        Uses the Spotify cookie to authenticate and fetch lyrics for a given song.
        The cookie can be obtained by logging into Spotify Web Player and copying
        the 'sp_dc' cookie value.
        """
        self.logger.info(f"Searching Spotify for {artist} - {title}")

        if not self.spotify_cookie:
            self.logger.warning("No Spotify cookie provided, skipping Spotify lyrics fetch")
            return None

        try:
            # First, search for the track
            search_url = "https://api.spotify.com/v1/search"
            headers = {
                "Cookie": f"sp_dc={self.spotify_cookie}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "App-Platform": "WebPlayer",
            }
            params = {"q": f"artist:{artist} track:{title}", "type": "track", "limit": 1}

            self.logger.debug("Making Spotify search request")
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()

            search_data = response.json()
            if not search_data.get("tracks", {}).get("items"):
                self.logger.warning("No tracks found on Spotify")
                return None

            track = search_data["tracks"]["items"][0]
            track_id = track["id"]

            # Then, fetch lyrics for the track
            lyrics_url = f"https://api.spotify.com/v1/tracks/{track_id}/lyrics"

            self.logger.debug("Making Spotify lyrics request")
            lyrics_response = requests.get(lyrics_url, headers=headers)
            lyrics_response.raise_for_status()

            lyrics_data = lyrics_response.json()
            if not lyrics_data.get("lyrics", {}).get("lines"):
                self.logger.warning("No lyrics found for track on Spotify")
                return None

            # Combine all lines into a single string
            lyrics_lines = [line["words"] for line in lyrics_data["lyrics"]["lines"] if line.get("words")]
            lyrics = "\n".join(lyrics_lines)

            self.logger.info("Successfully fetched lyrics from Spotify")
            return lyrics

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to Spotify: {str(e)}")
            return None
        except KeyError as e:
            self.logger.error(f"Unexpected response format from Spotify: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching from Spotify: {str(e)}")
            return None
