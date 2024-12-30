import pytest
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig


class TestLyricsProviderConfig:
    def test_default_config(self):
        config = LyricsProviderConfig()
        assert config.genius_api_token is None
        assert config.spotify_cookie is None

    def test_custom_config(self):
        config = LyricsProviderConfig(genius_api_token="test_token", spotify_cookie="test_cookie")
        assert config.genius_api_token == "test_token"
        assert config.spotify_cookie == "test_cookie"
