import pytest
import logging
from pathlib import Path
import shutil
import os
import tempfile


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a dummy audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"dummy audio content")
    return str(audio_file)


@pytest.fixture
def test_logger():
    """Create a logger for testing."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_directories():
    """Clean up test directories after all tests complete."""
    yield  # Run all tests first

    # Clean up test_cache in temp directory
    cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-test-cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    # Clean up local test_cache
    if os.path.exists("test_cache"):
        shutil.rmtree("test_cache")

    # Clean up test_output
    if os.path.exists("test_output"):
        shutil.rmtree("test_output")


def main():
    """Entry point for coverage testing."""
    import pytest

    pytest.main(["--cov=lyrics_transcriber", "--cov-report=term-missing"])
