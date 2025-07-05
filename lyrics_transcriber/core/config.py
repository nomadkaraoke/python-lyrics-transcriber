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
    rapidapi_key: Optional[str] = None
    spotify_cookie: Optional[str] = None
    lyrics_file: Optional[str] = None

@dataclass
class OutputConfig:
    """Configuration for output generation."""

    output_styles_json: str
    max_line_length: int = 36
    styles: Dict[str, Any] = field(default_factory=dict)
    output_dir: Optional[str] = os.getcwd()
    cache_dir: str = os.getenv(
        "LYRICS_TRANSCRIBER_CACHE_DIR",
        os.path.join(os.path.expanduser("~"), "lyrics-transcriber-cache")
    )

    fetch_lyrics: bool = True
    run_transcription: bool = True
    run_correction: bool = True
    enable_review: bool = True

    generate_plain_text: bool = True
    generate_lrc: bool = True
    generate_cdg: bool = True
    render_video: bool = True
    video_resolution: str = "360p"
    subtitle_offset_ms: int = 0
