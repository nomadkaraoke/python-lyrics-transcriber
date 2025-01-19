import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TranscriberConfig:
    """Configuration for transcription services."""

    audioshake_api_token: Optional[str] = None
    runpod_api_key: Optional[str] = None
    whisper_runpod_id: Optional[str] = None


@dataclass
class LyricsConfig:
    """Configuration for lyrics services."""

    genius_api_token: Optional[str] = None
    spotify_cookie: Optional[str] = None


@dataclass
class OutputConfig:
    """Configuration for output generation."""

    output_styles_json: str
    max_line_length: int = 36
    styles: Dict[str, Any] = field(default_factory=dict)
    output_dir: Optional[str] = os.getcwd()
    cache_dir: str = os.getenv("LYRICS_TRANSCRIBER_CACHE_DIR", "/tmp/lyrics-transcriber-cache/")
    render_video: bool = False
    generate_cdg: bool = False
    video_resolution: str = "360p"
