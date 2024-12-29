import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.core.fetcher import (
    LyricsFetcherConfig,
    GeniusProvider,
    SpotifyProvider,
    LyricsFetcher,
)


@pytest.fixture
def mock_logger():
    return Mock()


class TestLyricsFetcherConfig:
    def test_default_config(self):
        config = LyricsFetcherConfig()
        assert config.genius_api_token is None
        assert config.spotify_cookie is None

    def test_custom_config(self):
        config = LyricsFetcherConfig(genius_api_token="test_token", spotify_cookie="test_cookie")
        assert config.genius_api_token == "test_token"
        assert config.spotify_cookie == "test_cookie"


class TestGeniusProvider:
    @pytest.fixture
    def provider(self, mock_logger):
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(api_token="test_token", logger=mock_logger)
            # Store the mock instance, not the class
            provider.client = mock_genius.return_value
            return provider

    def test_init_with_token(self, provider):
        assert provider.api_token == "test_token"
        assert provider.client is not None
        assert provider.client.verbose is False
        assert provider.client.remove_section_headers is True

    def test_init_without_token(self, mock_logger):
        provider = GeniusProvider(api_token=None, logger=mock_logger)
        assert provider.client is None

    def test_fetch_lyrics_success(self, provider):
        mock_song = Mock()
        mock_song.lyrics = "Test lyrics"
        provider.client.search_song.return_value = mock_song

        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics == "Test lyrics"
        provider.logger.info.assert_called_with("Found lyrics on Genius")

    def test_fetch_lyrics_no_results(self, provider):
        provider.client.search_song.return_value = None
        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None

    def test_fetch_lyrics_error(self, provider):
        provider.client.search_song.side_effect = Exception("API Error")
        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        provider.logger.error.assert_called_once()

    def test_fetch_lyrics_no_token(self, mock_logger):
        provider = GeniusProvider(api_token=None, logger=mock_logger)
        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        mock_logger.warning.assert_called_with("No Genius API token provided")


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
        # Verify we only called the search API, not the lyrics API
        assert mock_get.call_count == 1

    @patch("requests.get")
    def test_fetch_lyrics_empty_lyrics(self, mock_get, provider):
        """Test when lyrics endpoint returns empty data"""
        # First response for track search
        search_response = Mock()
        search_response.json.return_value = {"tracks": {"items": [{"id": "track123"}]}}
        # Second response for lyrics fetch
        lyrics_response = Mock()
        lyrics_response.json.return_value = {"lyrics": {"lines": []}}

        mock_get.side_effect = [search_response, lyrics_response]

        lyrics = provider.fetch_lyrics("Artist", "Title")
        assert lyrics is None
        assert mock_get.call_count == 2


class TestLyricsFetcher:
    @pytest.fixture
    def mock_genius_provider(self):
        return Mock()

    @pytest.fixture
    def mock_spotify_provider(self):
        return Mock()

    @pytest.fixture
    def fetcher(self, mock_logger, mock_genius_provider, mock_spotify_provider):
        return LyricsFetcher(
            config=LyricsFetcherConfig(genius_api_token="token", spotify_cookie="cookie"),
            genius_provider=mock_genius_provider,
            spotify_provider=mock_spotify_provider,
            logger=mock_logger,
        )

    def test_fetch_lyrics_genius_success(self, fetcher, mock_genius_provider):
        mock_genius_provider.fetch_lyrics.return_value = "Genius lyrics"
        result = fetcher.fetch_lyrics("Artist", "Title")

        assert result["source"] == "genius"
        assert result["lyrics"] == "Genius lyrics"
        assert result["genius_lyrics"] == "Genius lyrics"
        assert result["spotify_lyrics"] is None

    def test_fetch_lyrics_spotify_fallback(self, fetcher, mock_genius_provider, mock_spotify_provider):
        mock_genius_provider.fetch_lyrics.return_value = None
        mock_spotify_provider.fetch_lyrics.return_value = "Spotify lyrics"

        result = fetcher.fetch_lyrics("Artist", "Title")

        assert result["source"] == "spotify"
        assert result["lyrics"] == "Spotify lyrics"
        assert result["genius_lyrics"] is None
        assert result["spotify_lyrics"] == "Spotify lyrics"

    def test_fetch_lyrics_all_fail(self, fetcher, mock_genius_provider, mock_spotify_provider):
        mock_genius_provider.fetch_lyrics.return_value = None
        mock_spotify_provider.fetch_lyrics.return_value = None

        result = fetcher.fetch_lyrics("Artist", "Title")

        assert result["source"] is None
        assert result["lyrics"] is None
        assert result["genius_lyrics"] is None
        assert result["spotify_lyrics"] is None

    def test_init_with_env_vars(self, mock_logger):
        with patch.dict("os.environ", {"GENIUS_API_TOKEN": "env_token", "SPOTIFY_COOKIE": "env_cookie"}):
            fetcher = LyricsFetcher(logger=mock_logger)
            assert isinstance(fetcher.genius, GeniusProvider)
            assert isinstance(fetcher.spotify, SpotifyProvider)
