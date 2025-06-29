import pytest
from lyrics_transcriber.types import TranscriptionData, LyricsSegment, Word, TranscriptionResult, LyricsData, LyricsMetadata
from lyrics_transcriber.utils.word_utils import WordUtils


@pytest.fixture
def sample_transcription_data():
    # Create words with proper IDs
    words = [
        Word(id=WordUtils.generate_id(), text="My", start_time=0.0, end_time=0.5, confidence=0.9),
        Word(id=WordUtils.generate_id(), text="sample", start_time=0.5, end_time=1.5, confidence=0.8),
        Word(id=WordUtils.generate_id(), text="lyrics", start_time=1.5, end_time=2.0, confidence=0.95),
    ]
    
    # Create segment with proper ID
    segment = LyricsSegment(
        id=WordUtils.generate_id(),
        text="My sample lyrics",
        start_time=0.0,
        end_time=2.0,
        words=words
    )
    
    return TranscriptionData(
        text="My sample lyrics",
        segments=[segment],
        words=words,  # TranscriptionData needs a words list
        source="test",
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_lyrics_data():
    # Create words for the lyrics segment
    words = [
        Word(id=WordUtils.generate_id(), text="My", start_time=0.0, end_time=0.5, confidence=0.9),
        Word(id=WordUtils.generate_id(), text="sample", start_time=0.5, end_time=1.5, confidence=0.8),
        Word(id=WordUtils.generate_id(), text="lyrics", start_time=1.5, end_time=2.0, confidence=0.95),
    ]
    
    # Create segment
    segment = LyricsSegment(
        id=WordUtils.generate_id(),
        text="My sample lyrics",
        start_time=0.0,
        end_time=2.0,
        words=words
    )
    
    # Create metadata
    metadata = LyricsMetadata(
        source="genius",
        track_name="Test Song",
        artist_names="Test Artist",
        lyrics_provider="genius",
        is_synced=False
    )
    
    return LyricsData(
        segments=[segment],
        metadata=metadata,
        source="genius"
    )


def test_correction_workflow_with_lyrics(transcriber, sample_transcription_data, sample_lyrics_data):
    """Test the correction workflow with both transcription and lyrics data"""
    # Set up test data using correct data structure
    transcription_result = TranscriptionResult(
        name="test",
        priority=1,
        result=sample_transcription_data
    )
    transcriber.results.transcription_results = [transcription_result]
    transcriber.results.lyrics_results = {"genius": sample_lyrics_data}

    # Run correction
    transcriber.correct_lyrics()

    # Verify results
    assert transcriber.results.transcription_corrected is not None
    assert hasattr(transcriber.results.transcription_corrected, 'corrected_segments')
    assert hasattr(transcriber.results.transcription_corrected, 'original_segments')


def test_correction_workflow_fallback(transcriber, sample_transcription_data):
    """Test that correction falls back to raw transcription when no reference lyrics are available"""
    # Set up test data with only transcription (no reference lyrics)
    transcription_result = TranscriptionResult(
        name="test",
        priority=1,
        result=sample_transcription_data
    )
    transcriber.results.transcription_results = [transcription_result]
    # No lyrics_results - this should trigger fallback behavior

    # Run correction
    transcriber.correct_lyrics()

    # Verify fallback behavior - should create a CorrectionResult with no corrections
    assert transcriber.results.transcription_corrected is not None
    assert transcriber.results.transcription_corrected.corrections_made == 0
    assert transcriber.results.transcription_corrected.confidence == 1.0
