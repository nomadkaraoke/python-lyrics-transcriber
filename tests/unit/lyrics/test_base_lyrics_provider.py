import pytest
import os


from lyrics_transcriber.types import (
    LyricsData,
    LyricsMetadata,
    LyricsSegment,
    Word,
)

from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig
from tests.test_helpers import create_test_word, create_test_segment


class MockLyricsProvider(BaseLyricsProvider):
    """Mock implementation of BaseLyricsProvider for testing"""

    def _fetch_data_from_source(self, artist, title):
        return {"test": "data"}

    def _convert_result_format(self, raw_data):
        return LyricsData(
            source="test",
            segments=[],
            metadata=LyricsMetadata(source="test", track_name="Test Track", artist_names="Test Artist"),
        )


class FailingMockProvider(BaseLyricsProvider):
    """Mock provider that returns None for testing failure cases"""

    def _fetch_data_from_source(self, artist, title):
        return None

    def _convert_result_format(self, raw_data):
        return None


@pytest.fixture
def test_provider(tmp_path):
    config = LyricsProviderConfig(cache_dir=str(tmp_path), audio_filepath="test.mp3")
    return MockLyricsProvider(config=config)


@pytest.fixture
def failing_provider(tmp_path):
    config = LyricsProviderConfig(cache_dir=str(tmp_path), audio_filepath="test.mp3")
    return FailingMockProvider(config=config)


def test_word_to_dict():
    """Test Word.to_dict() method"""
    # Test with confidence
    word = create_test_word(text="test", start_time=1.0, end_time=2.0, confidence=0.9)
    expected = {"id": word.id, "text": "test", "start_time": 1.0, "end_time": 2.0, "confidence": 0.9, "created_during_correction": False}
    assert word.to_dict() == expected

    # Test without confidence
    word = create_test_word(text="test", start_time=1.0, end_time=2.0)
    expected = {"id": word.id, "text": "test", "start_time": 1.0, "end_time": 2.0, "created_during_correction": False}
    assert word.to_dict() == expected


def test_lyrics_segment_to_dict():
    """Test LyricsSegment.to_dict() method"""
    # Create test words
    words = [
        create_test_word(text="hello", start_time=1.0, end_time=1.5), 
        create_test_word(text="world", start_time=1.5, end_time=2.0)
    ]

    # Create a lyrics segment
    segment = create_test_segment(text="hello world", words=words, start_time=1.0, end_time=2.0)

    # Test the to_dict method
    expected = {
        "id": segment.id,
        "text": "hello world",
        "words": [
            {"id": words[0].id, "text": "hello", "start_time": 1.0, "end_time": 1.5, "created_during_correction": False}, 
            {"id": words[1].id, "text": "world", "start_time": 1.5, "end_time": 2.0, "created_during_correction": False}
        ],
        "start_time": 1.0,
        "end_time": 2.0,
    }

    assert segment.to_dict() == expected


def test_fetch_lyrics_with_cache(test_provider, tmp_path):
    """Test fetch_lyrics with caching enabled"""
    result = test_provider.fetch_lyrics("Test Artist", "Test Song")
    assert result is not None

    # Verify cache files were created (now uses artist/title hash instead of file hash)
    cache_key = test_provider._get_artist_title_hash("Test Artist", "Test Song")
    raw_cache_path = test_provider._get_cache_path(cache_key, "raw")
    converted_cache_path = test_provider._get_cache_path(cache_key, "converted")

    assert os.path.exists(raw_cache_path)
    assert os.path.exists(converted_cache_path)

    # Test loading from cache
    result2 = test_provider.fetch_lyrics("Test Artist", "Test Song")
    assert result2 is not None


def test_fetch_lyrics_without_cache():
    """Test fetch_lyrics with caching disabled"""
    provider = MockLyricsProvider(config=LyricsProviderConfig())
    result = provider.fetch_lyrics("Test Artist", "Test Song")
    assert result is not None


def test_cache_operations(test_provider, tmp_path):
    """Test cache-related operations"""
    test_data = {"test": "data"}
    cache_path = os.path.join(tmp_path, "test_cache.json")

    # Test save to cache
    test_provider._save_to_cache(cache_path, test_data)
    assert os.path.exists(cache_path)

    # Test load from cache
    loaded_data = test_provider._load_from_cache(cache_path)
    assert loaded_data == test_data

    # Test load from non-existent file
    assert test_provider._load_from_cache("nonexistent.json") is None

    # Test load from corrupted file
    with open(cache_path, "w") as f:
        f.write("invalid json")
    assert test_provider._load_from_cache(cache_path) is None


def test_get_name(test_provider):
    """Test get_name method"""
    assert test_provider.get_name() == "MockLyrics"


def test_get_artist_title_hash(test_provider):
    """Test _get_artist_title_hash method"""
    hash1 = test_provider._get_artist_title_hash("Artist", "Title")
    hash2 = test_provider._get_artist_title_hash("ARTIST", "TITLE")
    assert hash1 == hash2  # Should be case-insensitive


def test_fetch_lyrics_returns_none_when_no_data(failing_provider, tmp_path):
    """Test fetch_lyrics returns None when no data is found"""
    # Create test audio file first
    test_file = tmp_path / "test.mp3"
    test_file.write_bytes(b"test audio data")

    # Update the provider's audio filepath
    failing_provider.audio_filepath = str(test_file)

    result = failing_provider.fetch_lyrics("Test Artist", "Test Song")
    assert result is None


def test_fetch_and_convert_returns_none_when_no_data(failing_provider):
    """Test _fetch_and_convert_result returns None when no data is found"""
    result = failing_provider._fetch_and_convert_result("Test Artist", "Test Song")
    assert result is None


def test_abstract_methods():
    """Test that abstract methods raise NotImplementedError"""

    class AbstractProvider(BaseLyricsProvider):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AbstractProvider(config=LyricsProviderConfig())
