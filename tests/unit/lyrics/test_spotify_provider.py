import pytest
from unittest.mock import Mock, patch, call
from lyrics_transcriber.lyrics.spotify import SpotifyProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData
import requests


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
        mock_logger.warning.assert_called_with("No Spotify cookie provided and RapidAPI failed")

    def test_fetch_lyrics_no_cookie_no_rapidapi(self, mock_logger):
        """Test when no cookie and no rapidapi key are provided"""
        config = LyricsProviderConfig(spotify_cookie=None, rapidapi_key=None)
        provider = SpotifyProvider(config=config, logger=mock_logger)
        result = provider.fetch_lyrics("Artist", "Title")
        assert result is None
        mock_logger.warning.assert_called_with("No Spotify cookie provided and RapidAPI failed")

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

    @patch('requests.get')
    def test_fetch_from_rapidapi_success(self, mock_get, mock_logger):
        """Test successful RapidAPI fetch"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "status": True,
            "errorId": "Success",
            "id": "test_track_id",
            "name": "Test Track",
            "artists": [{"name": "Test Artist"}]
        }
        mock_search_response.raise_for_status.return_value = None
        
        # Mock lyrics response
        mock_lyrics_response = Mock()
        mock_lyrics_response.json.return_value = [
            {"startMs": 1000, "durMs": 2000, "text": "Test lyrics line 1"},
            {"startMs": 3000, "durMs": 2000, "text": "Test lyrics line 2"}
        ]
        mock_lyrics_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_search_response, mock_lyrics_response]
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is not None
        assert result["_rapidapi_source"] is True
        assert result["track_data"]["id"] == "test_track_id"
        assert len(result["lyrics_data"]) == 2
        
        # Verify the API calls
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_fetch_from_rapidapi_search_failure(self, mock_get, mock_logger):
        """Test RapidAPI search failure"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock failed search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "status": False,
            "errorId": "Error"
        }
        mock_search_response.raise_for_status.return_value = None
        
        mock_get.return_value = mock_search_response
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("RapidAPI search failed")

    @patch('requests.get')
    def test_fetch_from_rapidapi_no_track_id(self, mock_get, mock_logger):
        """Test RapidAPI response without track ID"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock search response without track ID
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "status": True,
            "errorId": "Success",
            "name": "Test Track"
            # Missing "id" field
        }
        mock_search_response.raise_for_status.return_value = None
        
        mock_get.return_value = mock_search_response
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No track ID found in RapidAPI search results")

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
        assert len(segment.words) > 0  # Words should be created from the text

        # Test segment with zero timing
        segment_no_timing = result.segments[2]
        assert segment_no_timing.text == "Line without timing"
        assert segment_no_timing.start_time == 0.0  # Zero timing is converted to 0.0, not None
        assert segment_no_timing.end_time == 0.0

        # Test lyrics text
        assert result.get_full_text() == "Line 1\nLine 2\nLine without timing"

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
        assert result.get_full_text() == "Test lyrics"
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

    def test_convert_rapidapi_format(self, provider, mock_raw_data):
        """Test conversion of RapidAPI response to standardized format"""
        # This test is for syrics format, not RapidAPI format
        result = provider._convert_syrics_format(mock_raw_data)

        assert isinstance(result, LyricsData)

        # Test segments
        assert len(result.segments) == 3  # All lines with words are included

        # Test first segment
        segment = result.segments[0]
        assert segment.text == "Line 1"
        assert segment.start_time == 1.0  # 1000ms -> 1.0s
        assert segment.end_time == 2.0
        assert len(segment.words) > 0  # Words should be created from the text

        # Test segment with zero timing
        segment_no_timing = result.segments[2]
        assert segment_no_timing.text == "Line without timing"
        assert segment_no_timing.start_time == 0.0  # Zero timing is converted to 0.0, not None
        assert segment_no_timing.end_time == 0.0

        # Test lyrics text
        assert result.get_full_text() == "Line 1\nLine 2\nLine without timing"

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

    def test_convert_rapidapi_format_proper(self, mock_logger):
        """Test conversion of actual RapidAPI response to standardized format"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        rapidapi_data = {
            "_rapidapi_source": True,
            "track_data": {
                "id": "test_track_id",
                "name": "Test Track",
                "artists": [{"name": "Test Artist"}],
                "album": {"name": "Test Album"},
                "durationMs": 180000,
                "explicit": True,
                "shareUrl": "https://open.spotify.com/track/123",
                "durationText": "03:00"
            },
            "lyrics_data": [
                {"startMs": 1000, "durMs": 2000, "text": "Line 1"},
                {"startMs": 3000, "durMs": 2000, "text": "Line 2"}
            ]
        }
        
        result = provider._convert_rapidapi_format(rapidapi_data)
        
        assert isinstance(result, LyricsData)
        assert len(result.segments) == 2
        
        # Test first segment
        segment = result.segments[0]
        assert segment.text == "Line 1"
        assert segment.start_time == 1.0  # 1000ms -> 1.0s
        assert segment.end_time == 3.0   # 1000ms + 2000ms -> 3.0s
        
        # Test metadata
        metadata = result.metadata
        assert metadata.source == "spotify"
        assert metadata.track_name == "Test Track"
        assert metadata.artist_names == "Test Artist"
        assert metadata.album_name == "Test Album"
        assert metadata.duration_ms == 180000
        assert metadata.explicit is True
        assert metadata.is_synced is True
        assert metadata.lyrics_provider == "spotify"
        assert metadata.lyrics_provider_id == "test_track_id"
        
        # Test provider-specific metadata
        assert metadata.provider_metadata["spotify_id"] == "test_track_id"
        assert metadata.provider_metadata["share_url"] == "https://open.spotify.com/track/123"
        assert metadata.provider_metadata["duration_text"] == "03:00"
        assert metadata.provider_metadata["api_source"] == "rapidapi"

    @patch('syrics.api.Spotify')
    @patch('time.sleep')
    def test_init_with_cookie_retry_logic(self, mock_sleep, mock_spotify, mock_logger):
        """Test syrics client initialization with retry logic"""
        # Mock client to fail first few times then succeed
        mock_spotify.side_effect = [Exception("Connection failed"), Exception("Auth failed"), Mock()]
        
        config = LyricsProviderConfig(spotify_cookie="test_cookie")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Should have called sleep twice (for first two failures)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(5)
        
        # Should have logged warnings for retries
        expected_calls = [
            call("Attempt 1/5 failed, retrying in 5 seconds..."),
            call("Attempt 2/5 failed, retrying in 5 seconds...")
        ]
        mock_logger.warning.assert_has_calls(expected_calls)

    @patch('syrics.api.Spotify')
    def test_init_with_cookie_max_retries_exceeded(self, mock_spotify, mock_logger):
        """Test syrics client initialization when max retries exceeded"""
        # Mock client to always fail
        mock_spotify.side_effect = Exception("Connection failed")
        
        config = LyricsProviderConfig(spotify_cookie="test_cookie")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Should have logged final error message
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to initialize Spotify client after 5 attempts" in error_call

    @patch('requests.get')
    def test_fetch_from_rapidapi_request_exception(self, mock_get, mock_logger):
        """Test RapidAPI request exception handling"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock request to raise exception
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is None
        mock_logger.error.assert_called_with("RapidAPI request failed: Network error")

    @patch('requests.get')
    def test_fetch_from_rapidapi_general_exception(self, mock_get, mock_logger):
        """Test RapidAPI general exception handling"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock request to raise general exception
        mock_get.side_effect = ValueError("JSON decode error")
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is None
        mock_logger.error.assert_called_with("Error fetching from RapidAPI: JSON decode error")

    def test_convert_syrics_format_with_musical_notes(self, mock_logger):
        """Test syrics format conversion with musical notes that should be skipped"""
        config = LyricsProviderConfig(spotify_cookie="test_cookie")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        syrics_data = {
            "track_data": {
                "name": "Test Track",
                "artists": [{"name": "Test Artist"}]
            },
            "lyrics_data": {
                "lyrics": {
                    "lines": [
                        {"startTimeMs": "1000", "endTimeMs": "2000", "words": "♪"},  # Musical note
                        {"startTimeMs": "2000", "endTimeMs": "3000", "words": "Valid line"},
                        {"startTimeMs": "3000", "endTimeMs": "4000", "words": "   "},  # Empty after strip
                    ]
                }
            }
        }
        
        result = provider._convert_syrics_format(syrics_data)
        
        # Should only have one segment (the valid line)
        assert len(result.segments) == 1
        assert result.segments[0].text == "Valid line"

    def test_convert_rapidapi_format_with_musical_notes(self, mock_logger):
        """Test RapidAPI format conversion with musical notes that should be skipped"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        rapidapi_data = {
            "_rapidapi_source": True,
            "track_data": {
                "id": "test_track_id",
                "name": "Test Track",
                "artists": [{"name": "Test Artist"}]
            },
            "lyrics_data": [
                {"startMs": 1000, "durMs": 2000, "text": "♪"},  # Musical note
                {"startMs": 2000, "durMs": 2000, "text": "Valid line"},
                {"startMs": 3000, "durMs": 2000, "text": "   "},  # Empty after strip
                {"startMs": 4000, "durMs": 2000}  # Missing text field
            ]
        }
        
        result = provider._convert_rapidapi_format(rapidapi_data)
        
        # Should only have one segment (the valid line)
        assert len(result.segments) == 1
        assert result.segments[0].text == "Valid line"

    def test_clean_lyrics_with_musical_note(self, mock_logger):
        """Test _clean_lyrics method with musical note symbol"""
        config = LyricsProviderConfig()
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Test with musical note
        result = provider._clean_lyrics("♪")
        assert result == ""
        
        # Test with normal text
        result = provider._clean_lyrics("Normal lyrics")
        assert result == "Normal lyrics"
        
        # Test with musical note and spaces
        result = provider._clean_lyrics("  ♪  ")
        assert result == ""

    @patch('syrics.api.Spotify')
    @patch('time.sleep')
    def test_init_with_cookie_single_retry(self, mock_sleep, mock_spotify, mock_logger):
        """Test syrics client initialization with single retry to ensure sleep is called"""
        # Mock client to fail once then succeed
        mock_spotify.side_effect = [Exception("Connection failed"), Mock()]
        
        config = LyricsProviderConfig(spotify_cookie="test_cookie")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Should have called sleep once
        mock_sleep.assert_called_once_with(5)
        
        # Should have logged warning for retry
        mock_logger.warning.assert_called_with("Attempt 1/5 failed, retrying in 5 seconds...")

    @patch('requests.get')
    def test_fetch_from_rapidapi_lyrics_request_failure(self, mock_get, mock_logger):
        """Test RapidAPI lyrics request failure after successful search"""
        config = LyricsProviderConfig(rapidapi_key="test_key")
        provider = SpotifyProvider(config=config, logger=mock_logger)
        
        # Mock successful search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "status": True,
            "errorId": "Success",
            "id": "test_track_id",
            "name": "Test Track",
            "artists": [{"name": "Test Artist"}]
        }
        mock_search_response.raise_for_status.return_value = None
        
        # Mock failed lyrics response
        mock_lyrics_response = Mock()
        mock_lyrics_response.raise_for_status.side_effect = requests.exceptions.RequestException("Lyrics request failed")
        
        mock_get.side_effect = [mock_search_response, mock_lyrics_response]
        
        result = provider._fetch_from_rapidapi("Artist", "Title")
        
        assert result is None
        mock_logger.error.assert_called_with("RapidAPI request failed: Lyrics request failed")
