import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from lyrics_transcriber.core.controller import TranscriberConfig, LyricsConfig, LyricsTranscriber
import threading
import time
import requests

from lyrics_transcriber.review.server import ReviewServer
from lyrics_transcriber.output.generator import OutputGenerator
from lyrics_transcriber.types import CorrectionResult, LyricsSegment, Word

# Add the tests directory to Python path for imports
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from test_helpers import create_test_output_config


@pytest.fixture
def test_audio_file():
    return os.path.join(os.path.dirname(__file__), "fixtures", "audio_samples", "sample1.mp3")


@pytest.fixture
def mock_configs():
    transcriber_config = TranscriberConfig(audioshake_api_token="test_token", runpod_api_key="test_key", whisper_runpod_id="test_id")

    lyrics_config = LyricsConfig(genius_api_token="test_token", spotify_cookie="test_cookie")

    # Create unique output directories for each test to prevent interference
    unique_output_dir = tempfile.mkdtemp(prefix="test_output_")
    unique_cache_dir = tempfile.mkdtemp(prefix="test_cache_")
    
    # Enable video rendering so ASS files are generated
    output_config = create_test_output_config(
        output_dir=unique_output_dir, 
        cache_dir=unique_cache_dir,
        render_video=True  # Enable ASS file generation
    )

    return transcriber_config, lyrics_config, output_config


@pytest.fixture
def mock_dropbox_handler():
    """Mock DropboxHandler to avoid validation errors in CI."""
    with patch("lyrics_transcriber.storage.dropbox.DropboxHandler") as mock_dropbox:
        # Create a mock storage instance
        mock_storage = Mock()
        mock_storage.file_exists.return_value = False
        mock_storage.upload_with_retry.return_value = None
        mock_storage.create_or_get_shared_link.return_value = "https://test.com/audio.mp3"
        mock_dropbox.return_value = mock_storage
        yield mock_dropbox


@pytest.fixture
def mock_video_generators():
    """Mock video and subtitle generators to prevent actual video processing during tests."""
    with patch("lyrics_transcriber.output.generator.SubtitlesGenerator") as mock_subtitle_gen, \
         patch("lyrics_transcriber.output.generator.VideoGenerator") as mock_video_gen:
        
        # Mock subtitle generator
        mock_subtitle_instance = Mock()
        mock_subtitle_instance.generate_ass.return_value = "test_output/Test Artist - Test Song.ass"
        mock_subtitle_gen.return_value = mock_subtitle_instance
        
        # Mock video generator  
        mock_video_instance = Mock()
        mock_video_instance.generate_video.return_value = "test_output/Test Artist - Test Song.mp4"
        mock_video_gen.return_value = mock_video_instance
        
        yield mock_subtitle_gen, mock_video_gen


@pytest.fixture
def transcriber(test_audio_file, mock_configs, mock_dropbox_handler, mock_video_generators):
    transcriber_config, lyrics_config, output_config = mock_configs
    
    return LyricsTranscriber(
        audio_filepath=test_audio_file,
        artist="Test Artist",
        title="Test Song",
        transcriber_config=transcriber_config,
        lyrics_config=lyrics_config,
        output_config=output_config,
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as an integration test")


@pytest.fixture(scope="session", autouse=True)
def start_review_server_for_api_tests(tmp_path_factory):
    """Start the FastAPI review server in background for API integration tests.

    If frontend assets are unavailable, the server constructor raises; we
    suppress startup in that case and let API tests skip gracefully.
    """
    # Create a minimal CorrectionResult to satisfy server init
    try:
        seg = LyricsSegment(id="s1", text="hello world", words=[Word(id="w1", text="hello", start_time=0.0, end_time=0.5), Word(id="w2", text="world", start_time=0.5, end_time=1.0)], start_time=0.0, end_time=1.0)
        correction_result = CorrectionResult(
            original_segments=[seg],
            corrected_segments=[seg],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )
        # Minimal OutputConfig via helper
        transcriber_config, lyrics_config, output_config = None, None, create_test_output_config(
            output_dir=tmp_path_factory.mktemp("out"), cache_dir=tmp_path_factory.mktemp("cache"), render_video=False
        )

        server = ReviewServer(
            correction_result=correction_result,
            output_config=output_config,
            audio_filepath="",
            logger=None,
        )

        th = threading.Thread(target=lambda: __import__("uvicorn").run(server.app, host="127.0.0.1", port=8000, log_level="error"), daemon=True)
        th.start()
        # Wait briefly for server
        time.sleep(0.5)
        try:
            requests.get("http://localhost:8000/api/ping", timeout=1)
        except Exception:
            pass
        yield
    except Exception:
        # If server can't start (e.g., missing frontend assets), continue tests
        yield
