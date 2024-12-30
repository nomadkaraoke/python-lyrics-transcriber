import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.spotify import SpotifyProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return LyricsProviderConfig(spotify_cookie="test_cookie")


class TestSpotifyProvider:
    @pytest.fixture
    def provider(self, mock_logger, config):
        with patch("syrics.api.Spotify") as mock_spotify:
            # Configure the mock Spotify client
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
