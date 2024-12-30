import logging
from typing import Optional, Dict, Any
import lyricsgenius
from .base_lyrics_provider import BaseLyricsProvider, LyricsMetadata, LyricsProviderConfig, LyricsData


class GeniusProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Genius."""

    def __init__(self, config: LyricsProviderConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.api_token = config.genius_api_token
        self.client = None
        if self.api_token:
            self.client = lyricsgenius.Genius(self.api_token)
            self.client.verbose = False
            self.client.remove_section_headers = True

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

        # Create result object
        return LyricsData(lyrics=raw_data.get("lyrics", ""), segments=[], metadata=metadata)  # Genius doesn't provide timestamp data
