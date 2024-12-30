import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config_with_token():
    return LyricsProviderConfig(genius_api_token="test_token")


@pytest.fixture
def config_without_token():
    return LyricsProviderConfig(genius_api_token=None)


class TestGeniusProvider:
    @pytest.fixture
    def provider(self, mock_logger, config_with_token):
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(config=config_with_token, logger=mock_logger)
            # Store the mock instance, not the class
            provider.client = mock_genius.return_value
            return provider

    def test_init_with_token(self, provider):
        assert provider.api_token == "test_token"
        assert provider.client is not None
        assert provider.client.verbose is False
        assert provider.client.remove_section_headers is True

    def test_init_without_token(self, mock_logger, config_without_token):
        provider = GeniusProvider(config=config_without_token, logger=mock_logger)
        assert provider.client is None

    def test_fetch_lyrics_success(self, provider):
        mock_song = Mock()
        mock_song.to_dict.return_value = {"lyrics": "Test lyrics", "title": "Test Title", "artist_names": "Test Artist"}
        provider.client.search_song.return_value = mock_song

        result = provider.fetch_lyrics("Artist", "Title")
        assert result.lyrics == "Test lyrics"
        provider.logger.info.assert_any_call("Found lyrics on Genius")

    def test_fetch_lyrics_no_results(self, provider):
        provider.client.search_song.return_value = None
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None

    def test_fetch_lyrics_error(self, provider):
        provider.client.search_song.side_effect = Exception("API Error")
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None
        provider.logger.error.assert_called_once()

    def test_fetch_lyrics_no_token(self, mock_logger, config_without_token):
        provider = GeniusProvider(config=config_without_token, logger=mock_logger)
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None
        mock_logger.warning.assert_called_with("No Genius API token provided")
