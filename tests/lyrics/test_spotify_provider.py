import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.spotify import SpotifyProvider


@pytest.fixture
def mock_logger():
    return Mock()


class TestSpotifyProvider:
    @pytest.fixture
    def provider(self, mock_logger):
        return SpotifyProvider(cookie="test_cookie", logger=mock_logger)

    def test_init(self, provider):
        assert provider.cookie == "test_cookie"

    def test_get_headers(self, provider):
        headers = provider._get_headers()
        assert headers["Cookie"] == "sp_dc=test_cookie"
        assert "User-Agent" in headers
        assert "App-Platform" in headers

    @patch("requests.get")
    def test_search_track_success(self, mock_get, provider):
        mock_response = Mock()
        mock_response.json.return_value = {"tracks": {"items": [{"id": "track123"}]}}
        mock_get.return_value = mock_response

        track_id = provider._search_track("Artist", "Title")
        assert track_id == "track123"

    @patch("requests.get")
    def test_search_track_no_results(self, mock_get, provider):
        mock_response = Mock()
        mock_response.json.return_value = {"tracks": {"items": []}}
        mock_get.return_value = mock_response

        track_id = provider._search_track("Artist", "Title")
        assert track_id is None

    @patch("requests.get")
    def test_fetch_track_lyrics_success(self, mock_get, provider):
        mock_response = Mock()
        mock_response.json.return_value = {"lyrics": {"lines": [{"words": "Line 1"}, {"words": "Line 2"}]}}
        mock_get.return_value = mock_response

        lyrics = provider._fetch_track_lyrics("track123")
        assert lyrics == "Line 1\nLine 2"

    def test_fetch_lyrics_no_cookie(self, mock_logger):
        provider = SpotifyProvider(cookie=None, logger=mock_logger)
        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        mock_logger.warning.assert_called_with("No Spotify cookie provided")

    @patch("requests.get")
    def test_fetch_lyrics_error(self, mock_get, provider):
        mock_get.side_effect = Exception("API Error")
        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        provider.logger.error.assert_called_once()

    @patch("requests.get")
    def test_fetch_lyrics_no_track_id(self, mock_get, provider):
        """Test when no track ID is found"""
        mock_response = Mock()
        mock_response.json.return_value = {"tracks": {"items": []}}
        mock_get.return_value = mock_response

        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        assert mock_get.call_count == 1

    @patch("requests.get")
    def test_fetch_lyrics_empty_lyrics(self, mock_get, provider):
        """Test when lyrics endpoint returns empty data"""
        search_response = Mock()
        search_response.json.return_value = {"tracks": {"items": [{"id": "track123"}]}}
        lyrics_response = Mock()
        lyrics_response.json.return_value = {"lyrics": {"lines": []}}

        mock_get.side_effect = [search_response, lyrics_response]

        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        assert mock_get.call_count == 2
