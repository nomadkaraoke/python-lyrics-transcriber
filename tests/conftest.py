import pytest
import logging
import shutil
import os
import tempfile
import sys

# Add the project root to the path so we can import from the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# All tests are now working! No more skip patterns needed.
SKIP_PATTERNS = []

def pytest_collection_modifyitems(config, items):
    for item in items:
        # Check if any test path pattern matches the current test
        for pattern in SKIP_PATTERNS:
            if pattern in item.nodeid:
                item.add_marker(pytest.mark.skip(reason="Skipped due to codebase changes"))
                break


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
    """Run the test suite with coverage reporting."""
    import pytest
    sys.exit(pytest.main(["-xvs", "--cov=lyrics_transcriber", "--cov-report=term", "--cov-report=html"]))


if __name__ == "__main__":
    main()
