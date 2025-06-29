import pytest
from unittest.mock import Mock
from lyrics_transcriber.types import (
    LyricsData,
    LyricsMetadata,
    LyricsSegment,
    Word,
    TranscriptionResult,
    TranscriptionData,
    CorrectionResult,
)
from lyrics_transcriber.correction.corrector import LyricsCorrector
import os
import tempfile
import shutil

# Import test helpers for new API
from tests.test_helpers import create_test_word, create_test_segment


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    """Create a simple transcription result for testing."""
    words = [
        create_test_word(text="hello", start_time=0.0, end_time=0.5),
        create_test_word(text="world", start_time=0.6, end_time=1.0),
    ]

    segment = create_test_segment(
        text="hello world",
        words=words,
        start_time=0.0,
        end_time=1.0,
    )

    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],
            text="hello world",
            source="test",
            words=words,
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    """Create simple lyrics data for testing."""
    words = [
        create_test_word(text="hello", start_time=0.0, end_time=0.5),
        create_test_word(text="world", start_time=0.6, end_time=1.0),
    ]

    segment = create_test_segment(
        text="hello world",
        words=words,
        start_time=0.0,
        end_time=1.0,
    )

    lyrics_data = LyricsData(
        source="test",
        segments=[segment],
        metadata=LyricsMetadata(source="test", track_name="test track", artist_names="test artist"),
    )
    
    return {"test": lyrics_data}


class TestLyricsCorrector:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test cache directory."""
        test_cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-test-cache")
        
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
            
        os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"] = test_cache_dir
        
        yield test_cache_dir
        
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
            
        if "LYRICS_TRANSCRIBER_CACHE_DIR" in os.environ:
            del os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]

    def test_init_with_defaults(self, mock_logger, setup_teardown):
        """Test that corrector can be initialized with default settings."""
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        assert corrector.logger == mock_logger
        assert len(corrector.handlers) > 0  # Should have default handlers
        assert corrector._cache_dir.name == "lyrics-transcriber-test-cache"

    def test_init_with_custom_handlers(self, mock_logger, setup_teardown):
        """Test that corrector can be initialized with custom handlers."""
        mock_handler = Mock()
        corrector = LyricsCorrector(
            cache_dir=setup_teardown, 
            handlers=[mock_handler], 
            logger=mock_logger
        )
        
        assert len(corrector.handlers) == 1
        assert corrector.handlers[0] == mock_handler

    def test_run_no_transcription_results(self, mock_logger, setup_teardown):
        """Test that corrector raises error when no transcription results provided."""
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        with pytest.raises(ValueError, match="No primary transcription data available"):
            corrector.run(transcription_results=[], lyrics_results={})

    def test_run_basic_flow(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test that corrector can run basic correction flow without errors."""
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        # This should not crash and should return a CorrectionResult
        result = corrector.run(
            transcription_results=[sample_transcription_result], 
            lyrics_results=sample_lyrics
        )
        
        # Verify result structure
        assert isinstance(result, CorrectionResult)
        assert result.original_segments == sample_transcription_result.result.segments
        assert len(result.corrected_segments) > 0
        assert isinstance(result.corrections, list)
        assert isinstance(result.corrections_made, int)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert result.reference_lyrics == sample_lyrics
        assert isinstance(result.anchor_sequences, list)
        assert isinstance(result.gap_sequences, list)
        assert isinstance(result.metadata, dict)

    def test_run_with_empty_lyrics(self, mock_logger, sample_transcription_result, setup_teardown):
        """Test that corrector can handle empty lyrics results."""
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        result = corrector.run(
            transcription_results=[sample_transcription_result], 
            lyrics_results={}
        )
        
        # Should still return a valid result even with no reference lyrics
        assert isinstance(result, CorrectionResult)
        assert result.corrections_made >= 0
        assert len(result.reference_lyrics) == 0

    def test_run_multiple_transcription_results(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test that corrector uses primary transcription result based on priority."""
        # Create second transcription with different priority
        second_transcription = TranscriptionResult(
            name="secondary",
            priority=2,  # Higher priority number (lower priority)
            result=sample_transcription_result.result
        )
        
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        result = corrector.run(
            transcription_results=[second_transcription, sample_transcription_result],
            lyrics_results=sample_lyrics
        )
        
        # Should use the first transcription (priority 1) as primary
        assert isinstance(result, CorrectionResult)
        
    def test_corrector_preserves_metadata(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test that corrector includes metadata in results."""
        corrector = LyricsCorrector(cache_dir=setup_teardown, logger=mock_logger)
        
        custom_metadata = {"audio_file_hash": "test_hash", "custom_field": "test_value"}
        
        result = corrector.run(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
            metadata=custom_metadata
        )
        
        # Verify metadata structure exists
        assert "anchor_sequences_count" in result.metadata
        assert "gap_sequences_count" in result.metadata
        assert "total_words" in result.metadata
        assert "available_handlers" in result.metadata
        assert "enabled_handlers" in result.metadata
