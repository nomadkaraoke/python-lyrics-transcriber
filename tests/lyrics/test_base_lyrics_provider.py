import pytest
import os


from lyrics_transcriber.types import (
    LyricsData,
    LyricsMetadata,
    LyricsSegment,
    Word,
)

from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig


class MockLyricsProvider(BaseLyricsProvider):
    """Mock implementation of BaseLyricsProvider for testing"""

    def _fetch_data_from_source(self, artist, title):
        return {"test": "data"}

    def _convert_result_format(self, raw_data):
        return LyricsData(
            source="test",
            lyrics="Test lyrics",
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
    word = Word(text="test", start_time=1.0, end_time=2.0, confidence=0.9)
    assert word.to_dict() == {"text": "test", "start_time": 1.0, "end_time": 2.0, "confidence": 0.9}

    # Test without confidence
    word = Word(text="test", start_time=1.0, end_time=2.0)
    assert word.to_dict() == {"text": "test", "start_time": 1.0, "end_time": 2.0}


def test_lyrics_segment_to_dict():
    """Test LyricsSegment.to_dict() method"""
    # Create test words
    words = [Word(text="hello", start_time=1.0, end_time=1.5), Word(text="world", start_time=1.5, end_time=2.0)]

    # Create a lyrics segment
    segment = LyricsSegment(text="hello world", words=words, start_time=1.0, end_time=2.0)

    # Test the to_dict method
    expected = {
        "text": "hello world",
        "words": [{"text": "hello", "start_time": 1.0, "end_time": 1.5}, {"text": "world", "start_time": 1.5, "end_time": 2.0}],
        "start_time": 1.0,
        "end_time": 2.0,
    }

    assert segment.to_dict() == expected


def test_fetch_lyrics_with_cache(test_provider, tmp_path):
    """Test fetch_lyrics with caching enabled"""
    # Create test audio file
    with open("test.mp3", "wb") as f:
        f.write(b"test audio data")

    result = test_provider.fetch_lyrics("Test Artist", "Test Song")
    assert result is not None

    # Verify cache files were created
    file_hash = test_provider._get_file_hash("test.mp3")
    raw_cache_path = test_provider._get_cache_path(file_hash, "raw")
    converted_cache_path = test_provider._get_cache_path(file_hash, "converted")

    assert os.path.exists(raw_cache_path)
    assert os.path.exists(converted_cache_path)

    # Test loading from cache
    result2 = test_provider.fetch_lyrics("Test Artist", "Test Song")
    assert result2 is not None

    # Cleanup
    os.remove("test.mp3")


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
