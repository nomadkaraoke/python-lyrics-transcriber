import logging
import re
from typing import Optional, Dict, Any
import lyricsgenius
from lyrics_transcriber.types import LyricsData, LyricsMetadata
from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig


class GeniusProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Genius."""

    def __init__(self, config: LyricsProviderConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.api_token = config.genius_api_token
        self.client = None
        if self.api_token:
            self.client = lyricsgenius.Genius(
                self.api_token,
                verbose=(logger.getEffectiveLevel() == logging.DEBUG if logger else False),
                remove_section_headers=True,  # Remove [Chorus], [Verse], etc.
                skip_non_songs=True,  # Skip track listings and other non-song results
                timeout=10,  # Reasonable timeout for requests
                retries=3,  # Number of retries for failed requests
                sleep_time=1,  # Small delay between requests to be nice to the API
            )

    def _fetch_data_from_source(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Fetch raw song data from Genius API."""
        if not self.client:
            self.logger.warning("No Genius API token provided")
            return None

        self.logger.info(f"Searching Genius for {artist} - {title}")
        try:
            song = self.client.search_song(title, artist)
            if song:
                self.logger.info("Found lyrics on Genius")
                return song.to_dict()
        except Exception as e:
            self.logger.error(f"Error fetching from Genius: {str(e)}")
        return None

    def _convert_result_format(self, raw_data: Dict[str, Any]) -> LyricsData:
        """Convert Genius's raw API response to standardized format."""
        # Clean the lyrics before processing
        lyrics = self._clean_lyrics(raw_data.get("lyrics", ""))

        # Extract release date components if available
        release_date = None
        if release_components := raw_data.get("release_date_components"):
            year = release_components.get("year")
            month = release_components.get("month")
            day = release_components.get("day")
            if all(x is not None for x in (year, month, day)):
                release_date = f"{year}-{month:02d}-{day:02d}"

        # Create metadata object
        metadata = LyricsMetadata(
            source="genius",
            track_name=raw_data.get("title", ""),
            artist_names=raw_data.get("artist_names", ""),
            album_name=raw_data.get("album", {}).get("name"),
            lyrics_provider="genius",
            lyrics_provider_id=str(raw_data.get("id")),
            is_synced=False,  # Genius doesn't provide synced lyrics
            provider_metadata={
                "genius_id": raw_data.get("id"),
                "release_date": release_date,
                "page_url": raw_data.get("url"),
                "annotation_count": raw_data.get("annotation_count"),
                "lyrics_state": raw_data.get("lyrics_state"),
                "lyrics_owner_id": raw_data.get("lyrics_owner_id"),
                "pyongs_count": raw_data.get("pyongs_count"),
                "verified_annotations": len(raw_data.get("verified_annotations_by", [])),
                "verified_contributors": len(raw_data.get("verified_contributors", [])),
                "external_urls": {"genius": raw_data.get("url")},
            },
        )

        # Create segments with words from cleaned lyrics
        segments = self._create_segments_with_words(lyrics, is_synced=False)

        # Create result object with segments
        return LyricsData(source="genius", segments=segments, metadata=metadata)

    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean and process lyrics from Genius to remove unwanted content."""
        self.logger.debug("Starting lyrics cleaning process")
        original = lyrics

        lyrics = lyrics.replace("\\n", "\n")
        lyrics = re.sub(r"You might also like", "", lyrics)
        if original != lyrics:
            self.logger.debug("Removed 'You might also like' text")

        original = lyrics
        lyrics = re.sub(r".*?Lyrics([A-Z])", r"\1", lyrics)
        if original != lyrics:
            self.logger.debug("Removed song name and 'Lyrics' prefix")

        original = lyrics
        lyrics = re.sub(r"^[0-9]* Contributors.*Lyrics", "", lyrics)
        if original != lyrics:
            self.logger.debug("Removed contributors count and 'Lyrics' text")

        original = lyrics
        lyrics = re.sub(r"See.*Live.*Get tickets as low as \$[0-9]+", "", lyrics)
        if original != lyrics:
            self.logger.debug("Removed ticket sales text")

        original = lyrics
        lyrics = re.sub(r"[0-9]+Embed$", "", lyrics)
        if original != lyrics:
            self.logger.debug("Removed numbered embed marker")

        original = lyrics
        lyrics = re.sub(r"(\S)Embed$", r"\1", lyrics)
        if original != lyrics:
            self.logger.debug("Removed 'Embed' suffix from word")

        original = lyrics
        lyrics = re.sub(r"^Embed$", r"", lyrics)
        if original != lyrics:
            self.logger.debug("Removed standalone 'Embed' text")

        original = lyrics
        lyrics = re.sub(r".*?\[.*?\].*?", "", lyrics)
        if original != lyrics:
            self.logger.debug("Removed lines containing square brackets")

        self.logger.debug("Completed lyrics cleaning process")
        return lyrics
