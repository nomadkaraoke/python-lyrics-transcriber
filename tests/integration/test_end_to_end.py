import pytest
import os
from unittest.mock import patch, Mock
from lyrics_transcriber.core.controller import LyricsControllerResult
from lyrics_transcriber.types import TranscriptionData, LyricsSegment, Word, TranscriptionResult, LyricsData, LyricsMetadata
from lyrics_transcriber.utils.word_utils import WordUtils


@pytest.fixture
def mock_transcription_data():
    """Create sample transcription data for testing"""
    words = [
        Word(id=WordUtils.generate_id(), text="Test", start_time=0.0, end_time=0.5, confidence=0.9),
        Word(id=WordUtils.generate_id(), text="transcription", start_time=0.5, end_time=1.5, confidence=0.8),
        Word(id=WordUtils.generate_id(), text="result", start_time=1.5, end_time=2.0, confidence=0.95),
    ]
    
    segment = LyricsSegment(
        id=WordUtils.generate_id(),
        text="Test transcription result",
        start_time=0.0,
        end_time=2.0,
        words=words
    )
    
    return TranscriptionData(
        text="Test transcription result",
        segments=[segment],
        words=words,
        source="audioshake",
        metadata={"source": "audioshake", "confidence": 0.9},
    )


@pytest.fixture
def mock_lyrics_data():
    """Create sample lyrics data for testing"""
    words = [
        Word(id=WordUtils.generate_id(), text="Test", start_time=0.0, end_time=0.5, confidence=0.9),
        Word(id=WordUtils.generate_id(), text="lyrics", start_time=0.5, end_time=1.5, confidence=0.8),
        Word(id=WordUtils.generate_id(), text="result", start_time=1.5, end_time=2.0, confidence=0.95),
    ]
    
    segment = LyricsSegment(
        id=WordUtils.generate_id(),
        text="Test lyrics result",
        start_time=0.0,
        end_time=2.0,
        words=words
    )
    
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


def test_full_transcription_workflow(transcriber, test_audio_file, mock_transcription_data, mock_lyrics_data):
    """Test the full workflow with mocked services"""
    with patch.object(transcriber.transcribers["audioshake"]["instance"], 'transcribe') as mock_audioshake, \
         patch.object(transcriber.transcribers["whisper"]["instance"], 'transcribe') as mock_whisper, \
         patch.object(transcriber.lyrics_providers["genius"], 'fetch_lyrics') as mock_fetch_lyrics:
        
        # Mock both transcribers to return our test data
        mock_audioshake.return_value = mock_transcription_data
        mock_whisper.return_value = mock_transcription_data
        
        # Mock lyrics fetch to return our test data
        mock_fetch_lyrics.return_value = mock_lyrics_data
        
        # Run the full workflow
        result = transcriber.process()

        # Verify result type
        assert isinstance(result, LyricsControllerResult)

        # Verify we have transcription results
        assert result.transcription_results is not None
        assert len(result.transcription_results) > 0
        assert result.transcription_results[0].result.text == "Test transcription result"

        # Verify we have lyrics results
        assert result.lyrics_results is not None
        assert len(result.lyrics_results) > 0
        assert "genius" in result.lyrics_results

        # Verify correction was performed
        assert result.transcription_corrected is not None

        # Verify output files would be created (they should have paths set)
        assert result.lrc_filepath is not None
        assert result.ass_filepath is not None


def test_transcription_without_lyrics(transcriber, mock_transcription_data):
    """Test workflow without lyrics fetching"""
    # Test without artist/title to skip lyrics fetching
    transcriber.artist = None
    transcriber.title = None

    with patch.object(transcriber.transcribers["audioshake"]["instance"], 'transcribe') as mock_audioshake, \
         patch.object(transcriber.transcribers["whisper"]["instance"], 'transcribe') as mock_whisper:
        # Mock both transcribers to return our test data
        mock_audioshake.return_value = mock_transcription_data
        mock_whisper.return_value = mock_transcription_data
        
        result = transcriber.process()

        # Should still have transcription but no lyrics
        assert result.transcription_results is not None
        assert len(result.transcription_results) > 0
        assert len(result.lyrics_results) == 0
        
        # Should still create a correction result (fallback mode)
        assert result.transcription_corrected is not None
        assert result.transcription_corrected.corrections_made == 0  # No corrections since no reference lyrics
