import pytest
import os
from lyrics_transcriber.core.controller import TranscriptionResult


def test_full_transcription_workflow(transcriber, test_audio_file):
    # Run the full workflow
    result = transcriber.process()

    # Verify result type
    assert isinstance(result, TranscriptionResult)

    # Verify files were created
    assert result.lrc_filepath and os.path.exists(result.lrc_filepath)
    assert result.ass_filepath and os.path.exists(result.ass_filepath)

    # Verify transcription data
    assert result.transcription_primary is not None
    assert result.transcription_corrected is not None

    # Verify lyrics were fetched
    assert result.lyrics_text is not None
    assert result.lyrics_source in ["genius", "spotify"]


def test_transcription_without_lyrics(transcriber):
    # Test without artist/title to skip lyrics fetching
    transcriber.artist = None
    transcriber.title = None

    result = transcriber.process()

    # Should still have transcription but no lyrics
    assert result.transcription_primary is not None
    assert result.lyrics_text is None
