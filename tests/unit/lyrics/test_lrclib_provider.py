import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import requests
from lyrics_transcriber.lyrics.lrclib import LRCLIBProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return LyricsProviderConfig(cache_dir="cache")


@pytest.fixture
def config_with_audio():
    return LyricsProviderConfig(cache_dir="cache", audio_filepath="/path/to/audio.mp3")


@pytest.fixture
def mock_lrclib_response():
    """Mock LRCLIB API response with both synced and plain lyrics"""
    return {
        "id": 3396226,
        "trackName": "I Want to Live",
        "artistName": "Borislav Slavov",
        "albumName": "Baldur's Gate 3 (Original Game Soundtrack)",
        "duration": 233,
        "instrumental": False,
        "plainLyrics": "I feel your breath upon my neck\nThe clock won't stop and this is what we get\n",
        "syncedLyrics": "[00:17.12] I feel your breath upon my neck\n[00:22.45] A kiss goodbye\n[03:20.31] The clock won't stop and this is what we get\n"
    }


@pytest.fixture
def mock_lrclib_plain_only():
    """Mock LRCLIB API response with only plain lyrics"""
    return {
        "id": 123456,
        "trackName": "Test Song",
        "artistName": "Test Artist",
        "albumName": "Test Album",
        "duration": 180,
        "instrumental": False,
        "plainLyrics": "Line one\nLine two\nLine three\n",
        "syncedLyrics": ""
    }


@pytest.fixture
def mock_lrclib_instrumental():
    """Mock LRCLIB API response for instrumental track"""
    return {
        "id": 789012,
        "trackName": "Instrumental Track",
        "artistName": "Composer",
        "albumName": "Soundtracks",
        "duration": 120,
        "instrumental": True,
        "plainLyrics": "",
        "syncedLyrics": ""
    }


@pytest.fixture
def mock_search_results():
    """Mock LRCLIB search API response"""
    return [
        {
            "id": 3396226,
            "trackName": "I Want to Live",
            "artistName": "Borislav Slavov",
            "albumName": "Baldur's Gate 3 (Original Game Soundtrack)",
            "duration": 233,
            "instrumental": False,
            "plainLyrics": "I feel your breath upon my neck\n",
            "syncedLyrics": "[00:17.12] I feel your breath upon my neck\n"
        }
    ]


class TestLRCLIBProvider:
    @pytest.fixture
    def provider(self, mock_logger, config):
        return LRCLIBProvider(config=config, logger=mock_logger)

    def test_init(self, provider):
        """Test initialization"""
        assert provider.duration is None
        assert provider.BASE_URL == "https://lrclib.net"

    def test_get_track_duration_success(self, provider, config_with_audio):
        """Test successful track duration extraction"""
        provider_with_audio = LRCLIBProvider(config=config_with_audio, logger=Mock())
        
        # Mock mutagen module
        mock_mutagen = MagicMock()
        mock_audio = MagicMock()
        mock_audio.info.length = 233.5
        mock_mutagen.File.return_value = mock_audio
        
        with patch.dict(sys.modules, {'mutagen': mock_mutagen}):
            duration = provider_with_audio._get_track_duration()
            assert duration == 233

    def test_get_track_duration_no_filepath(self, provider):
        """Test track duration extraction with no audio file"""
        duration = provider._get_track_duration()
        assert duration is None

    def test_get_track_duration_error(self, config_with_audio, mock_logger):
        """Test track duration extraction with error"""
        provider_with_audio = LRCLIBProvider(config=config_with_audio, logger=mock_logger)
        
        # Mock mutagen module to raise exception
        mock_mutagen = MagicMock()
        mock_mutagen.File.side_effect = Exception("File not found")
        
        with patch.dict(sys.modules, {'mutagen': mock_mutagen}):
            duration = provider_with_audio._get_track_duration()
            assert duration is None
            mock_logger.warning.assert_called_once()

    @patch("requests.get")
    def test_fetch_with_duration_success(self, mock_get, provider, mock_lrclib_response):
        """Test successful fetch with duration"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_lrclib_response)
        
        result = provider._fetch_with_duration("Borislav Slavov", "I Want to Live", "", 233)
        
        assert result is not None
        assert result["trackName"] == "I Want to Live"
        assert result["artistName"] == "Borislav Slavov"
        assert result["duration"] == 233
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "api/get" in call_args[0][0]
        assert call_args[1]["params"]["artist_name"] == "Borislav Slavov"
        assert call_args[1]["params"]["track_name"] == "I Want to Live"
        assert call_args[1]["params"]["duration"] == 233
        assert "User-Agent" in call_args[1]["headers"]

    @patch("requests.get")
    def test_fetch_with_duration_not_found(self, mock_get, provider):
        """Test fetch with duration when track not found"""
        mock_get.return_value = Mock(status_code=404)
        
        result = provider._fetch_with_duration("Unknown Artist", "Unknown Song", "", 180)
        
        assert result is None

    @patch("requests.get")
    def test_fetch_with_duration_request_error(self, mock_get, provider, mock_logger):
        """Test fetch with duration when request fails"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = provider._fetch_with_duration("Artist", "Song", "", 180)
        
        assert result is None
        mock_logger.error.assert_called_with("LRCLIB request failed: Network error")

    @patch("requests.get")
    def test_fetch_from_search_success(self, mock_get, provider, mock_search_results):
        """Test successful search"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_search_results)
        
        result = provider._fetch_from_search("Borislav Slavov", "I Want to Live")
        
        assert result is not None
        assert result["trackName"] == "I Want to Live"
        assert result["artistName"] == "Borislav Slavov"
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "api/search" in call_args[0][0]
        assert call_args[1]["params"]["track_name"] == "I Want to Live"
        assert call_args[1]["params"]["artist_name"] == "Borislav Slavov"

    @patch("requests.get")
    def test_fetch_from_search_no_results(self, mock_get, provider):
        """Test search with no results"""
        mock_get.return_value = Mock(status_code=200, json=lambda: [])
        
        result = provider._fetch_from_search("Unknown Artist", "Unknown Song")
        
        assert result is None

    @patch("requests.get")
    def test_fetch_from_search_request_error(self, mock_get, provider, mock_logger):
        """Test search when request fails"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = provider._fetch_from_search("Artist", "Song")
        
        assert result is None
        mock_logger.error.assert_called_with("LRCLIB search request failed: Network error")

    @patch.object(LRCLIBProvider, "_get_track_duration")
    @patch.object(LRCLIBProvider, "_fetch_with_duration")
    def test_fetch_data_from_source_with_duration(self, mock_fetch_duration, mock_get_duration, 
                                                  provider, mock_lrclib_response):
        """Test fetch data with duration available"""
        mock_get_duration.return_value = 233
        mock_fetch_duration.return_value = mock_lrclib_response
        
        result = provider._fetch_data_from_source("Borislav Slavov", "I Want to Live")
        
        assert result is not None
        assert result["trackName"] == "I Want to Live"
        mock_get_duration.assert_called_once()
        mock_fetch_duration.assert_called_once_with("Borislav Slavov", "I Want to Live", "", 233)

    @patch.object(LRCLIBProvider, "_get_track_duration")
    @patch.object(LRCLIBProvider, "_fetch_from_search")
    def test_fetch_data_from_source_no_duration(self, mock_fetch_search, mock_get_duration, 
                                                provider, mock_search_results):
        """Test fetch data without duration (falls back to search)"""
        mock_get_duration.return_value = None
        mock_fetch_search.return_value = mock_search_results[0]
        
        result = provider._fetch_data_from_source("Borislav Slavov", "I Want to Live")
        
        assert result is not None
        mock_fetch_search.assert_called_once_with("Borislav Slavov", "I Want to Live")

    @patch.object(LRCLIBProvider, "_get_track_duration")
    @patch.object(LRCLIBProvider, "_fetch_with_duration")
    @patch.object(LRCLIBProvider, "_fetch_from_search")
    def test_fetch_data_from_source_duration_fails_fallback_to_search(
        self, mock_fetch_search, mock_fetch_duration, mock_get_duration, 
        provider, mock_search_results
    ):
        """Test fetch data when duration fetch fails, falls back to search"""
        mock_get_duration.return_value = 233
        mock_fetch_duration.return_value = None  # Duration-based fetch fails
        mock_fetch_search.return_value = mock_search_results[0]
        
        result = provider._fetch_data_from_source("Borislav Slavov", "I Want to Live")
        
        assert result is not None
        mock_fetch_duration.assert_called_once()
        mock_fetch_search.assert_called_once()

    def test_convert_result_format_with_synced_lyrics(self, provider, mock_lrclib_response):
        """Test conversion with synced lyrics"""
        result = provider._convert_result_format(mock_lrclib_response)
        
        assert isinstance(result, LyricsData)
        assert result.source == "lrclib"
        assert len(result.segments) == 3  # Three synced lines
        
        # Check metadata
        metadata = result.metadata
        assert metadata.source == "lrclib"
        assert metadata.track_name == "I Want to Live"
        assert metadata.artist_names == "Borislav Slavov"
        assert metadata.album_name == "Baldur's Gate 3 (Original Game Soundtrack)"
        assert metadata.duration_ms == 233000
        assert metadata.is_synced is True
        assert metadata.lyrics_provider == "lrclib"
        assert metadata.lyrics_provider_id == "3396226"
        
        # Check provider metadata
        assert metadata.provider_metadata["lrclib_id"] == 3396226
        assert metadata.provider_metadata["duration"] == 233
        assert metadata.provider_metadata["instrumental"] is False
        assert metadata.provider_metadata["has_synced_lyrics"] is True
        assert metadata.provider_metadata["has_plain_lyrics"] is True
        
        # Check segments have timing
        first_segment = result.segments[0]
        assert first_segment.text == "I feel your breath upon my neck"
        assert first_segment.start_time == pytest.approx(17.12, rel=0.01)
        assert first_segment.end_time == pytest.approx(22.45, rel=0.01)
        assert len(first_segment.words) > 0
        
        # Check words have timing
        first_word = first_segment.words[0]
        assert first_word.text == "I"
        assert first_word.start_time is not None
        assert first_word.end_time is not None

    def test_convert_result_format_plain_only(self, provider, mock_lrclib_plain_only):
        """Test conversion with only plain lyrics"""
        result = provider._convert_result_format(mock_lrclib_plain_only)
        
        assert isinstance(result, LyricsData)
        assert result.source == "lrclib"
        assert len(result.segments) == 3  # Three plain lines
        
        # Check metadata
        metadata = result.metadata
        assert metadata.is_synced is False
        assert metadata.provider_metadata["has_synced_lyrics"] is False
        assert metadata.provider_metadata["has_plain_lyrics"] is True
        
        # Check segments don't have timing (None instead of 0.0)
        first_segment = result.segments[0]
        assert first_segment.text == "Line one"
        assert first_segment.start_time is None
        assert first_segment.end_time is None

    def test_convert_result_format_instrumental(self, provider, mock_lrclib_instrumental):
        """Test conversion of instrumental track"""
        result = provider._convert_result_format(mock_lrclib_instrumental)
        
        assert isinstance(result, LyricsData)
        assert result.source == "lrclib"
        assert len(result.segments) == 0  # No lyrics for instrumental
        
        # Check metadata
        metadata = result.metadata
        assert metadata.provider_metadata["instrumental"] is True
        assert metadata.provider_metadata["has_synced_lyrics"] is False
        assert metadata.provider_metadata["has_plain_lyrics"] is False

    def test_parse_synced_lyrics(self, provider):
        """Test parsing of LRC format synced lyrics"""
        synced_lyrics = """[00:17.12] I feel your breath upon my neck
[00:22.45] A kiss goodbye
[00:27.80] No second chance
[03:20.31] The clock won't stop and this is what we get
"""
        
        segments = provider._parse_synced_lyrics(synced_lyrics)
        
        assert len(segments) == 4
        
        # Check first segment
        first = segments[0]
        assert first.text == "I feel your breath upon my neck"
        assert first.start_time == pytest.approx(17.12, rel=0.01)
        assert first.end_time == pytest.approx(22.45, rel=0.01)
        
        # Check second segment
        second = segments[1]
        assert second.text == "A kiss goodbye"
        assert second.start_time == pytest.approx(22.45, rel=0.01)
        assert second.end_time == pytest.approx(27.80, rel=0.01)
        
        # Check last segment (should add 3 seconds as default end time)
        last = segments[3]
        assert last.text == "The clock won't stop and this is what we get"
        assert last.start_time == pytest.approx(200.31, rel=0.01)
        assert last.end_time == pytest.approx(203.31, rel=0.01)

    def test_parse_synced_lyrics_with_empty_lines(self, provider):
        """Test parsing synced lyrics with empty lines"""
        synced_lyrics = """[00:17.12] First line
[00:22.45] 
[00:27.80] Third line
"""
        
        segments = provider._parse_synced_lyrics(synced_lyrics)
        
        # Empty lines should be skipped
        assert len(segments) == 2
        assert segments[0].text == "First line"
        assert segments[1].text == "Third line"

    def test_parse_synced_lyrics_invalid_format(self, provider):
        """Test parsing synced lyrics with invalid format lines"""
        synced_lyrics = """[00:17.12] Valid line
This is not LRC format
[00:27.80] Another valid line
"""
        
        segments = provider._parse_synced_lyrics(synced_lyrics)
        
        # Invalid lines should be skipped
        assert len(segments) == 2
        assert segments[0].text == "Valid line"
        assert segments[1].text == "Another valid line"

    def test_convert_result_format_missing_optional_fields(self, provider):
        """Test conversion with missing optional fields"""
        minimal_data = {
            "id": 123,
            "trackName": "Test Song",
            "artistName": "Test Artist",
            "instrumental": False,
            "plainLyrics": "Test lyrics\n",
            "syncedLyrics": ""
        }
        
        result = provider._convert_result_format(minimal_data)
        
        assert isinstance(result, LyricsData)
        assert result.metadata.album_name is None
        assert result.metadata.duration_ms is None

    def test_get_name(self, provider):
        """Test getting provider name"""
        assert provider.get_name() == "LRCLIB"

