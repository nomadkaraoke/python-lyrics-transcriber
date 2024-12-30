import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.core.controller import (
    LyricsTranscriber,
    TranscriberConfig,
    LyricsConfig,
    OutputConfig,
    WhisperConfig,
    AudioShakeConfig,
)
import logging
from dataclasses import dataclass
from typing import Optional
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.spotify import SpotifyProvider


@dataclass
class MockOutputPaths:
    lrc: Optional[str] = None
    ass: Optional[str] = None
    video: Optional[str] = None


@pytest.fixture
def mock_corrector():
    return Mock()


@pytest.fixture
def mock_output_generator():
    return Mock()


@pytest.fixture
def mock_whisper_transcriber():
    return Mock()


@pytest.fixture
def mock_audioshake_transcriber():
    return Mock()


@pytest.fixture
def mock_genius_provider():
    return Mock()


@pytest.fixture
def mock_spotify_provider():
    return Mock()


@pytest.fixture
def basic_transcriber(sample_audio_file, test_logger, mock_genius_provider, mock_spotify_provider, mock_corrector, mock_output_generator):
    lyrics_providers = {"genius": mock_genius_provider, "spotify": mock_spotify_provider}
    return LyricsTranscriber(
        audio_filepath=sample_audio_file,
        artist="Test Artist",
        title="Test Song",
        logger=test_logger,
        lyrics_providers=lyrics_providers,
        corrector=mock_corrector,
        output_generator=mock_output_generator,
    )


def test_lyrics_transcriber_initialization(basic_transcriber):
    assert basic_transcriber.audio_filepath is not None
    assert basic_transcriber.artist == "Test Artist"
    assert basic_transcriber.title == "Test Song"
    assert basic_transcriber.output_prefix == "Test Artist - Test Song"


@patch("lyrics_transcriber.core.controller.AudioShakeTranscriber")
@patch("lyrics_transcriber.core.controller.WhisperTranscriber")
def test_transcriber_with_configs(
    mock_whisper_class,
    mock_audioshake_class,
    sample_audio_file,
    test_logger,
    mock_corrector,
    mock_output_generator,
    mock_whisper_transcriber,
    mock_audioshake_transcriber,
):
    # Setup mock transcriber instances
    mock_whisper_class.return_value = mock_whisper_transcriber
    mock_audioshake_class.return_value = mock_audioshake_transcriber

    transcriber_config = TranscriberConfig(audioshake_api_token="test_token", runpod_api_key="test_key", whisper_runpod_id="test_id")
    lyrics_config = LyricsConfig(genius_api_token="test_token", spotify_cookie="test_cookie")
    output_config = OutputConfig(output_dir="test_output", cache_dir="test_cache", render_video=True)

    transcriber = LyricsTranscriber(
        audio_filepath=sample_audio_file,
        transcriber_config=transcriber_config,
        lyrics_config=lyrics_config,
        output_config=output_config,
        logger=test_logger,
        corrector=mock_corrector,
        output_generator=mock_output_generator,
    )

    # Verify config values
    assert transcriber.transcriber_config.audioshake_api_token == "test_token"
    assert transcriber.lyrics_config.genius_api_token == "test_token"
    assert transcriber.output_config.render_video is True

    # Update assertions to include cache_dir
    mock_whisper_class.assert_called_once_with(
        cache_dir="test_cache", config=WhisperConfig(runpod_api_key="test_key", endpoint_id="test_id"), logger=test_logger
    )
    mock_audioshake_class.assert_called_once_with(
        cache_dir="test_cache",
        config=AudioShakeConfig(api_token="test_token", base_url="https://groovy.audioshake.ai", output_prefix=None),
        logger=test_logger,
    )


def test_process_with_artist_and_title(basic_transcriber, mock_genius_provider):
    # Setup mock returns
    mock_genius_provider.fetch_lyrics.return_value = "Test lyrics"

    # Run process
    result = basic_transcriber.process()

    # Verify lyrics fetching was called
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify results
    assert result.lyrics_text == "Test lyrics"
    assert result.lyrics_source == "genius"
    assert result.lyrics_genius == "Test lyrics"


def test_process_without_artist_and_title(
    sample_audio_file, test_logger, mock_genius_provider, mock_spotify_provider, mock_corrector, mock_output_generator
):
    lyrics_providers = {"genius": mock_genius_provider, "spotify": mock_spotify_provider}
    transcriber = LyricsTranscriber(
        audio_filepath=sample_audio_file,
        logger=test_logger,
        lyrics_providers=lyrics_providers,
        corrector=mock_corrector,
        output_generator=mock_output_generator,
    )

    result = transcriber.process()

    # Verify lyrics fetching was not called
    mock_genius_provider.fetch_lyrics.assert_not_called()
    mock_spotify_provider.fetch_lyrics.assert_not_called()


def test_generate_outputs(basic_transcriber, mock_output_generator):
    # Create a mock OutputPaths-like object
    class MockOutputPaths:
        def __init__(self):
            self.lrc = "test.lrc"
            self.ass = "test.ass"
            self.video = "test.mp4"

    # Setup mock returns
    mock_output_generator.generate_outputs.return_value = MockOutputPaths()

    # Setup transcription data
    basic_transcriber.results.transcription_corrected = {"test": "data"}

    # Run generate_outputs
    basic_transcriber.generate_outputs()

    # Verify output generation was called correctly
    mock_output_generator.generate_outputs.assert_called_once_with(
        transcription_data={"test": "data"},
        output_prefix="Test Artist - Test Song",
        audio_filepath=basic_transcriber.audio_filepath,
        render_video=False,
    )

    # Verify results
    assert basic_transcriber.results.lrc_filepath == "test.lrc"
    assert basic_transcriber.results.ass_filepath == "test.ass"
    assert basic_transcriber.results.video_filepath == "test.mp4"


def test_initialize_transcribers_with_no_config(basic_transcriber):
    """Test transcriber initialization when no API tokens are provided"""
    transcribers = basic_transcriber._initialize_transcribers()
    assert len(transcribers) == 0


def test_logger_initialization_without_existing_logger(sample_audio_file):
    """Test that logger is properly initialized when none is provided"""
    transcriber = LyricsTranscriber(audio_filepath=sample_audio_file)
    assert transcriber.logger is not None
    assert transcriber.logger.level == logging.DEBUG
    assert len(transcriber.logger.handlers) == 1


def test_transcribe_with_failed_transcriber(basic_transcriber, mock_whisper_transcriber):
    """Test transcription handling when a transcriber fails"""
    # Setup mock transcriber that raises an exception
    mock_whisper_transcriber.transcribe.side_effect = Exception("Transcription failed")
    basic_transcriber.transcribers = {"whisper": mock_whisper_transcriber}

    # Should not raise exception
    basic_transcriber.transcribe()
    assert basic_transcriber.results.transcription_primary is None


def test_correct_lyrics_with_failed_correction(basic_transcriber, mock_corrector):
    """Test correction handling when correction fails"""
    # Setup initial transcription data
    basic_transcriber.results.transcription_primary = {"test": "data"}
    mock_corrector.run_corrector.side_effect = Exception("Correction failed")

    # Should not raise exception and should use primary transcription as fallback
    basic_transcriber.correct_lyrics()
    assert basic_transcriber.results.transcription_corrected == {"test": "data"}


def test_process_with_failed_output_generation(basic_transcriber, mock_output_generator):
    """Test process handling when output generation fails"""
    # Setup successful transcription but failed output generation
    basic_transcriber.results.transcription_corrected = {"test": "data"}
    mock_output_generator.generate_outputs.side_effect = Exception("Output generation failed")

    with pytest.raises(Exception):
        basic_transcriber.process()


def test_fetch_lyrics_with_failed_fetcher(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test lyrics fetching when the providers fail"""
    mock_genius_provider.fetch_lyrics.side_effect = Exception("Failed to fetch lyrics")
    mock_spotify_provider.fetch_lyrics.side_effect = Exception("Failed to fetch lyrics")

    # Should not raise exception
    basic_transcriber.fetch_lyrics()

    # Verify results remain None
    assert basic_transcriber.results.lyrics_text is None
    assert basic_transcriber.results.lyrics_source is None
    assert basic_transcriber.results.lyrics_genius is None
    assert basic_transcriber.results.lyrics_spotify is None
    assert basic_transcriber.results.spotify_lyrics_data is None


def test_fetch_lyrics_with_empty_result(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test lyrics fetching when no lyrics are found"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_provider.fetch_lyrics.return_value = None

    basic_transcriber.fetch_lyrics()

    # Verify empty results are handled
    assert basic_transcriber.results.lyrics_text is None
    assert basic_transcriber.results.lyrics_source is None


def test_transcribe_with_multiple_transcribers(basic_transcriber, mock_whisper_transcriber, mock_audioshake_transcriber):
    """Test transcription with multiple transcribers where first one fails"""
    # Setup transcribers
    mock_whisper_transcriber.transcribe.side_effect = Exception("Whisper failed")
    mock_audioshake_transcriber.transcribe.return_value = {"test": "audioshake_data"}
    basic_transcriber.transcribers = {"whisper": mock_whisper_transcriber, "audioshake": mock_audioshake_transcriber}

    basic_transcriber.transcribe()

    # Verify AudioShake result was used as primary when Whisper failed
    assert basic_transcriber.results.transcription_whisper is None
    assert basic_transcriber.results.transcription_audioshake == {"test": "audioshake_data"}
    assert basic_transcriber.results.transcription_primary == {"test": "audioshake_data"}


def test_process_with_successful_correction(basic_transcriber, mock_corrector):
    """Test successful correction process"""
    # Setup mock data
    basic_transcriber.results.transcription_primary = {"test": "data"}
    mock_corrector.run_corrector.return_value = {"test": "corrected_data"}

    # Run correction
    basic_transcriber.correct_lyrics()

    # Verify correction was successful
    assert basic_transcriber.results.transcription_corrected == {"test": "corrected_data"}


def test_transcribe_with_successful_whisper(basic_transcriber, mock_whisper_transcriber):
    """Test successful whisper transcription"""
    # Setup mock
    mock_whisper_transcriber.transcribe.return_value = {"test": "whisper_data"}
    basic_transcriber.transcribers = {"whisper": mock_whisper_transcriber}

    # Run transcription
    basic_transcriber.transcribe()

    # Verify whisper results were stored
    assert basic_transcriber.results.transcription_whisper == {"test": "whisper_data"}
    assert basic_transcriber.results.transcription_primary == {"test": "whisper_data"}


def test_process_full_successful_workflow(basic_transcriber, mock_genius_provider, mock_corrector, mock_whisper_transcriber):
    """Test a complete successful workflow"""
    # Setup mocks
    mock_genius_provider.fetch_lyrics.return_value = "Test lyrics"
    basic_transcriber.transcribers = {"whisper": mock_whisper_transcriber}
    mock_whisper_transcriber.transcribe.return_value = {"test": "whisper_data"}
    mock_corrector.run_corrector.return_value = {"test": "corrected_data"}

    # Run full process
    result = basic_transcriber.process()

    # Verify complete workflow
    assert result.lyrics_text == "Test lyrics"
    assert result.lyrics_source == "genius"
    assert result.lyrics_genius == "Test lyrics"
    assert result.transcription_whisper == {"test": "whisper_data"}
    assert result.transcription_corrected == {"test": "corrected_data"}


def test_fetch_lyrics_success(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test successful lyrics fetching from primary provider"""
    mock_genius_provider.fetch_lyrics.return_value = "Test lyrics"

    basic_transcriber.fetch_lyrics()

    # Verify lyrics fetching was called
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_not_called()

    # Verify results
    assert basic_transcriber.results.lyrics_text == "Test lyrics"
    assert basic_transcriber.results.lyrics_source == "genius"
    assert basic_transcriber.results.lyrics_genius == "Test lyrics"


def test_fetch_lyrics_fallback(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test fallback to secondary provider when primary fails"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_provider.fetch_lyrics.return_value = "Spotify lyrics"

    basic_transcriber.fetch_lyrics()

    # Verify both providers were tried in order
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify results use fallback provider
    assert basic_transcriber.results.lyrics_text == "Spotify lyrics"
    assert basic_transcriber.results.lyrics_source == "spotify"
    assert basic_transcriber.results.lyrics_spotify == "Spotify lyrics"


def test_fetch_lyrics_all_fail(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test handling when all providers fail"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_provider.fetch_lyrics.return_value = None

    basic_transcriber.fetch_lyrics()

    # Verify all providers were tried
    mock_genius_provider.fetch_lyrics.assert_called_once()
    mock_spotify_provider.fetch_lyrics.assert_called_once()

    # Verify results remain None
    assert basic_transcriber.results.lyrics_text is None
    assert basic_transcriber.results.lyrics_source is None
    assert basic_transcriber.results.lyrics_genius is None
    assert basic_transcriber.results.lyrics_spotify is None
