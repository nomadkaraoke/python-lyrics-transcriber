# Lyrics Transcriber 🎶

![PyPI - Version](https://img.shields.io/pypi/v/lyrics-transcriber)
![Python Version](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
[![Tests](https://github.com/nomadkaraoke/python-lyrics-transcriber/actions/workflows/test-and-publish.yml/badge.svg)](https://github.com/nomadkaraoke/python-lyrics-transcriber/actions/workflows/test-and-publish.yml)
[![Coverage](https://codecov.io/gh/nomadkaraoke/python-lyrics-transcriber/graph/badge.svg?token=SMW2TVPVNT)](https://codecov.io/gh/nomadkaraoke/python-lyrics-transcriber)

Create synchronized karaoke assets from an audio file with word‑level timing: fetch lyrics, transcribe audio, auto‑correct against references, review in a web UI, and export ASS, LRC, CDG, and video.

### What this project is now
- **Modular pipeline** orchestrated by `LyricsTranscriber` with clear configs
- **Transcription** via AudioShake (preferred) and Whisper on RunPod (fallback)
- **Lyrics providers**: Genius, Spotify, Musixmatch, or a local file
- **Rule‑based correction** with optional **LLM‑assisted** gap fixes
- **Human review** server + frontend for iterative corrections and previews
- **Outputs**: original/corrected text, corrections JSON, LRC, ASS, CDG(+MP3/ZIP), and video

## Features
- **Multi-transcriber orchestration** with caching per audio hash
  - AudioShake API (priority 1)
  - Whisper via RunPod + Dropbox upload (priority 2)
- **Lyrics fetching** with caching per artist/title
  - Genius (token or RapidAPI) • Spotify (cookie or RapidAPI) • Musixmatch (RapidAPI) • Local file
- **Correction engine**
  - Anchor/gap detection, multiple rule handlers (word count, syllables, relaxed, punctuation, extend‑anchor)
  - Optional LLM handlers (Ollama local, or OpenRouter with `OPENROUTER_API_KEY`)
- **Review UI** (FastAPI) at `http://localhost:8000`
  - Edit corrections, toggle handlers, add lyrics sources, generate preview video
- **Countdown intro for karaoke** (enabled by default)
  - Automatically adds 3-second intro with "3... 2... 1..." for songs that start within 3 seconds
  - Pads audio with silence and shifts all timestamps accordingly
  - Helps karaoke singers prepare before vocals begin
  - Disable with `--skip_countdown`
- **Rich outputs**
  - Plain text (original/corrected), corrections `JSON`, `*.lrc` (MidiCo), `*.ass` (karaoke), `*.cdg` with `*.mp3` and ZIP, and MP4/MKV video
  - Subtitle offset, line wrapping, styles via JSON

## Install
```
pip install lyrics-transcriber
```

### System requirements
- Python 3.10–3.13
- FFmpeg (required for audio probe and video rendering)
- spaCy English model (phrase analyzer used by correction):
```
python -m spacy download en_core_web_sm
```

## Quick start (CLI)
Minimal run (transcribe + LRC/ASS, no video/CDG):
```bash
lyrics-transcriber /path/to/song.mp3 --skip_video --skip_cdg
```

Use AudioShake and auto‑fetch lyrics (Genius + artist/title):
```bash
export AUDIOSHAKE_API_TOKEN=...   # or pass --audioshake_api_token
export GENIUS_API_TOKEN=...
lyrics-transcriber /path/to/song.mp3 --artist "Artist" --title "Song"
```

Use Whisper on RunPod (fallback or standalone):
```bash
export RUNPOD_API_KEY=...
export WHISPER_RUNPOD_ID=...      # your RunPod endpoint ID
lyrics-transcriber /path/to/song.mp3 --skip_cdg --skip_video
```

Provide a local lyrics file instead of fetching:
```bash
lyrics-transcriber /path/to/song.mp3 --lyrics_file /path/to/lyrics.txt
```

Render video/CDG (requires a styles JSON file):
```bash
lyrics-transcriber /path/to/song.mp3 \
  --output_styles_json /path/to/styles.json \
  --video_resolution 1080p
```

### Common flags
- **Song identification**: `--artist`, `--title`, `--lyrics_file`
- **APIs**: `--audioshake_api_token`, `--genius_api_token`, `--spotify_cookie`, `--runpod_api_key`, `--whisper_runpod_id`
- **Output**: `--output_dir`, `--cache_dir`, `--output_styles_json`, `--subtitle_offset`
- **Feature toggles**: `--skip_lyrics_fetch`, `--skip_transcription`, `--skip_correction`, `--skip_plain_text`, `--skip_lrc`, `--skip_cdg`, `--skip_video`, `--skip_countdown`, `--video_resolution {4k,1080p,720p,360p}`

Run `lyrics-transcriber --help` for full usage.

## Environment variables
These are read automatically (CLI flags override):
- `AUDIOSHAKE_API_TOKEN`
- `GENIUS_API_TOKEN`, `RAPIDAPI_KEY`
- `SPOTIFY_COOKIE_SP_DC`
- `RUNPOD_API_KEY`, `WHISPER_RUNPOD_ID`
- `WHISPER_DROPBOX_APP_KEY`, `WHISPER_DROPBOX_APP_SECRET`, `WHISPER_DROPBOX_REFRESH_TOKEN`
- `OPENROUTER_API_KEY` (optional LLM handler)
- `LYRICS_TRANSCRIBER_CACHE_DIR` (default `~/lyrics-transcriber-cache`)

## Outputs
Generated files are written to `--output_dir` (default: CWD):
- `... (Lyrics Corrections).json` — full correction data and audit trail
- `... (Karaoke).ass` — styled karaoke subtitles (ASS)
- `... .lrc` — MidiCo compatible LRC
- `... (original).txt` and `... (corrected).txt` — plain text exports
- `... .cdg`, `... .mp3`, `... .zip` — CDG package (when enabled)
- `... (With Vocals).mkv` — video with lyrics overlay (when enabled)

Notes
- If no `--output_styles_json` is provided, CDG and video are disabled automatically.
- `--subtitle_offset` shifts all word timings (ms) for late/early subtitles.

## Review server (human‑in‑the‑loop)
If review is enabled (default), a local server starts during processing and opens the UI at `http://localhost:8000`:
- Inspect and adjust corrections
- Toggle correction handlers (rule‑based/LLM)
- Add another lyrics source (paste plain text)
- Generate a low‑res preview video on demand

Frontend assets are bundled when installed from PyPI. For local dev, build the frontend once if needed:
```
./scripts/build_frontend.sh
```

## Styles JSON (for CDG/Video)
Provide a JSON with at least a `karaoke` section (for video/ASS) and, if generating CDG, a `cdg` section. Example (minimal):
```json
{
  "karaoke": {
    "ass_name": "Karaoke",
    "font": "Oswald SemiBold",
    "font_path": "lyrics_transcriber/output/fonts/Oswald-SemiBold.ttf",
    "font_size": 120,
    "primary_color": "255,165,0",
    "secondary_color": "255,255,255",
    "outline_color": "0,0,0",
    "back_color": "0,0,0",
    "bold": true,
    "italic": false,
    "underline": false,
    "strike_out": false,
    "scale_x": 100,
    "scale_y": 100,
    "spacing": 0,
    "angle": 0,
    "border_style": 1,
    "outline": 3,
    "shadow": 0,
    "margin_l": 0,
    "margin_r": 0,
    "margin_v": 100,
    "encoding": 1,
    "background_color": "black",
    "max_line_length": 36,
    "top_padding": 180
  },
  "cdg": {
    "font": "Oswald SemiBold",
    "font_path": "lyrics_transcriber/output/fonts/Oswald-SemiBold.ttf"
  }
}
```

## Using as a library
```python
from lyrics_transcriber import LyricsTranscriber
from lyrics_transcriber.core.controller import TranscriberConfig, LyricsConfig, OutputConfig

transcriber = LyricsTranscriber(
    audio_filepath="/path/to/song.mp3",
    artist="Artist",            # optional
    title="Title",              # optional
    transcriber_config=TranscriberConfig(
        audioshake_api_token="...",         # or env
        runpod_api_key="...", whisper_runpod_id="..."
    ),
    lyrics_config=LyricsConfig(
        genius_api_token="...", spotify_cookie="...", rapidapi_key="...",
        lyrics_file=None
    ),
    output_config=OutputConfig(
        output_dir="./out", cache_dir="~/lyrics-transcriber-cache",
        output_styles_json="/path/to/styles.json",  # required for CDG/video
        video_resolution="1080p", subtitle_offset_ms=0,
        add_countdown=True  # enable countdown for songs starting within 3s (default: True)
    ),
)

result = transcriber.process()
print(result.ass_filepath, result.lrc_filepath, result.video_filepath)

# Check if countdown padding was added (useful for syncing other audio files)
if result.countdown_padding_added:
    print(f"Countdown padding added: {result.countdown_padding_seconds}s")
    print(f"Padded audio filepath: {result.padded_audio_filepath}")
    # You can use this info to apply the same padding to instrumental tracks
```

## Docker
Build and run locally (includes FFmpeg and spaCy model):
```bash
docker build -t lyrics-transcriber:local .
docker run --rm -v "$PWD/input":/input -v "$PWD/output":/output \
  -e AUDIOSHAKE_API_TOKEN -e GENIUS_API_TOKEN -e RUNPOD_API_KEY -e WHISPER_RUNPOD_ID \
  lyrics-transcriber:local \
  --output_dir /output --skip_cdg --video_resolution 360p /input/song.mp3
```

## Development
- Python 3.10–3.13, Poetry
- Install deps: `poetry install`
- Run tests: `poetry run pytest`
- Build frontend (if editing UI): `./scripts/build_frontend.sh`

## Agentic AI (Experimental)

Uses **LangChain + LangGraph** for AI-powered lyrics correction with automatic **Langfuse** observability.

### Enabling
- CLI flags: `--use-agentic-ai` and `--ai-model provider/model`
- Or env: `USE_AGENTIC_AI=1`, `AGENTIC_AI_MODEL=ollama/gpt-oss:latest`

### Model Format
Models use `provider/model` format for LangChain:
- **Ollama** (local): `ollama/gpt-oss:latest`, `ollama/llama3.2:latest`
- **OpenAI**: `openai/gpt-4`, `openai/gpt-4-turbo`
- **Anthropic**: `anthropic/claude-3-sonnet-20240229`, `anthropic/claude-3-opus-20240229`

### Provider Configuration
- **API Keys**: Set provider-specific keys:
  - OpenAI: `OPENAI_API_KEY`
  - Anthropic: `ANTHROPIC_API_KEY`
- **Local/Privacy Mode**: `PRIVACY_MODE=1` (uses Ollama only)
- **Timeouts/Retries**: `AGENTIC_TIMEOUT_SECONDS=30`, `AGENTIC_MAX_RETRIES=2`
- **Circuit Breaker**: `AGENTIC_CIRCUIT_THRESHOLD=3`, `AGENTIC_CIRCUIT_OPEN_SECONDS=60`

### Observability (Langfuse)
Automatic tracing via LangChain callbacks - just set:
```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://us.cloud.langfuse.com"  # or https://cloud.langfuse.com for EU
```

Traces include:
- Full prompts and responses
- Token counts and latency
- Cost estimates (for paid APIs)
- Model performance metrics

View metrics: `GET /api/v1/metrics`

### Feedback Store
- SQLite DB persisted in cache dir (sessions, feedback)
- 3-year retention policy with automatic cleanup

### Architecture
See `LANGCHAIN_MIGRATION.md` for details on the LangChain/LangGraph implementation.

## License
MIT. See `LICENSE`.

## Credits
- Audio transcription by AudioShake and Whisper (RunPod)
- Lyrics via Genius, Spotify, Musixmatch; layout via `karaoke-lyrics-processor`
- UI/API: FastAPI, Vite/React frontend

## Support
Please open issues or PRs on the repo, or contact @beveradb.
