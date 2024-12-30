import logging
from typing import Optional
import lyricsgenius
from .base_lyrics_provider import BaseLyricsProvider


class GeniusProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Genius."""

    def __init__(self, api_token: Optional[str], logger: Optional[logging.Logger] = None):
        super().__init__(logger)
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
