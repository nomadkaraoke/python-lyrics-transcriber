# Lyrics Transcriber 🎶

![PyPI - Version](https://img.shields.io/pypi/v/lyrics-transcriber)
![Python Version](https://img.shields.io/badge/python-3.10+-blue)
[![Tests](https://github.com/nomadkaraoke/python-lyrics-transcriber/actions/workflows/test-and-publish.yml/badge.svg)](https://github.com/nomadkaraoke/python-lyrics-transcriber/actions/workflows/test-and-publish.yml)
[![Coverage](https://codecov.io/gh/nomadkaraoke/python-lyrics-transcriber/graph/badge.svg?token=SMW2TVPVNT)](https://codecov.io/gh/nomadkaraoke/python-lyrics-transcriber)

Automatically create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps, using OpenAI Whisper and lyrics from Genius and Spotify, for convenience in use cases such as karaoke video production.

## Features 🌟

- Automatically transcribe lyrics with word-level timestamps.
- Outputs lyrics in ASS and MidiCo LRC formats.
- Can fetch lyrics from with Genius and Spotify.
- Command Line Interface (CLI) for easy usage.
- Can be included and used in other Python projects.

## Installation 🛠️

### Prerequisites

- Python 3.10 or higher
- [Optional] Genius API token if you want to fetch lyrics from Genius
- [Optional] Spotify cookie value if you want to fetch lyrics from Spotify
- [Optional] OpenAI API token if you want to use LLM correction of the transcribed lyrics
- [Optional] AudioShake API token if you want to use a much higher quality (but paid) API for lyrics transcription

```
pip install lyrics-transcriber
```

> **Warning**
> The package published to PyPI was created by manually editing `poetry.lock` to remove [triton](https://github.com/openai/triton), as it is technically a sub-dependency from openai-whisper but is currently only supported on Linux (whisper still works fine without it, and I want this package to be usable on any platform)

## Docker

You can use the pre-built container image `beveradb/lyrics-transcriber:0.16.0` on Docker hub if you want, here's an example:

```sh
docker run \
 -v `pwd`/input:/input \
 -v `pwd`/output:/output \
beveradb/lyrics-transcriber:0.16.0 \
 --log_level debug \
 --output_dir /output \
 --render_video \
 --video_background_image /input/your-background-image.png \
 --video_resolution 360p \
 /input/song.flac
```

## Usage 🚀

### As a standalone CLI

1. To transcribe lyrics from an audio file:

```
lyrics-transcriber /path/to/your/audiofile.mp3
```

2. To specify Genius API token, song artist, and song title for auto-correction:

```
lyrics-transcriber /path/to/your/audiofile.mp3 --genius_api_token YOUR_API_TOKEN --artist "Artist Name" --title "Song Title"
```

### As a Python package in your project

1. Import LyricsTranscriber in your Python script:

```
from lyrics_transcriber import LyricsTranscriber
```

1. Create an instance and use it:

```
transcriber = LyricsTranscriber(audio_filepath='path_to_audio.mp3')
result_metadata = transcriber.generate()
```

result_metadata contains values as such:
```
result_metadata = {
    "whisper_json_filepath": str,
    "genius_lyrics": str,
    "genius_lyrics_filepath": str,
    "midico_lrc_filepath": str,
    "singing_percentage": int,
    "total_singing_duration": int,
    "song_duration": int,
}
```

## Requirements 📋

 - Python >= 3.9
 - Python Poetry
 - Dependencies are listed in pyproject.toml

## Local Development 💻

To work on the Lyrics Transcriber project locally, you need Python 3.9 or higher. It's recommended to create a virtual environment using poetry.

 1. Clone the repo and cd into it.
 2. Install poetry if you haven’t already.
 3. Run poetry install to install the dependencies.
 4. Run poetry shell to activate the virtual environment.

## Contributing 🤝

Contributions are very much welcome! Please fork the repository and submit a pull request with your changes, and I'll try to review, merge and publish promptly!

- This project is 100% open-source and free for anyone to use and modify as they wish. 
- If the maintenance workload for this repo somehow becomes too much for me I'll ask for volunteers to share maintainership of the repo, though I don't think that is very likely

## License 📄

This project is licensed under the MIT [License](LICENSE).

## Credits 🙏

- This project uses [OpenAI Whisper](https://github.com/openai/whisper) for transcription, which inspired the entire tool!
- Thanks to @linto-ai for the [whisper-timestamped](https://github.com/linto-ai/whisper-timestamped) project which solved a big chunk for me.
- Thanks to Genius for providing an API which makes fetching lyrics easier!

## Contact 💌

For questions or feedback, please raise an issue or reach out to @beveradb ([Andrew Beveridge](mailto:andrew@beveridge.uk)) directly.
