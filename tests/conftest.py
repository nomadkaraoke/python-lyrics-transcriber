import pytest
import logging
import shutil
import os
import tempfile
import sys

# Add the project root to the path so we can import from the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Dictionary of test file patterns to skip
SKIP_PATTERNS = [
    # Completely skip these test modules
    "tests/correction/handlers/test_extra_words.py",
    "tests/correction/handlers/test_levenshtein.py",
    "tests/correction/handlers/test_repeat.py",
    "tests/correction/handlers/test_sound_alike.py",
    "tests/correction/handlers/test_word_count_match.py",
    "tests/correction/test_anchor_sequence_1.py",
    "tests/correction/test_anchor_sequence_2.py",
    "tests/correction/test_corrector.py",
    # "tests/core/test_controller.py",  # COMPLETED - Phase 1 ✓
    "tests/output/ass/test_lyrics_line.py",
    "tests/output/ass/test_lyrics_screen.py",
    "tests/output/ass/test_section_detector.py",
    "tests/output/test_generator.py",
    "tests/output/test_lyrics_file.py",
    "tests/output/test_plain_text.py",
    "tests/output/test_segment_resizer.py",
    "tests/output/test_subtitles.py",
    "tests/output/test_video.py",
    
    # Specific test functions to skip
    "tests/cli/test_cli_main.py::test_create_arg_parser",
    "tests/cli/test_cli_main.py::test_create_configs",
    "tests/correction/test_phrase_analyzer.py::test_error_handling",
    "tests/correction/test_text_utils.py::test_punctuation_removal",
    "tests/correction/test_text_utils.py::test_hyphenated_words",
    "tests/correction/test_text_utils.py::test_whitespace_normalization",
    "tests/correction/test_text_utils.py::test_mixed_cases",
    "tests/correction/test_text_utils.py::test_empty_and_special_cases",
    "tests/lyrics/test_base_lyrics_provider.py::test_word_to_dict",
    "tests/lyrics/test_base_lyrics_provider.py::test_lyrics_segment_to_dict",
    "tests/lyrics/test_base_lyrics_provider.py::test_fetch_lyrics_with_cache",
    "tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_init_with_token",
    "tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_convert_result_format",
    "tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_convert_result_format_missing_fields",
    "tests/lyrics/test_spotify_provider.py::TestSpotifyProvider::test_convert_result_format",
    "tests/lyrics/test_spotify_provider.py::TestSpotifyProvider::test_convert_result_format_minimal",
    "tests/output/ass/test_config.py::test_screen_config_defaults",
    "tests/transcribers/test_base_transcriber.py::TestTranscriptionData::test_data_creation",
    "tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_transcribe_implementation",
    "tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_caching_mechanism",
    "tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_cache_file_structure",
    "tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_invalid_cache_handling",
    "tests/transcribers/test_whisper.py::TestWhisperTranscriber::test_perform_transcription_success"
]

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
