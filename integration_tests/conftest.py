import pytest
import os
from lyrics_transcriber.core.controller import TranscriberConfig, LyricsConfig, LyricsTranscriber
from tests.test_helpers import create_test_output_config


@pytest.fixture
def test_audio_file():
    return os.path.join(os.path.dirname(__file__), "fixtures", "audio_samples", "sample1.mp3")


@pytest.fixture
def mock_configs():
    transcriber_config = TranscriberConfig(audioshake_api_token="test_token", runpod_api_key="test_key", whisper_runpod_id="test_id")

    lyrics_config = LyricsConfig(genius_api_token="test_token", spotify_cookie="test_cookie")

    output_config = create_test_output_config(output_dir="test_output", cache_dir="test_cache")

    return transcriber_config, lyrics_config, output_config


@pytest.fixture
def transcriber(test_audio_file, mock_configs):
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
