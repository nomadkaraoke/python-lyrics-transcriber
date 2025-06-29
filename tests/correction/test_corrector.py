from typing import List, Dict, Any, Tuple, Optional
import pytest
from unittest.mock import Mock
from lyrics_transcriber.types import (
    LyricsData,
    LyricsMetadata,
    LyricsSegment,
    Word,
    TranscriptionResult,
    TranscriptionData,
    WordCorrection,
    GapSequence,
)
from lyrics_transcriber.correction.corrector import LyricsCorrector
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
import os
import tempfile
import shutil

# Import test helpers for new API
from tests.test_helpers import create_handler_test_data, create_test_word, create_word_map


class MockHandler(GapCorrectionHandler):
    """Mock handler for testing."""

    def __init__(self, should_handle=True, corrections=None):
        self.should_handle = should_handle
        self.corrections = corrections or []
        self.can_handle_called = False
        self.handle_called = False

    def can_handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        self.can_handle_called = True
        return self.should_handle, data or {}

    def handle(self, gap: GapSequence, data: Optional[Dict[str, Any]] = None) -> List[WordCorrection]:
        self.handle_called = True
        return self.corrections


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    words = [
        create_test_word(text="hello", start_time=0.0, end_time=0.5),
        create_test_word(text="wurld", start_time=0.6, end_time=1.0),  # Intentionally misspelled
        create_test_word(text="test", start_time=1.1, end_time=1.5),
        create_test_word(text="lyrics", start_time=1.6, end_time=2.0),
    ]

    segment = LyricsSegment(
        id="segment_1",
        text="hello wurld test lyrics",
        words=words,
        start_time=0.0,
        end_time=2.0,
    )

    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],
            text="hello wurld test lyrics",
            source="test",
            words=words,
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    words = [
        create_test_word(text="hello", start_time=0.0, end_time=0.5),
        create_test_word(text="world", start_time=0.6, end_time=1.0),  # Correct spelling
        create_test_word(text="test", start_time=1.1, end_time=1.5),
        create_test_word(text="lyrics", start_time=1.6, end_time=2.0),
    ]

    segment = LyricsSegment(
        id="segment_1",
        text="hello world test lyrics",  # Correct spelling
        words=words,
        start_time=0.0,
        end_time=2.0,
    )

    lyrics_data = LyricsData(
        source="test",
        segments=[segment],
        metadata=LyricsMetadata(source="genius", track_name="test track", artist_names="test artist"),
    )
    
    # Return as dictionary with source as key
    return {"test": lyrics_data}


@pytest.fixture
def mock_anchor_finder():
    finder = Mock()
    
    # Create test words for the gap
    transcribed_word = create_test_word(text="wurld", start_time=0.6, end_time=1.0)
    reference_word = create_test_word(text="world", start_time=0.6, end_time=1.0)
    
    # Create gap sequence that covers just the "wurld" word
    gap = GapSequence(
        id="gap_1",
        transcribed_word_ids=[transcribed_word.id],
        transcription_position=1,
        preceding_anchor_id=None,
        following_anchor_id=None,
        reference_word_ids={"test": [reference_word.id]},
    )
    
    # Create word map for the gap
    word_map = create_word_map([transcribed_word, reference_word])
    
    finder.find_anchors.return_value = []
    finder.find_gaps.return_value = [gap]
    finder.word_map = word_map  # Store word map for access by tests
    return finder


class TestLyricsCorrector:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clean up the test cache directory before and after each test."""
        # Use a test-specific cache directory
        test_cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-test-cache")

        # Clean up before test
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)

        # Set environment variable
        os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"] = test_cache_dir

        yield test_cache_dir

        # Clean up after test
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)

        # Clean up environment variable
        del os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]

    @pytest.fixture
    def corrector(self, mock_logger, mock_anchor_finder, setup_teardown):
        return LyricsCorrector(logger=mock_logger, anchor_finder=mock_anchor_finder, cache_dir=setup_teardown)

    def test_run_no_transcription_results(self, corrector):
        with pytest.raises(ValueError, match="No primary transcription data available"):
            corrector.run(transcription_results=[], lyrics_results=[])

    def test_run_full_flow(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        # Create test words for the gap
        transcribed_word = create_test_word(text="wurld", start_time=0.6, end_time=1.0)
        reference_word = create_test_word(text="world", start_time=0.6, end_time=1.0)
        
        # Create a gap sequence that covers just the "wurld" word
        gap = GapSequence(
            id="gap_1",
            transcribed_word_ids=[transcribed_word.id],
            transcription_position=1,
            preceding_anchor_id=None,
            following_anchor_id=None,
            reference_word_ids={"test": [reference_word.id]},
        )
        
        # Create word map
        word_map = create_word_map([transcribed_word, reference_word])
        
        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # Create a mock handler that will correct "wurld" to "world"
        correction = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            segment_index=0,
            original_position=1,
            confidence=1.0,
            source="test",
            reason="Test correction",
            alternatives={},
        )
        mock_handler = MockHandler(should_handle=True, corrections=[correction])

        # Create corrector with our mock handler
        corrector = LyricsCorrector(handlers=[mock_handler], logger=mock_logger, anchor_finder=mock_finder, cache_dir=setup_teardown)

        # Run correction with sample data
        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify handler was called
        assert mock_handler.can_handle_called
        assert mock_handler.handle_called

        # Verify correction was applied
        assert "world" in result.corrected_text
        assert "wurld" not in result.corrected_text
        assert len(result.corrections) == 1
        assert result.corrections[0] == correction
        assert result.corrections_made == 1
        assert result.confidence < 1.0  # Should be less than 1 since we made a correction

    def test_run_with_error(self, mock_logger, mock_anchor_finder, sample_transcription_result, sample_lyrics, setup_teardown):
        # Create a handler that raises an exception
        failing_handler = Mock(spec=GapCorrectionHandler)
        failing_handler.can_handle.side_effect = Exception("Test error")

        corrector = LyricsCorrector(
            handlers=[failing_handler], logger=mock_logger, anchor_finder=mock_anchor_finder, cache_dir=setup_teardown
        )

        # Run correction
        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify fallback behavior
        assert result.corrected_text == "hello wurld test lyrics\n"
        assert len(result.corrected_segments) == 1
        assert result.corrections == []
        assert result.corrections_made == 0
        assert result.confidence == 1.0

        # Verify error was logged
        mock_logger.error.assert_called()

    def test_partial_gap_correction(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        # Create a gap with multiple words
        gap = GapSequence(
            words=("wurld", "test"),
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world", "testing"]},
        )
        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # First handler corrects only "wurld"
        correction1 = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            segment_index=0,
            original_position=1,
            confidence=0.9,
            source="test",
            reason="First correction",
            alternatives={},
        )
        handler1 = MockHandler(should_handle=True, corrections=[correction1])

        # Second handler corrects "test"
        correction2 = WordCorrection(
            original_word="test",
            corrected_word="testing",
            segment_index=0,
            original_position=2,
            confidence=0.8,
            source="test",
            reason="Second correction",
            alternatives={},
        )
        handler2 = MockHandler(should_handle=True, corrections=[correction2])

        corrector = LyricsCorrector(handlers=[handler1, handler2], logger=mock_logger, anchor_finder=mock_finder, cache_dir=setup_teardown)

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify both corrections were made
        assert len(result.corrections) == 2
        assert "world" in result.corrected_text
        assert "testing" in result.corrected_text
        assert "wurld" not in result.corrected_text
        assert result.corrections_made == 2

        # Verify corrections were tracked in gap
        gap = result.gap_sequences[0]
        assert gap.is_word_corrected(0)  # "wurld" -> "world"
        assert gap.is_word_corrected(1)  # "test" -> "testing"
        assert gap.is_fully_corrected

    def test_skip_fully_corrected_gap(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test that handlers are skipped for fully corrected gaps."""
        # Create pre-existing corrections
        correction1 = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            original_position=1,
            segment_index=0,
            confidence=1.0,
            source="test",
            reason="Pre-existing correction",
            alternatives={},
        )
        correction2 = WordCorrection(
            original_word="test",
            corrected_word="testing",
            original_position=2,
            segment_index=0,
            confidence=1.0,
            source="test",
            reason="Pre-existing correction",
            alternatives={},
        )

        # Create gap with pre-existing corrections
        gap = GapSequence(
            words=("wurld", "test"),
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world", "testing"]},
        )
        gap.add_correction(correction1)
        gap.add_correction(correction2)

        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # This handler should never be called
        mock_handler = MockHandler(should_handle=True)

        corrector = LyricsCorrector(handlers=[mock_handler], logger=mock_logger, anchor_finder=mock_finder, cache_dir=setup_teardown)

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify handler was never called
        assert not mock_handler.can_handle_called
        assert not mock_handler.handle_called

        # Verify pre-existing corrections were preserved
        assert len(result.corrections) == 0  # No new corrections should be made
        assert gap.is_fully_corrected

    def test_no_corrections_warning(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test that a warning is logged when no handler can correct a gap."""
        gap = GapSequence(
            words=("wurld",),
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world"]},
        )

        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # Handler that can't handle the gap
        mock_handler = MockHandler(should_handle=False)

        corrector = LyricsCorrector(handlers=[mock_handler], logger=mock_logger, anchor_finder=mock_finder, cache_dir=setup_teardown)

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify warning was logged
        mock_logger.warning.assert_called_with("No handler could handle the gap")

        # Verify no corrections were made
        assert len(result.corrections) == 0
        assert not gap.was_corrected

    def test_multiple_gaps_processing(self, mock_logger, sample_transcription_result, sample_lyrics, setup_teardown):
        """Test processing multiple gaps with different handlers."""
        gap1 = GapSequence(
            words=("wurld",),
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world"]},
        )
        gap2 = GapSequence(
            words=("tst", "lyrcs"),
            transcription_position=2,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["test", "lyrics"]},
        )

        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap1, gap2]

        # Handler for first gap only
        correction1 = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            original_position=1,
            segment_index=0,
            confidence=1.0,
            source="test",
            reason="First gap correction",
            alternatives={},
        )
        handler1 = MockHandler(should_handle=True, corrections=[correction1])
        # Make handler1 only handle gap1
        original_can_handle = handler1.can_handle
        handler1.can_handle = lambda g: g == gap1 and original_can_handle(g)

        # Handler for second gap only
        correction2a = WordCorrection(
            original_word="tst",
            corrected_word="test",
            original_position=2,
            segment_index=0,
            confidence=1.0,
            source="test",
            reason="Second gap correction",
            alternatives={},
        )
        correction2b = WordCorrection(
            original_word="lyrcs",
            corrected_word="lyrics",
            original_position=3,
            segment_index=0,
            confidence=1.0,
            source="test",
            reason="Second gap correction",
            alternatives={},
        )
        handler2 = MockHandler(should_handle=True, corrections=[correction2a, correction2b])
        # Make handler2 only handle gap2
        original_can_handle2 = handler2.can_handle
        handler2.can_handle = lambda g: g == gap2 and original_can_handle2(g)

        corrector = LyricsCorrector(handlers=[handler1, handler2], logger=mock_logger, anchor_finder=mock_finder, cache_dir=setup_teardown)

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Debug: Print all corrections
        for i, corr in enumerate(result.corrections):
            print(f"Correction {i}: {corr.original_word} -> {corr.corrected_word}")

        # Verify both gaps were processed
        assert len(result.corrections) == 3  # One from first gap, two from second gap
        assert gap1.was_corrected
        assert gap2.was_corrected

        # Verify corrections were applied in correct order
        assert result.corrections[0].original_word == "wurld"
        assert result.corrections[1].original_word == "tst"
        assert result.corrections[2].original_word == "lyrcs"
