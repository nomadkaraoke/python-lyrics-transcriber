import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.spotify import SpotifyProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return LyricsProviderConfig(spotify_cookie="test_cookie")


@pytest.fixture
def mock_raw_data():
    """Fixture providing sample Spotify API response data"""
    return {
        "track_data": {
            "id": "track123",
            "name": "Test Track",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "album": {"name": "Test Album"},
            "duration_ms": 180000,
            "explicit": True,
            "external_urls": {"spotify": "https://open.spotify.com/track/123"},
            "preview_url": "https://preview.url",
        },
        "lyrics_data": {
            "lyrics": {
                "syncType": "LINE_SYNCED",
                "lines": [
                    {"startTimeMs": "1000", "endTimeMs": "2000", "words": "Line 1"},
                    {"startTimeMs": "2000", "endTimeMs": "3000", "words": "Line 2"},
                    {"startTimeMs": "0", "endTimeMs": "0", "words": "Line without timing"},
                ],
                "language": "en",
                "provider": "musicxmatch",
                "providerLyricsId": "lyrics123",
            }
        },
    }


class TestSpotifyProvider:
    @pytest.fixture
    def provider(self, mock_logger, config):
        with patch("syrics.api.Spotify") as mock_spotify:
            mock_instance = Mock()
            mock_spotify.return_value = mock_instance
            return SpotifyProvider(config=config, logger=mock_logger)

    def test_init(self, provider):
        assert provider.cookie == "test_cookie"

    def test_search_track_success(self, provider):
        # Mock both the search and lyrics response
        provider.client.search.return_value = {
            "tracks": {
                "items": [
                    {"id": "track123", "name": "Test Track", "artists": [{"name": "Test Artist"}], "external_urls": {"spotify": "url"}}
                ]
            }
        }
        provider.client.get_lyrics.return_value = {
            "lyrics": {"lines": [{"startTimeMs": "1000", "endTimeMs": "2000", "words": "Test lyrics"}]}
        }

        result = provider._fetch_data_from_source("Artist", "Title")
        assert result is not None
        assert result["track_data"]["id"] == "track123"
        assert "lyrics_data" in result

    def test_search_track_no_results(self, provider):
        provider.client.search.return_value = {"tracks": {"items": []}}
        result = provider._fetch_data_from_source("Artist", "Title")
        assert result is None

    def test_fetch_lyrics_no_cookie(self, mock_logger):
        config = LyricsProviderConfig(spotify_cookie=None)
        provider = SpotifyProvider(config=config, logger=mock_logger)
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None
        mock_logger.warning.assert_called_with("No Spotify cookie provided")

    def test_fetch_lyrics_error(self, provider):
        provider.client.search.side_effect = Exception("API Error")
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None
        provider.logger.error.assert_called_once()

    def test_fetch_lyrics_no_track_id(self, provider):
        """Test when no track ID is found"""
        provider.client.search.return_value = {"tracks": {"items": []}}
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None

    def test_fetch_lyrics_empty_lyrics(self, provider):
        """Test when lyrics endpoint returns empty data"""
        provider.client.search.return_value = {
            "tracks": {
                "items": [
                    {"id": "track123", "name": "Test Track", "artists": [{"name": "Test Artist"}], "external_urls": {"spotify": "url"}}
                ]
            }
        }
        provider.client.get_lyrics.return_value = None

        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None

    def test_convert_result_format(self, provider, mock_raw_data):
        """Test conversion of Spotify API response to standardized format"""
        result = provider._convert_result_format(mock_raw_data)

        assert isinstance(result, LyricsData)

        # Test segments
        assert len(result.segments) == 3  # All lines with words are included

        # Test first segment
        segment = result.segments[0]
        assert segment.text == "Line 1"
        assert segment.start_time == 1.0  # 1000ms -> 1.0s
        assert segment.end_time == 2.0
        assert segment.words == []  # Words list should be empty as per TODO comment

        # Test segment with zero timing
        segment_no_timing = result.segments[2]
        assert segment_no_timing.text == "Line without timing"
        assert segment_no_timing.start_time is None
        assert segment_no_timing.end_time is None

        # Test lyrics text
        assert result.lyrics == "Line 1\nLine 2\nLine without timing"

        # Test metadata
        metadata = result.metadata
        assert metadata.source == "spotify"
        assert metadata.track_name == "Test Track"
        assert metadata.artist_names == "Artist 1, Artist 2"
        assert metadata.album_name == "Test Album"
        assert metadata.duration_ms == 180000
        assert metadata.explicit is True
        assert metadata.language == "en"
        assert metadata.is_synced is True
        assert metadata.lyrics_provider == "musicxmatch"
        assert metadata.lyrics_provider_id == "lyrics123"

        # Test provider-specific metadata
        assert metadata.provider_metadata["spotify_id"] == "track123"
        assert metadata.provider_metadata["preview_url"] == "https://preview.url"
        assert metadata.provider_metadata["external_urls"] == {"spotify": "https://open.spotify.com/track/123"}
        assert metadata.provider_metadata["sync_type"] == "LINE_SYNCED"

    def test_convert_result_format_minimal(self, provider):
        """Test conversion with minimal data"""
        minimal_data = {
            "track_data": {"name": "Test Track", "artists": [{"name": "Artist"}]},
            "lyrics_data": {"lyrics": {"lines": [{"startTimeMs": "1000", "endTimeMs": "2000", "words": "Test lyrics"}]}},
        }

        result = provider._convert_result_format(minimal_data)
        assert isinstance(result, LyricsData)
        assert len(result.segments) == 1
        assert result.lyrics == "Test lyrics"
        assert result.metadata.track_name == "Test Track"
        assert result.metadata.artist_names == "Artist"

    def test_convert_result_format_skip_empty_words(self, provider):
        """Test that lines without words are skipped"""
        data = {
            "track_data": {"name": "Test Track", "artists": [{"name": "Artist"}]},
            "lyrics_data": {
                "lyrics": {
                    "lines": [
                        {"startTimeMs": "1000", "endTimeMs": "2000", "words": ""},  # Empty words
                        {"startTimeMs": "2000", "endTimeMs": "3000"},  # Missing words field
                        {"startTimeMs": "3000", "endTimeMs": "4000", "words": "Valid line"},
                    ]
                }
            },
        }

        result = provider._convert_result_format(data)
        assert len(result.segments) == 1  # Only the valid line should be included
        assert result.segments[0].text == "Valid line"
