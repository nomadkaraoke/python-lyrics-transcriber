import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.genius import GeniusProvider


@pytest.fixture
def mock_logger():
    return Mock()


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
