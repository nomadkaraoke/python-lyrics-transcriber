import logging
from typing import Optional, Dict, Any
import syrics.api
import time

from lyrics_transcriber.types import LyricsData, LyricsMetadata, LyricsSegment, Word
from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig
from lyrics_transcriber.utils.word_utils import WordUtils


class SpotifyProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Spotify."""

    def __init__(self, config: LyricsProviderConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.cookie = config.spotify_cookie
        self.client = None

        if self.cookie:
            max_retries = 5
            retry_delay = 5  # seconds

            for attempt in range(max_retries):
                try:
                    self.client = syrics.api.Spotify(self.cookie)
                    break  # Successfully initialized
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        self.logger.error(f"Failed to initialize Spotify client after {max_retries} attempts: {str(e)}")
                        break
                    self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

    def _fetch_data_from_source(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Fetch raw data from Spotify APIs using syrics library."""
        if not self.client:
            self.logger.warning("No Spotify cookie provided")
            return None

        try:
            # Search for track
            search_query = f"{title} - {artist}"
            search_results = self.client.search(search_query, type="track", limit=1)

            track_data = search_results["tracks"]["items"][0]
            self.logger.debug(
                f"Found track: {track_data['artists'][0]['name']} - {track_data['name']} " f"({track_data['external_urls']['spotify']})"
            )

            # Get lyrics data
            lyrics_data = self.client.get_lyrics(track_data["id"])
            if not lyrics_data:
                return None

            return {"track_data": track_data, "lyrics_data": lyrics_data}
        except Exception as e:
            self.logger.error(f"Error fetching from Spotify: {str(e)}")
            return None

    def _convert_result_format(self, raw_data: Dict[str, Any]) -> LyricsData:
        """Convert Spotify's raw API response to standardized format."""
        track_data = raw_data["track_data"]
        lyrics_data = raw_data["lyrics_data"]["lyrics"]

        # Create metadata object
        metadata = LyricsMetadata(
            source="spotify",
            track_name=track_data.get("name"),
            artist_names=", ".join(artist.get("name", "") for artist in track_data.get("artists", [])),
            album_name=track_data.get("album", {}).get("name"),
            duration_ms=track_data.get("duration_ms"),
            explicit=track_data.get("explicit"),
            language=lyrics_data.get("language"),
            is_synced=lyrics_data.get("syncType") == "LINE_SYNCED",
            lyrics_provider=lyrics_data.get("provider"),
            lyrics_provider_id=lyrics_data.get("providerLyricsId"),
            provider_metadata={
                "spotify_id": track_data.get("id"),
                "preview_url": track_data.get("preview_url"),
                "external_urls": track_data.get("external_urls"),
                "sync_type": lyrics_data.get("syncType"),
            },
        )

        # Create segments with timing information
        segments = []
        for line in lyrics_data.get("lines", []):
            if not line.get("words"):
                continue

            # Skip lines that are just musical notes
            if not self._clean_lyrics(line["words"]):
                continue

            # Split line into words
            word_texts = line["words"].strip().split()
            if not word_texts:
                continue

            # Calculate approximate timing for each word
            start_time = float(line["startTimeMs"]) / 1000 if line["startTimeMs"] != "0" else 0.0
            end_time = float(line["endTimeMs"]) / 1000 if line["endTimeMs"] != "0" else 0.0
            duration = end_time - start_time
            word_duration = duration / len(word_texts)

            words = []
            for i, word_text in enumerate(word_texts):
                word = Word(
                    id=WordUtils.generate_id(),
                    text=word_text,
                    start_time=start_time + (i * word_duration),
                    end_time=start_time + ((i + 1) * word_duration),
                    confidence=1.0,
                    created_during_correction=False,
                )
                words.append(word)

            segment = LyricsSegment(
                id=WordUtils.generate_id(), text=line["words"].strip(), words=words, start_time=start_time, end_time=end_time
            )
            segments.append(segment)

        return LyricsData(source="spotify", segments=segments, metadata=metadata)

    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean and process lyrics from Spotify to remove unwanted content."""
        # Remove lines that contain only musical note symbols
        if lyrics.strip() == "♪":
            return ""
        return lyrics
