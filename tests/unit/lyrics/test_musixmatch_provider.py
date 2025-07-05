import pytest
from unittest.mock import Mock, patch
import requests
from lyrics_transcriber.lyrics.musixmatch import MusixmatchProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config_with_rapidapi_key():
    return LyricsProviderConfig(rapidapi_key="test_rapidapi_key")


@pytest.fixture
def config_without_rapidapi_key():
    return LyricsProviderConfig(rapidapi_key=None)


@pytest.fixture
def mock_musixmatch_response():
    """Mock the complex Musixmatch API response structure."""
    return {
        "message": {
            "body": {
                "macro_calls": {
                    "matcher.track.get": {
                        "message": {
                            "body": {
                                "track": {
                                    "track_id": 108624154,
                                    "track_name": "Waterloo",
                                    "track_length": 292,
                                    "track_rating": 62,
                                    "track_share_url": "https://www.musixmatch.com/lyrics/ABBA/Waterloo",
                                    "track_edit_url": "https://www.musixmatch.com/lyrics/ABBA/Waterloo/edit",
                                    "track_spotify_id": "6OiYEtoP7atAt33TbSmegi",
                                    "track_isrc": "USA561227020",
                                    "artist_id": 55498249,
                                    "artist_name": "ABBA",
                                    "album_id": 23111800,
                                    "album_name": "The Very Best of Abba",
                                    "explicit": 0,
                                    "first_release_date": "1974-01-01T00:00:00Z",
                                    "num_favourite": 737,
                                    "has_lyrics": 1,
                                    "has_lyrics_crowd": 0,
                                    "has_richsync": 0,
                                    "has_subtitles": 0,
                                    "has_track_structure": 0,
                                    "instrumental": 0,
                                    "restricted": 0,
                                    "updated_time": "2024-03-16T13:00:19Z"
                                }
                            }
                        }
                    },
                    "track.lyrics.get": {
                        "message": {
                            "body": {
                                "lyrics": {
                                    "lyrics_id": 30294448,
                                    "lyrics_body": "My, my\\nAt Waterloo, Napoleon did surrender\\nOh, yeah\\nAnd I have met my destiny in quite a similar way\\n\\nThe history book on the shelf\\nIs always repeating itself\\n\\nWaterloo\\nI was defeated, you won the war\\nWaterloo\\nPromise to love you forevermore",
                                    "lyrics_language": "en",
                                    "lyrics_language_description": "English",
                                    "lyrics_copyright": "Writer(s): Benny Goran Bror Andersson, Bjoern K. Ulvaeus",
                                    "explicit": 0,
                                    "instrumental": 0,
                                    "restricted": 0,
                                    "can_edit": 0,
                                    "locked": 0,
                                    "published_status": 1,
                                    "verified": 0,
                                    "updated_time": "2024-05-26T13:26:11Z"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_musixmatch_minimal_response():
    """Mock minimal Musixmatch API response with required fields only."""
    return {
        "message": {
            "body": {
                "macro_calls": {
                    "matcher.track.get": {
                        "message": {
                            "body": {
                                "track": {
                                    "track_id": 12345,
                                    "track_name": "Test Song",
                                    "artist_name": "Test Artist"
                                }
                            }
                        }
                    },
                    "track.lyrics.get": {
                        "message": {
                            "body": {
                                "lyrics": {
                                    "lyrics_id": 54321,
                                    "lyrics_body": "Test lyrics content"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_musixmatch_no_lyrics_response():
    """Mock Musixmatch API response without lyrics."""
    return {
        "message": {
            "body": {
                "macro_calls": {
                    "matcher.track.get": {
                        "message": {
                            "body": {
                                "track": {
                                    "track_id": 12345,
                                    "track_name": "Test Song",
                                    "artist_name": "Test Artist"
                                }
                            }
                        }
                    },
                    "track.lyrics.get": {
                        "message": {
                            "body": {}  # No lyrics field
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_musixmatch_invalid_response():
    """Mock invalid Musixmatch API response."""
    return {
        "message": {
            "body": {}  # No macro_calls field
        }
    }


class TestMusixmatchProvider:
    @pytest.fixture
    def provider(self, mock_logger, config_with_rapidapi_key):
        return MusixmatchProvider(config=config_with_rapidapi_key, logger=mock_logger)

    def test_init_with_rapidapi_key(self, provider):
        """Test initialization with RapidAPI key"""
        assert provider.rapidapi_key == "test_rapidapi_key"

    def test_init_without_rapidapi_key(self, mock_logger, config_without_rapidapi_key):
        """Test initialization without RapidAPI key"""
        provider = MusixmatchProvider(config=config_without_rapidapi_key, logger=mock_logger)
        assert provider.rapidapi_key is None

    @patch("requests.get")
    def test_fetch_data_from_source_success(self, mock_get, provider, mock_musixmatch_response):
        """Test successful data fetch from Musixmatch"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_musixmatch_response)
        
        result = provider._fetch_data_from_source("ABBA", "Waterloo")
        
        assert result == mock_musixmatch_response
        provider.logger.info.assert_any_call("Successfully fetched lyrics from Musixmatch")
        
        # Verify the API call was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "https://musixmatch-song-lyrics-api.p.rapidapi.com/lyrics/ABBA/Waterloo/" in call_args[0][0]
        assert call_args[1]["headers"]["x-rapidapi-key"] == "test_rapidapi_key"
        assert call_args[1]["headers"]["x-rapidapi-host"] == "musixmatch-song-lyrics-api.p.rapidapi.com"

    def test_fetch_data_from_source_no_rapidapi_key(self, mock_logger, config_without_rapidapi_key):
        """Test fetch attempt without RapidAPI key"""
        provider = MusixmatchProvider(config=config_without_rapidapi_key, logger=mock_logger)
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No RapidAPI key provided for Musixmatch")

    @patch("requests.get")
    def test_fetch_data_from_source_invalid_response(self, mock_get, provider, mock_musixmatch_invalid_response):
        """Test fetch with invalid response structure"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_musixmatch_invalid_response)
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        provider.logger.warning.assert_called_with("Invalid response structure from Musixmatch API")

    @patch("requests.get")
    def test_fetch_data_from_source_no_lyrics(self, mock_get, provider, mock_musixmatch_no_lyrics_response):
        """Test fetch with no lyrics in response"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_musixmatch_no_lyrics_response)
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        provider.logger.warning.assert_called_with("No lyrics found in Musixmatch response")

    @patch("requests.get")
    def test_fetch_data_from_source_request_error(self, mock_get, provider):
        """Test fetch with request error"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        provider.logger.error.assert_called_with("Musixmatch API request failed: Network error")

    @patch("requests.get")
    def test_fetch_data_from_source_http_error(self, mock_get, provider):
        """Test fetch with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_response
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        provider.logger.error.assert_called_with("Musixmatch API request failed: 403 Forbidden")

    @patch("requests.get")
    def test_fetch_data_from_source_json_error(self, mock_get, provider):
        """Test fetch with JSON parsing error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        provider.logger.error.assert_called_with("Error fetching from Musixmatch: Invalid JSON")

    def test_convert_result_format_success(self, provider, mock_musixmatch_response):
        """Test successful conversion of Musixmatch response to standardized format"""
        result = provider._convert_result_format(mock_musixmatch_response)
        
        assert isinstance(result, LyricsData)
        assert result.source == "musixmatch"
        assert len(result.segments) > 0
        
        # Check that lyrics text was processed correctly (escaped newlines converted)
        full_text = result.get_full_text()
        assert "My, my" in full_text
        assert "At Waterloo, Napoleon did surrender" in full_text
        assert "\\n" not in full_text  # Should be converted to actual newlines
        
        # Verify metadata
        metadata = result.metadata
        assert metadata.source == "musixmatch"
        assert metadata.track_name == "Waterloo"
        assert metadata.artist_names == "ABBA"
        assert metadata.album_name == "The Very Best of Abba"
        assert metadata.duration_ms == 292000  # 292 seconds * 1000
        assert metadata.explicit is False
        assert metadata.language == "en"
        assert metadata.is_synced is False
        assert metadata.lyrics_provider == "musixmatch"
        assert metadata.lyrics_provider_id == "30294448"
        
        # Verify provider-specific metadata
        provider_metadata = metadata.provider_metadata
        assert provider_metadata["musixmatch_track_id"] == 108624154
        assert provider_metadata["musixmatch_lyrics_id"] == 30294448
        assert provider_metadata["album_id"] == 23111800
        assert provider_metadata["artist_id"] == 55498249
        assert provider_metadata["track_share_url"] == "https://www.musixmatch.com/lyrics/ABBA/Waterloo"
        assert provider_metadata["track_edit_url"] == "https://www.musixmatch.com/lyrics/ABBA/Waterloo/edit"
        assert provider_metadata["lyrics_language"] == "en"
        assert provider_metadata["lyrics_language_description"] == "English"
        assert provider_metadata["lyrics_copyright"] == "Writer(s): Benny Goran Bror Andersson, Bjoern K. Ulvaeus"
        assert provider_metadata["track_rating"] == 62
        assert provider_metadata["num_favourite"] == 737
        assert provider_metadata["first_release_date"] == "1974-01-01T00:00:00Z"
        assert provider_metadata["spotify_id"] == "6OiYEtoP7atAt33TbSmegi"
        assert provider_metadata["isrc"] == "USA561227020"
        assert provider_metadata["api_source"] == "rapidapi_musixmatch"

    def test_convert_result_format_minimal(self, provider, mock_musixmatch_minimal_response):
        """Test conversion with minimal response data"""
        result = provider._convert_result_format(mock_musixmatch_minimal_response)
        
        assert isinstance(result, LyricsData)
        assert result.source == "musixmatch"
        assert result.get_full_text() == "Test lyrics content"
        
        # Verify metadata with minimal fields
        metadata = result.metadata
        assert metadata.source == "musixmatch"
        assert metadata.track_name == "Test Song"
        assert metadata.artist_names == "Test Artist"
        assert metadata.album_name == ""  # Default empty string for missing fields
        assert metadata.duration_ms is None  # Missing track_length
        assert metadata.explicit is False  # Default for missing explicit field
        assert metadata.lyrics_provider_id == "54321"

    def test_convert_result_format_error_handling(self, provider):
        """Test conversion with malformed response data"""
        malformed_response = {"invalid": "structure"}
        
        result = provider._convert_result_format(malformed_response)
        
        assert isinstance(result, LyricsData)
        assert result.source == "musixmatch"
        assert len(result.segments) == 0  # Empty segments due to error
        assert result.metadata.track_name == ""
        assert result.metadata.artist_names == ""
        # The malformed response doesn't cause an exception, it just results in empty data
        # The provider_metadata should still have the api_source
        assert result.metadata.provider_metadata.get("api_source") == "rapidapi_musixmatch"

    def test_convert_result_format_exception_handling(self, provider):
        """Test conversion with data that actually causes an exception"""
        # Create a response that will cause an exception when processing
        # Mock the _create_segments_with_words method to raise an exception
        with patch.object(provider, '_create_segments_with_words', side_effect=Exception("Segment creation failed")):
            valid_response = {
                "message": {
                    "body": {
                        "macro_calls": {
                            "matcher.track.get": {
                                "message": {
                                    "body": {
                                        "track": {
                                            "track_id": 12345,
                                            "track_name": "Test Song",
                                            "artist_name": "Test Artist"
                                        }
                                    }
                                }
                            },
                            "track.lyrics.get": {
                                "message": {
                                    "body": {
                                        "lyrics": {
                                            "lyrics_id": 54321,
                                            "lyrics_body": "Test lyrics content"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            result = provider._convert_result_format(valid_response)
            
            assert isinstance(result, LyricsData)
            assert result.source == "musixmatch"
            assert len(result.segments) == 0  # Empty segments due to error
            assert result.metadata.track_name == ""
            assert result.metadata.artist_names == ""
            assert "conversion_error" in result.metadata.provider_metadata
            assert result.metadata.provider_metadata["conversion_error"] == "Segment creation failed"
            provider.logger.error.assert_called_once()

    def test_clean_lyrics_basic(self, provider):
        """Test basic lyrics cleaning functionality"""
        raw_lyrics = "Line 1\\nLine 2\\nLine 3"
        cleaned = provider._clean_lyrics(raw_lyrics)
        
        assert cleaned == "Line 1\nLine 2\nLine 3"
        assert "\\n" not in cleaned

    def test_clean_lyrics_html_tags(self, provider):
        """Test HTML tag removal"""
        raw_lyrics = "Line 1<br>Line 2<span>Line 3</span>"
        cleaned = provider._clean_lyrics(raw_lyrics)
        
        assert "<br>" not in cleaned
        assert "<span>" not in cleaned
        assert "</span>" not in cleaned

    def test_clean_lyrics_multiple_newlines(self, provider):
        """Test multiple newline cleanup"""
        raw_lyrics = "Line 1\\n\\n\\n\\nLine 2\\n\\n\\nLine 3"
        cleaned = provider._clean_lyrics(raw_lyrics)
        
        # Should reduce multiple newlines to double newlines
        assert "Line 1\n\nLine 2\n\nLine 3" == cleaned

    def test_clean_lyrics_whitespace(self, provider):
        """Test whitespace cleanup"""
        raw_lyrics = "  \\n  Line 1  \\n  Line 2  \\n  "
        cleaned = provider._clean_lyrics(raw_lyrics)
        
        assert cleaned == "Line 1\nLine 2"
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")

    def test_clean_lyrics_none_input(self, provider):
        """Test handling of None input"""
        result = provider._clean_lyrics(None)
        assert result == ""
        provider.logger.warning.assert_called_once()

    def test_clean_lyrics_non_string_input(self, provider):
        """Test handling of non-string input"""
        result = provider._clean_lyrics(123)
        assert result == "123"
        provider.logger.warning.assert_called_once()

    def test_clean_lyrics_conversion_error(self, provider):
        """Test handling of conversion errors"""
        # Create an object that can't be converted to string
        class UnconvertibleObject:
            def __str__(self):
                raise Exception("Conversion error")
        
        mock_obj = UnconvertibleObject()
        
        result = provider._clean_lyrics(mock_obj)
        assert result == ""
        provider.logger.error.assert_called_once()

    def test_get_name(self, provider):
        """Test that the provider returns correct name"""
        assert provider.get_name() == "Musixmatch"

    @patch("requests.get")
    def test_fetch_lyrics_integration(self, mock_get, provider, mock_musixmatch_response):
        """Test the full fetch_lyrics workflow"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_musixmatch_response)
        
        result = provider.fetch_lyrics("ABBA", "Waterloo")
        
        assert result is not None
        assert isinstance(result, LyricsData)
        assert result.source == "musixmatch"
        assert "Waterloo" in result.get_full_text()
        assert result.metadata.track_name == "Waterloo"
        assert result.metadata.artist_names == "ABBA"

    @patch("requests.get")
    def test_fetch_lyrics_no_results(self, mock_get, provider, mock_musixmatch_invalid_response):
        """Test fetch_lyrics with no results"""
        mock_get.return_value = Mock(status_code=200, json=lambda: mock_musixmatch_invalid_response)
        
        result = provider.fetch_lyrics("Artist", "Title")
        
        assert result is None

    @patch("requests.get")
    def test_fetch_lyrics_api_error(self, mock_get, provider):
        """Test fetch_lyrics with API error"""
        mock_get.side_effect = requests.RequestException("API Error")
        
        result = provider.fetch_lyrics("Artist", "Title")
        
        assert result is None 