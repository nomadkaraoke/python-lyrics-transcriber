import logging
from typing import Optional, Dict, Any
import syrics.api

from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsSegment, Word
from .base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig, LyricsMetadata, LyricsData


class SpotifyProvider(BaseLyricsProvider):
    """Handles fetching lyrics from Spotify."""

    def __init__(self, config: LyricsProviderConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.cookie = config.spotify_cookie
        self.client = syrics.api.Spotify(self.cookie) if self.cookie else None

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

        # Convert raw lines to LyricsSegment objects
        segments = []
        for line in lyrics_data.get("lines", []):
            if not line.get("words"):
                continue

            segment = LyricsSegment(
                text=line["words"],
                words=[],  # TODO: Could potentially split words if needed
                start_time=float(line["startTimeMs"]) / 1000 if line["startTimeMs"] != "0" else None,
                end_time=float(line["endTimeMs"]) / 1000 if line["endTimeMs"] != "0" else None,
            )
            segments.append(segment)

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

        return LyricsData(lyrics="\n".join(segment.text for segment in segments), segments=segments, metadata=metadata)
