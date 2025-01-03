import pytest
from unittest.mock import Mock
from lyrics_transcriber.correction.base_strategy import CorrectionResult
from lyrics_transcriber.correction.corrector import LyricsCorrector
from lyrics_transcriber.transcribers.base_transcriber import TranscriptionResult, TranscriptionData
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsData, LyricsMetadata
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsSegment, Word


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        {"text": "world", "start": 0.6, "end": 1.0},
        {"text": "test", "start": 1.1, "end": 1.5},
        {"text": "lyrics", "start": 1.6, "end": 2.0},
    ]

    # Create a segment with the words
    segment = LyricsSegment(
        text="hello world test lyrics",
        words=[Word(text=w["text"], start_time=w["start"], end_time=w["end"]) for w in words],
        start_time=0.0,
        end_time=2.0,
    )

    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],  # Add the segment with words
            text="hello world test lyrics",
            source="test",
            words=words,
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    # Create a lyrics segment matching the transcription
    segment = LyricsSegment(
        text="hello world test lyrics",
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
            segments=[segment],  # Add the segment with words
            metadata=LyricsMetadata(source="genius", track_name="test track", artist_names="test artist"),
        )
    ]


class TestLyricsCorrector:
    @pytest.fixture
    def corrector(self, mock_logger):
        return LyricsCorrector(logger=mock_logger)

    def test_run_no_transcription_results(self, corrector):
        with pytest.raises(ValueError, match="No primary transcription data available"):
            corrector.run(transcription_results=[], lyrics_results=[])

    def test_run_full_flow(self, corrector, sample_transcription_result, sample_lyrics):
        # Create a mock correction strategy that returns expected result
        mock_strategy = Mock()
        mock_strategy.correct.return_value = CorrectionResult(
            original_segments=sample_transcription_result.result.segments,
            corrected_segments=sample_transcription_result.result.segments,
            corrected_text="hello world test lyrics",
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            transcribed_text="hello world test lyrics",
            reference_texts={"test": "hello world test lyrics"},
            anchor_sequences=[],
            metadata={"correction_strategy": "diff_based", "primary_source": "test"}
        )

        # Replace the default strategy with our mock
        corrector.correction_strategy = mock_strategy

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify the mock was called correctly
        mock_strategy.correct.assert_called_once_with(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Verify the result
        assert result.corrected_text == "hello world test lyrics", f"Expected matching text but got: '{result.corrected_text}'"
        assert result.corrected_segments == sample_transcription_result.result.segments
        assert result.confidence > 0
        assert result.corrections_made >= 0
        assert "correction_strategy" in result.metadata
        assert "primary_source" in result.metadata
        assert result.metadata["primary_source"] == "test"

    def test_run_with_error(self, corrector, sample_transcription_result, sample_lyrics):
        # Set up a failing correction strategy
        mock_strategy = Mock()
        mock_strategy.correct.side_effect = Exception("Test error")
        corrector.correction_strategy = mock_strategy

        result = corrector.run(transcription_results=[sample_transcription_result], lyrics_results=sample_lyrics)

        # Should fall back to original transcription
        assert result.corrected_segments == sample_transcription_result.result.segments
        primary_text = sample_transcription_result.result.text
        assert result.corrected_text == primary_text
        assert result.transcribed_text == primary_text
        assert result.reference_texts == {}  # Empty reference texts in fallback case
        assert result.confidence == 1.0
        assert result.corrections_made == 0
