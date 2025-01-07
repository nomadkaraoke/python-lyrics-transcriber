import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.core.controller import (
    LyricsTranscriber,
    TranscriberConfig,
    LyricsConfig,
    OutputConfig,
    TranscriptionResult,
)
import logging
from dataclasses import dataclass
from typing import Optional
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.lyrics.genius import GeniusProvider


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
    # Create lyrics providers with proper structure
    lyrics_providers = {"genius": mock_genius_provider, "spotify": mock_spotify_provider}  # Pass the mock directly, not in a dict

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
    mock_genius_provider,
    mock_spotify_provider,
):
    # Setup mock transcriber instances
    mock_whisper_class.return_value = mock_whisper_transcriber
    mock_audioshake_class.return_value = mock_audioshake_transcriber

    # Setup lyrics providers
    lyrics_providers = {"genius": mock_genius_provider, "spotify": mock_spotify_provider}  # Pass the mock directly

    transcriber_config = TranscriberConfig(audioshake_api_token="test_token", runpod_api_key="test_key", whisper_runpod_id="test_id")
    lyrics_config = LyricsConfig(genius_api_token="test_token", spotify_cookie="test_cookie")
    output_config = OutputConfig(output_dir="test_output", cache_dir="test_cache")

    transcriber = LyricsTranscriber(
        audio_filepath=sample_audio_file,
        transcriber_config=transcriber_config,
        lyrics_config=lyrics_config,
        output_config=output_config,
        logger=test_logger,
        corrector=mock_corrector,
        output_generator=mock_output_generator,
        lyrics_providers=lyrics_providers,
    )

    # Verify transcribers were initialized
    assert "audioshake" in transcriber.transcribers
    assert "whisper" in transcriber.transcribers


def test_process_with_artist_and_title(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    # Setup mock returns
    mock_lyrics_data = {"text": "Test lyrics", "source": "genius"}
    mock_genius_provider.fetch_lyrics.return_value = mock_lyrics_data
    mock_spotify_provider.fetch_lyrics.return_value = None  # Spotify should return None

    # Run process
    result = basic_transcriber.process()

    # Verify lyrics fetching was called with correct arguments
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify results - only one result should be added since Spotify returns None
    assert len(result.lyrics_results) == 1
    assert result.lyrics_results[0] == mock_lyrics_data


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
    # Create mock output paths
    mock_output_paths = MockOutputPaths(lrc="test.lrc", ass="test.ass", video="test.mp4")
    mock_output_generator.generate_outputs.return_value = mock_output_paths

    # Setup test data
    basic_transcriber.results.transcription_corrected = {"test": "data"}

    # Run generate_outputs
    basic_transcriber.generate_outputs()

    # Verify output generation was called correctly
    mock_output_generator.generate_outputs.assert_called_once_with(
        transcription_corrected={"test": "data"},
        lyrics_results=[],
        output_prefix="Test Artist - Test Song",
        audio_filepath=basic_transcriber.audio_filepath,
        render_video=False
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
    basic_transcriber.transcribers = {"whisper": {"instance": mock_whisper_transcriber, "priority": 1}}

    # Should not raise exception
    basic_transcriber.transcribe()
    assert len(basic_transcriber.results.transcription_results) == 0


def test_correct_lyrics_with_failed_correction(basic_transcriber, mock_corrector):
    """Test correction handling when correction fails"""
    # Setup mock data
    mock_corrector.run.side_effect = Exception("Correction failed")

    # Should not raise exception
    basic_transcriber.correct_lyrics()

    # Verify no corrected results
    assert basic_transcriber.results.transcription_corrected is None


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

    # Verify no results were stored
    assert len(basic_transcriber.results.lyrics_results) == 0


def test_fetch_lyrics_with_empty_result(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test lyrics fetching when no lyrics are found"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_provider.fetch_lyrics.return_value = None

    basic_transcriber.fetch_lyrics()

    # Verify no results were stored
    assert len(basic_transcriber.results.lyrics_results) == 0


def test_transcribe_with_multiple_transcribers(basic_transcriber, mock_whisper_transcriber, mock_audioshake_transcriber):
    """Test transcription with multiple transcribers where first one fails"""
    # Setup transcribers
    mock_whisper_transcriber.transcribe.side_effect = Exception("Whisper failed")
    mock_audioshake_transcriber.transcribe.return_value = {"test": "audioshake_data"}
    basic_transcriber.transcribers = {
        "whisper": {"instance": mock_whisper_transcriber, "priority": 2},
        "audioshake": {"instance": mock_audioshake_transcriber, "priority": 1},
    }

    basic_transcriber.transcribe()

    # Verify results
    assert len(basic_transcriber.results.transcription_results) == 1
    assert basic_transcriber.results.transcription_results[0].name == "audioshake"
    assert basic_transcriber.results.transcription_results[0].result == {"test": "audioshake_data"}


def test_process_with_successful_correction(basic_transcriber, mock_corrector):
    """Test successful correction process"""
    # Setup mock data
    mock_corrector.run.return_value = {"test": "corrected_data"}
    basic_transcriber.results.transcription_results = [TranscriptionResult(name="test", priority=1, result={"test": "data"})]

    # Run correction
    basic_transcriber.correct_lyrics()

    # Verify correction was successful
    assert basic_transcriber.results.transcription_corrected == {"test": "corrected_data"}


def test_transcribe_with_successful_whisper(basic_transcriber, mock_whisper_transcriber):
    """Test successful whisper transcription"""
    # Setup mock
    mock_whisper_transcriber.transcribe.return_value = {"test": "whisper_data"}
    basic_transcriber.transcribers = {"whisper": {"instance": mock_whisper_transcriber, "priority": 1}}

    # Run transcription
    basic_transcriber.transcribe()

    # Verify results
    assert len(basic_transcriber.results.transcription_results) == 1
    assert basic_transcriber.results.transcription_results[0].name == "whisper"
    assert basic_transcriber.results.transcription_results[0].result == {"test": "whisper_data"}


def test_process_full_successful_workflow(
    basic_transcriber, mock_genius_provider, mock_spotify_provider, mock_corrector, mock_whisper_transcriber
):
    """Test a complete successful workflow"""
    # Setup mocks
    mock_lyrics_data = {"text": "Test lyrics", "source": "genius"}
    mock_genius_provider.fetch_lyrics.return_value = mock_lyrics_data
    mock_spotify_provider.fetch_lyrics.return_value = None  # Spotify should return None

    # Setup transcriber
    basic_transcriber.transcribers = {"whisper": {"instance": mock_whisper_transcriber, "priority": 1}}
    mock_whisper_transcriber.transcribe.return_value = {"test": "whisper_data"}
    mock_corrector.run.return_value = {"test": "corrected_data"}

    # Run full process
    result = basic_transcriber.process()

    # Verify complete workflow
    assert len(result.lyrics_results) == 1
    assert result.lyrics_results[0] == mock_lyrics_data
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    assert len(result.transcription_results) == 1
    assert result.transcription_results[0].result == {"test": "whisper_data"}
    assert result.transcription_corrected == {"test": "corrected_data"}


def test_fetch_lyrics_success(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test successful lyrics fetching from primary provider"""
    mock_lyrics_data = {"text": "Test lyrics", "source": "genius"}
    mock_genius_provider.fetch_lyrics.return_value = mock_lyrics_data
    mock_spotify_provider.fetch_lyrics.return_value = None  # Spotify should return None

    basic_transcriber.fetch_lyrics()

    # Verify lyrics fetching was called for both providers
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify results - only one result should be added since Spotify returns None
    assert len(basic_transcriber.results.lyrics_results) == 1
    assert basic_transcriber.results.lyrics_results[0] == mock_lyrics_data


def test_fetch_lyrics_fallback(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test fallback to secondary provider when primary fails"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_lyrics = {"text": "Spotify lyrics", "source": "spotify"}
    mock_spotify_provider.fetch_lyrics.return_value = mock_spotify_lyrics

    basic_transcriber.fetch_lyrics()

    # Verify both providers were tried
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify results - only Spotify result should be present
    assert len(basic_transcriber.results.lyrics_results) == 1
    assert basic_transcriber.results.lyrics_results[0] == mock_spotify_lyrics


def test_fetch_lyrics_all_fail(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test handling when all providers fail"""
    mock_genius_provider.fetch_lyrics.return_value = None
    mock_spotify_provider.fetch_lyrics.return_value = None

    basic_transcriber.fetch_lyrics()

    # Verify all providers were tried
    mock_genius_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")
    mock_spotify_provider.fetch_lyrics.assert_called_once_with("Test Artist", "Test Song")

    # Verify no results were stored
    assert len(basic_transcriber.results.lyrics_results) == 0


def test_initialize_transcribers_with_audioshake_only(sample_audio_file):
    """Test transcriber initialization with only AudioShake config"""
    transcriber_config = TranscriberConfig(audioshake_api_token="test_token")
    transcriber = LyricsTranscriber(audio_filepath=sample_audio_file, transcriber_config=transcriber_config)

    transcribers = transcriber.transcribers
    assert len(transcribers) == 1
    assert "audioshake" in transcribers
    assert "whisper" not in transcribers


def test_initialize_transcribers_with_whisper_only(sample_audio_file):
    """Test transcriber initialization with only Whisper config"""
    transcriber_config = TranscriberConfig(runpod_api_key="test_key", whisper_runpod_id="test_id")
    transcriber = LyricsTranscriber(audio_filepath=sample_audio_file, transcriber_config=transcriber_config)

    transcribers = transcriber.transcribers
    assert len(transcribers) == 1
    assert "whisper" in transcribers
    assert "audioshake" not in transcribers


def test_generate_outputs_with_error(basic_transcriber, mock_output_generator):
    """Test output generation when an error occurs"""
    mock_output_generator.generate_outputs.side_effect = Exception("Failed to generate outputs")

    with pytest.raises(Exception) as exc_info:
        basic_transcriber.generate_outputs()

    assert str(exc_info.value) == "Failed to generate outputs"
    assert basic_transcriber.results.lrc_filepath is None
    assert basic_transcriber.results.ass_filepath is None
    assert basic_transcriber.results.video_filepath is None


def test_initialize_lyrics_providers_with_genius_only(sample_audio_file):
    """Test lyrics provider initialization with only Genius config"""
    lyrics_config = LyricsConfig(genius_api_token="test_token")
    transcriber = LyricsTranscriber(audio_filepath=sample_audio_file, lyrics_config=lyrics_config)

    providers = transcriber.lyrics_providers
    assert len(providers) == 1
    assert "genius" in providers
    assert isinstance(providers["genius"], GeniusProvider)
    assert "spotify" not in providers


@patch("lyrics_transcriber.core.controller.SpotifyProvider")
@patch("syrics.api.Spotify")
def test_initialize_lyrics_providers_with_spotify_only(mock_spotify_api_class, mock_spotify_provider_class, sample_audio_file):
    """Test lyrics provider initialization with only Spotify config"""
    # Setup mock SpotifyProvider instance
    mock_spotify_provider = Mock()
    mock_spotify_provider_class.return_value = mock_spotify_provider

    # Setup mock Spotify API instance
    mock_spotify_api = Mock()
    mock_spotify_api_class.return_value = mock_spotify_api

    lyrics_config = LyricsConfig(spotify_cookie="test_cookie")
    transcriber = LyricsTranscriber(audio_filepath=sample_audio_file, lyrics_config=lyrics_config)

    providers = transcriber.lyrics_providers
    assert len(providers) == 1
    assert "spotify" in providers
    assert providers["spotify"] == mock_spotify_provider
    assert "genius" not in providers

    # Verify SpotifyProvider was initialized with correct arguments
    mock_spotify_provider_class.assert_called_once()
    call_kwargs = mock_spotify_provider_class.call_args.kwargs
    assert isinstance(call_kwargs["config"], LyricsProviderConfig)
    assert call_kwargs["config"].spotify_cookie == lyrics_config.spotify_cookie
    assert call_kwargs["config"].genius_api_token == lyrics_config.genius_api_token
    assert call_kwargs["config"].cache_dir == "/tmp/lyrics-transcriber-cache/"
    assert call_kwargs["config"].audio_filepath == sample_audio_file
    assert call_kwargs["logger"] is not None


def test_fetch_lyrics_with_provider_error(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test fetch_lyrics error handling when providers raise exceptions"""
    # Make both providers raise exceptions
    mock_genius_provider.fetch_lyrics.side_effect = Exception("Genius error")
    mock_spotify_provider.fetch_lyrics.side_effect = Exception("Spotify error")

    # Should not raise exception
    basic_transcriber.fetch_lyrics()

    # Verify error was handled gracefully
    assert len(basic_transcriber.results.lyrics_results) == 0
    mock_genius_provider.fetch_lyrics.assert_called_once()
    mock_spotify_provider.fetch_lyrics.assert_called_once()


def test_fetch_lyrics_with_outer_exception(basic_transcriber, mock_genius_provider, mock_spotify_provider):
    """Test fetch_lyrics when an outer exception occurs"""
    # Make the lyrics_providers attribute raise an exception when accessed
    basic_transcriber.lyrics_providers = None  # This will cause an attribute error when iterating

    # Should not raise exception
    basic_transcriber.fetch_lyrics()

    # Verify no results were stored
    assert len(basic_transcriber.results.lyrics_results) == 0
