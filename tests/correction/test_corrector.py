import pytest
import logging
from unittest.mock import Mock, patch
from lyrics_transcriber.types import (
    CorrectionResult,
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


class MockHandler(GapCorrectionHandler):
    """Mock handler for testing."""

    def __init__(self, should_handle=True, correction=None, target_word=None):
        self.should_handle = should_handle
        self.correction = correction
        self.can_handle_called = False
        self.handle_called = False
        self.target_word = target_word  # Add target word to specify which gap this handler handles

    def can_handle(self, gap, current_word_idx):
        self.can_handle_called = True
        # Only handle gaps containing our target word
        return self.should_handle and (not self.target_word or self.target_word in gap.words)

    def handle(self, gap, word, current_word_idx, segment_idx):
        self.handle_called = True
        # Only return correction if this is our target word
        if self.target_word and word.text != self.target_word:
            return None
        return self.correction


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        {"text": "wurld", "start": 0.6, "end": 1.0},  # Intentionally misspelled
        {"text": "test", "start": 1.1, "end": 1.5},
        {"text": "lyrics", "start": 1.6, "end": 2.0},
    ]

    segment = LyricsSegment(
        text="hello wurld test lyrics",
        words=[Word(text=w["text"], start_time=w["start"], end_time=w["end"]) for w in words],
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
    segment = LyricsSegment(
        text="hello world test lyrics",  # Correct spelling
        words=[
            Word(text="hello", start_time=0.0, end_time=0.5),
            Word(text="world", start_time=0.6, end_time=1.0),
            Word(text="test", start_time=1.1, end_time=1.5),
            Word(text="lyrics", start_time=1.6, end_time=2.0),
        ],
        start_time=0.0,
        end_time=2.0,
    )

    return [
        LyricsData(
            source="test",
            lyrics="hello world test lyrics",
            segments=[segment],
            metadata=LyricsMetadata(source="genius", track_name="test track", artist_names="test artist"),
        )
    ]


@pytest.fixture
def mock_anchor_finder():
    finder = Mock()
    # Create a gap sequence that covers just the "wurld" word
    gap = GapSequence(
        words=["wurld"],  # The word we want to correct
        transcription_position=1,  # Position of "wurld"
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"test": ["world"]},  # The correct word
        corrections=[],
    )
    finder.find_anchors.return_value = []
    finder.find_gaps.return_value = [gap]
    return finder


class TestLyricsCorrector:
    @pytest.fixture
    def corrector(self, mock_logger, mock_anchor_finder):
        return LyricsCorrector(logger=mock_logger, anchor_finder=mock_anchor_finder)

    def test_run_no_transcription_results(self, corrector):
        with pytest.raises(ValueError, match="No primary transcription data available"):
            corrector.run(transcription_results=[], lyrics_results=[])

    def test_run_full_flow(self, mock_logger, sample_transcription_result, sample_lyrics):
        # Create a gap sequence that covers just the "wurld" word
        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world"]},
            corrections=[],
        )
        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # Create a mock handler that will correct "wurld" to "world"
        correction = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            segment_index=0,
            word_index=1,
            confidence=1.0,
            source="test",
            reason="Test correction",
            alternatives={},
        )
        mock_handler = MockHandler(should_handle=True, correction=correction)

        # Create corrector with our mock handler
        corrector = LyricsCorrector(handlers=[mock_handler], logger=mock_logger, anchor_finder=mock_finder)

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

    def test_run_with_error(self, mock_logger, mock_anchor_finder, sample_transcription_result, sample_lyrics):
        # Create a handler that raises an exception
        failing_handler = Mock(spec=GapCorrectionHandler)
        failing_handler.can_handle.side_effect = Exception("Test error")

        corrector = LyricsCorrector(handlers=[failing_handler], logger=mock_logger, anchor_finder=mock_anchor_finder)

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

    def test_multiple_handlers(self, mock_logger, sample_transcription_result, sample_lyrics):
        # Create a gap sequence that covers just the "wurld" word
        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world"]},
            corrections=[],
        )
        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap]

        # Create two handlers with different behaviors
        correction1 = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            segment_index=0,
            word_index=1,
            confidence=0.8,
            source="test",
            reason="First correction",
            alternatives={},
        )
        handler1 = MockHandler(should_handle=True, correction=correction1)
        handler2 = MockHandler(should_handle=False, correction=None)

        corrector = LyricsCorrector(handlers=[handler1, handler2], logger=mock_logger, anchor_finder=mock_finder)

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify first handler was used and second was skipped
        assert handler1.handle_called
        assert not handler2.handle_called
        assert len(result.corrections) == 1
        assert result.corrections[0] == correction1

    def test_handler_ordering_and_gap_correction(self, mock_logger, sample_transcription_result, sample_lyrics):
        # Create two gaps in our mock anchor finder
        gap1 = GapSequence(
            words=("wurld",),
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["world"]},
            corrections=[],
        )
        gap2 = GapSequence(
            words=("test",),
            transcription_position=2,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={"test": ["testing"]},
            corrections=[],
        )
        mock_finder = Mock()
        mock_finder.find_anchors.return_value = []
        mock_finder.find_gaps.return_value = [gap1, gap2]

        # Create three handlers with different behaviors
        correction1 = WordCorrection(
            original_word="wurld",
            corrected_word="world",
            segment_index=0,
            word_index=1,
            confidence=0.9,
            source="test",
            reason="First handler correction",
            alternatives={},
        )
        correction2 = WordCorrection(
            original_word="test",
            corrected_word="testing",
            segment_index=0,
            word_index=2,
            confidence=0.8,
            source="test",
            reason="Second handler correction",
            alternatives={},
        )

        # First handler only corrects "wurld"
        handler1 = MockHandler(should_handle=True, correction=correction1, target_word="wurld")
        
        # Second handler only corrects "test"
        handler2 = MockHandler(should_handle=True, correction=correction2, target_word="test")
        
        # Third handler should never be called since all gaps are corrected
        handler3 = Mock(spec=GapCorrectionHandler)
        handler3.can_handle = Mock(return_value=True)
        handler3.handle = Mock()

        corrector = LyricsCorrector(
            handlers=[handler1, handler2, handler3],
            logger=mock_logger,
            anchor_finder=mock_finder
        )

        result = corrector.run(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics
        )

        # Print debug logs
        print("\nDebug logs:")
        for call in mock_logger.debug.call_args_list:
            print(f"DEBUG: {call[0][0]}")

        # Verify corrections were made in order
        assert len(result.corrections) == 2, f"Expected 2 corrections, got {len(result.corrections)}"
        assert result.corrections[0] == correction1, "First correction should be from handler1"
        assert result.corrections[1] == correction2, "Second correction should be from handler2"

        # Verify third handler was never called
        handler3.handle.assert_not_called()

        # Verify corrected text contains both corrections
        assert "world" in result.corrected_text, "Expected 'world' in corrected text"
        assert "testing" in result.corrected_text, "Expected 'testing' in corrected text"
        assert "wurld" not in result.corrected_text, "Expected 'wurld' to be corrected"
        assert result.corrections_made == 2, f"Expected 2 corrections made, got {result.corrections_made}"
