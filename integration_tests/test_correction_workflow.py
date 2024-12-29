import pytest
from lyrics_transcriber.transcribers.base import TranscriptionData, LyricsSegment, Word


@pytest.fixture
def sample_transcription_data():
    return TranscriptionData(
        text="My sample lyrics",
        segments=[
            LyricsSegment(
                text="My sample lyrics",
                start_time=0.0,
                end_time=2.0,
                words=[
                    Word(text="My", start_time=0.0, end_time=0.5, confidence=0.9),
                    Word(text="sample", start_time=0.5, end_time=1.5, confidence=0.8),
                    Word(text="lyrics", start_time=1.5, end_time=2.0, confidence=0.95),
                ],
            )
        ],
        metadata={"source": "test"},
    )


def test_correction_workflow_with_lyrics(transcriber, sample_transcription_data):
    """Test the correction workflow with both transcription and lyrics data"""
    # Set up test data
    transcriber.results.transcription_primary = sample_transcription_data
    transcriber.results.transcription_whisper = sample_transcription_data
    transcriber.results.lyrics_genius = "My sample lyrics"

    # Run correction
    transcriber.correct_lyrics()

    # Verify results
    assert transcriber.results.transcription_corrected is not None
    assert isinstance(transcriber.results.transcription_corrected.segments, list)
    assert len(transcriber.results.transcription_corrected.segments) > 0

    # Verify segment structure
    first_segment = transcriber.results.transcription_corrected.segments[0]
    assert isinstance(first_segment, LyricsSegment)
    assert isinstance(first_segment.words, list)
    assert all(isinstance(word, Word) for word in first_segment.words)


def test_correction_workflow_fallback(transcriber, sample_transcription_data):
    """Test that correction falls back to primary transcription on error"""
    # Set up test data with only primary transcription
    transcriber.results.transcription_primary = sample_transcription_data

    # Run correction
    transcriber.correct_lyrics()

    # Verify fallback behavior
    assert transcriber.results.transcription_corrected == sample_transcription_data
