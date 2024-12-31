import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig, LyricsData


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config_with_token():
    return LyricsProviderConfig(genius_api_token="test_token")


@pytest.fixture
def config_without_token():
    return LyricsProviderConfig(genius_api_token=None)


@pytest.fixture
def mock_song_data():
    return {
        "lyrics": "Test lyrics",
        "title": "Test Title",
        "artist_names": "Test Artist",
        "id": "123",
        "url": "https://genius.com/test",
        "album": {"name": "Test Album"},
        "release_date_components": {"year": 2023, "month": 1, "day": 1},
        "annotation_count": 5,
        "lyrics_state": "complete",
        "lyrics_owner_id": "456",
        "pyongs_count": 10,
        "verified_annotations_by": ["user1", "user2"],
        "verified_contributors": ["contrib1", "contrib2"],
    }


class TestGeniusProvider:
    @pytest.fixture
    def provider(self, mock_logger, config_with_token):
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(config=config_with_token, logger=mock_logger)
            provider.client = mock_genius.return_value
            return provider

    def test_init_with_token(self, provider):
        """Test initialization with API token"""
        assert provider.api_token == "test_token"
        assert provider.client is not None
        assert provider.client.verbose is False
        assert provider.client.remove_section_headers is True

    def test_init_without_token(self, mock_logger, config_without_token):
        """Test initialization without API token"""
        provider = GeniusProvider(config=config_without_token, logger=mock_logger)
        assert provider.client is None

    def test_fetch_data_from_source_success(self, provider, mock_song_data):
        """Test successful data fetch from Genius"""
        mock_song = Mock()
        mock_song.to_dict.return_value = mock_song_data
        provider.client.search_song.return_value = mock_song

        result = provider._fetch_data_from_source("Artist", "Title")
        assert result == mock_song_data
        provider.logger.info.assert_any_call("Found lyrics on Genius")

    def test_fetch_data_from_source_no_client(self, mock_logger, config_without_token):
        """Test fetch attempt without initialized client"""
        provider = GeniusProvider(config=config_without_token, logger=mock_logger)
        result = provider._fetch_data_from_source("Artist", "Title")
        assert result is None
        mock_logger.warning.assert_called_with("No Genius API token provided")

    def test_fetch_data_from_source_no_results(self, provider):
        """Test fetch with no results found"""
        provider.client.search_song.return_value = None
        result = provider._fetch_data_from_source("Artist", "Title")
        assert result is None

    def test_fetch_data_from_source_error(self, provider):
        """Test fetch with API error"""
        provider.client.search_song.side_effect = Exception("API Error")
        result = provider._fetch_data_from_source("Artist", "Title")
        assert result is None
        provider.logger.error.assert_called_once()

    def test_convert_result_format(self, provider, mock_song_data):
        """Test conversion of raw API response to standardized format"""
        result = provider._convert_result_format(mock_song_data)

        assert isinstance(result, LyricsData)
        assert result.lyrics == "Test lyrics"
        assert result.segments == []

        # Verify metadata
        metadata = result.metadata
        assert metadata.source == "genius"
        assert metadata.track_name == "Test Title"
        assert metadata.artist_names == "Test Artist"
        assert metadata.album_name == "Test Album"
        assert metadata.is_synced is False
        assert metadata.lyrics_provider == "genius"
        assert metadata.lyrics_provider_id == "123"

        # Verify provider-specific metadata
        assert metadata.provider_metadata["genius_id"] == "123"
        assert metadata.provider_metadata["release_date"] == "2023-01-01"
        assert metadata.provider_metadata["page_url"] == "https://genius.com/test"
        assert metadata.provider_metadata["verified_annotations"] == 2
        assert metadata.provider_metadata["verified_contributors"] == 2

    def test_convert_result_format_missing_fields(self, provider):
        """Test conversion with missing optional fields"""
        minimal_data = {"title": "Test Title", "artist_names": "Test Artist", "lyrics": "Test lyrics"}

        result = provider._convert_result_format(minimal_data)
        assert isinstance(result, LyricsData)
        assert result.lyrics == "Test lyrics"
        assert result.metadata.album_name is None
        assert result.metadata.provider_metadata["release_date"] is None
