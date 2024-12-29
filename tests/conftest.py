import pytest
import logging
from pathlib import Path

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