import pytest
from unittest.mock import Mock, patch
import requests
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData


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
def config_with_rapidapi():
    return LyricsProviderConfig(rapidapi_key="test_rapidapi_key")


@pytest.fixture
def config_with_both():
    return LyricsProviderConfig(genius_api_token="test_token", rapidapi_key="test_rapidapi_key")


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


@pytest.fixture
def mock_rapidapi_search_response():
    return {
        "hits": [
            {
                "result": {
                    "id": "12345",
                    "title": "Test Title",
                    "primary_artist": {"name": "Test Artist"},
                    "url": "https://genius.com/test",
                    "album": {"name": "Test Album"},
                    "release_date_for_display": "2023-01-01",
                    "annotation_count": 5,
                    "lyrics_state": "complete",
                    "pyongs_count": 10,
                }
            }
        ]
    }


@pytest.fixture
def mock_rapidapi_lyrics_response():
    return {
        "lyrics": {
            "lyrics": "Test lyrics from RapidAPI"
        }
    }


class TestGeniusProvider:
    @pytest.fixture
    def provider(self, mock_logger, config_with_token):
        with patch("lyricsgenius.Genius") as mock_genius:
            # Configure the mock client attributes
            mock_client = mock_genius.return_value
            mock_client.verbose = False
            mock_client.remove_section_headers = True
            
            provider = GeniusProvider(config=config_with_token, logger=mock_logger)
            provider.client = mock_client
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

    def test_init_with_rapidapi(self, mock_logger, config_with_rapidapi):
        """Test initialization with RapidAPI key"""
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        assert provider.rapidapi_key == "test_rapidapi_key"
        assert provider.client is None

    def test_init_with_both_tokens(self, mock_logger, config_with_both):
        """Test initialization with both tokens - should prioritize RapidAPI and not initialize client"""
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(config=config_with_both, logger=mock_logger)
            assert provider.api_token == "test_token"
            assert provider.rapidapi_key == "test_rapidapi_key"
            assert provider.client is None  # Should not initialize client when rapidapi_key is set

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
        mock_logger.warning.assert_called_with("No Genius API token provided and RapidAPI failed")

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

    @patch("requests.get")
    def test_fetch_from_rapidapi_success(self, mock_get, mock_logger, config_with_rapidapi, 
                                        mock_rapidapi_search_response, mock_rapidapi_lyrics_response):
        """Test successful RapidAPI fetch"""
        # Mock the two API calls
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: mock_rapidapi_search_response),
            Mock(status_code=200, json=lambda: mock_rapidapi_lyrics_response)
        ]
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is not None
        assert result["lyrics"] == "Test lyrics from RapidAPI"
        assert result["title"] == "Test Title"
        assert result["primary_artist"]["name"] == "Test Artist"
        
        # Verify the API calls were made correctly
        assert mock_get.call_count == 2
        
        # Check search call
        search_call = mock_get.call_args_list[0]
        assert "search" in search_call[0][0]
        assert search_call[1]["params"]["q"] == "Test Artist Test Title"
        
        # Check lyrics call  
        lyrics_call = mock_get.call_args_list[1]
        assert "lyrics" in lyrics_call[0][0]
        assert lyrics_call[1]["params"]["id"] == "12345"

    @patch("requests.get")
    def test_fetch_from_rapidapi_no_results(self, mock_get, mock_logger, config_with_rapidapi):
        """Test RapidAPI fetch with no search results"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"hits": []})
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No search results from RapidAPI")

    @patch("requests.get")
    def test_fetch_from_rapidapi_invalid_search_results(self, mock_get, mock_logger, config_with_rapidapi):
        """Test RapidAPI fetch with invalid search results"""
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            "hits": [{"result": {"title": "Test"}}]  # Missing ID
        })
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No valid song ID found in RapidAPI search results")

    @patch("requests.get")
    def test_fetch_from_rapidapi_no_lyrics(self, mock_get, mock_logger, config_with_rapidapi, 
                                          mock_rapidapi_search_response):
        """Test RapidAPI fetch with no lyrics in response"""
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: mock_rapidapi_search_response),
            Mock(status_code=200, json=lambda: {"lyrics": {}})  # No lyrics
        ]
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No lyrics found in RapidAPI response")

    @patch("requests.get")
    def test_fetch_from_rapidapi_request_error(self, mock_get, mock_logger, config_with_rapidapi):
        """Test RapidAPI fetch with request error"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is None
        mock_logger.error.assert_called_with("RapidAPI request failed: Network error")

    @patch("requests.get")
    def test_fetch_from_rapidapi_http_error(self, mock_get, mock_logger, config_with_rapidapi):
        """Test RapidAPI fetch with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_response
        
        provider = GeniusProvider(config=config_with_rapidapi, logger=mock_logger)
        result = provider._fetch_from_rapidapi("Test Artist", "Test Title")
        
        assert result is None
        mock_logger.error.assert_called_with("RapidAPI request failed: 403 Forbidden")

    @patch("requests.get")
    def test_fetch_data_from_source_rapidapi_priority(self, mock_get, mock_logger, config_with_both,
                                                     mock_rapidapi_search_response, mock_rapidapi_lyrics_response):
        """Test that RapidAPI is tried first when both tokens are available"""
        # Mock successful RapidAPI response
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: mock_rapidapi_search_response),
            Mock(status_code=200, json=lambda: mock_rapidapi_lyrics_response)
        ]
        
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(config=config_with_both, logger=mock_logger)
            result = provider._fetch_data_from_source("Test Artist", "Test Title")
        
        assert result is not None
        assert result["lyrics"] == "Test lyrics from RapidAPI"
        
        # Verify RapidAPI was called
        assert mock_get.call_count == 2
        
        # Verify Genius client was not used
        mock_genius.return_value.search_song.assert_not_called()

    @patch("requests.get")
    def test_fetch_data_from_source_rapidapi_fallback(self, mock_get, mock_logger, config_with_both, mock_song_data):
        """Test that when RapidAPI fails and rapidapi_key is set, no fallback occurs"""
        # Mock RapidAPI failure
        mock_get.side_effect = requests.RequestException("RapidAPI failed")
        
        with patch("lyricsgenius.Genius") as mock_genius:
            provider = GeniusProvider(config=config_with_both, logger=mock_logger)
            result = provider._fetch_data_from_source("Test Artist", "Test Title")
        
        assert result is None  # Should return None when RapidAPI fails and no fallback client
        
        # Verify RapidAPI was attempted
        assert mock_get.call_count == 1  # RapidAPI search attempt
        # Verify Genius client was not initialized (no fallback)
        mock_genius.assert_not_called()

    def test_convert_result_format_lyricsgenius(self, provider, mock_song_data):
        """Test conversion of lyricsgenius format to standardized format"""
        result = provider._convert_result_format(mock_song_data)

        assert isinstance(result, LyricsData)
        assert result.get_full_text() == "Test lyrics"
        assert len(result.segments) > 0  # Should have segments created from lyrics

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

    def test_convert_result_format_rapidapi(self, provider):
        """Test conversion of RapidAPI format to standardized format"""
        rapidapi_data = {
            "lyrics": "Test lyrics from RapidAPI",
            "title": "Test Title",
            "primary_artist": {"name": "Test Artist"},
            "id": "12345",
            "url": "https://genius.com/test",
            "album": {"name": "Test Album"},
            "release_date_for_display": "2023-01-01",
            "annotation_count": 5,
            "lyrics_state": "complete",
            "pyongs_count": 10,
            "_rapidapi_source": True,  # Mark as RapidAPI source for detection
        }

        result = provider._convert_result_format(rapidapi_data)

        assert isinstance(result, LyricsData)
        assert result.get_full_text() == "Test lyrics from RapidAPI"
        assert len(result.segments) > 0

        # Verify metadata
        metadata = result.metadata
        assert metadata.source == "genius"
        assert metadata.track_name == "Test Title"
        assert metadata.artist_names == "Test Artist"
        assert metadata.album_name == "Test Album"
        assert metadata.lyrics_provider == "genius"
        assert metadata.lyrics_provider_id == "12345"
        assert not metadata.is_synced

        # Check provider-specific metadata
        provider_metadata = metadata.provider_metadata
        assert provider_metadata["genius_id"] == "12345"
        assert provider_metadata["release_date"] == "2023-01-01"
        assert provider_metadata["page_url"] == "https://genius.com/test"
        assert provider_metadata["annotation_count"] == 5
        assert provider_metadata["lyrics_state"] == "complete"
        assert provider_metadata["pyongs_count"] == 10
        assert provider_metadata["api_source"] == "rapidapi"

    def test_convert_result_format_missing_fields(self, provider):
        """Test conversion with missing optional fields"""
        minimal_data = {"title": "Test Title", "artist_names": "Test Artist", "lyrics": "Test lyrics"}

        result = provider._convert_result_format(minimal_data)
        assert isinstance(result, LyricsData)
        assert result.get_full_text() == "Test lyrics"
        assert result.metadata.album_name is None
        assert result.metadata.provider_metadata["release_date"] is None

    def test_convert_result_format_rapidapi_missing_fields(self, provider):
        """Test conversion of RapidAPI format with missing optional fields"""
        minimal_rapidapi_data = {
            "lyrics": "Test lyrics from RapidAPI",
            "title": "Test Title",
            "primary_artist": {"name": "Test Artist"},
            "id": "12345",
            "_rapidapi_source": True,  # Mark as RapidAPI source for detection
        }

        result = provider._convert_result_format(minimal_rapidapi_data)
        assert isinstance(result, LyricsData)
        assert result.get_full_text() == "Test lyrics from RapidAPI"
        assert result.metadata.album_name is None
        assert result.metadata.provider_metadata["release_date"] is None
        assert result.metadata.provider_metadata["api_source"] == "rapidapi"
