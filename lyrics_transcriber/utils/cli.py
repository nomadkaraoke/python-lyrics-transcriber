#!/usr/bin/env python
import argparse
import datetime
import pkg_resources
from lyrics_transcriber import LyricsTranscriber


def log(message):
    timestamp = datetime.datetime.now().isoformat()
    print(f"{timestamp} - {message}")


def main():
    parser = argparse.ArgumentParser(
        description="Create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps, from any input song file"
    )

    parser.add_argument("audio_filepath", nargs="?", help="The audio file path to transcribe lyrics for.", default=argparse.SUPPRESS)
    parser.add_argument("--cache_dir", default="/tmp/lyrics-transcriber-cache/", help="Optional cache directory.")
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Optional directory where the resulting lyrics files will be saved. If not specified, outputs to current dir.",
    )
    parser.add_argument("--version", action="store_true", help="Show the version number and exit")

    args = parser.parse_args()

    if args.version:
        version = pkg_resources.get_distribution("lyrics-transcriber").version
        print(f"lyrics-transcriber version: {version}")
        exit(0)

    if not hasattr(args, "audio_filepath"):
        parser.print_help()
        exit(1)

    transcriber = LyricsTranscriber(args.audio_filepath, output_dir=args.output_dir, cache_dir=args.cache_dir)

    log("LyricsTranscriber beginning transcription")

    result_metadata = transcriber.generate()

    log(f"*** Success! ***")

    formatted_duration = f'{int(result_metadata["song_duration"] // 60):02d}:{int(result_metadata["song_duration"] % 60):02d}'
    log(f"Total Song Duration: {formatted_duration}")

    formatted_singing_duration = (
        f'{int(result_metadata["total_singing_duration"] // 60):02d}:{int(result_metadata["total_singing_duration"] % 60):02d}'
    )
    log(f"Total Singing Duration: {formatted_singing_duration}")
    log(f"Singing Percentage: {result_metadata['singing_percentage']}")

    log(f"*** Outputs: ***")
    log(f"Whisper transcription output JSON file: {result_metadata['whisper_json_filepath']}")
    log(f"MidiCo LRC output file: {result_metadata['midico_lrc_filepath']}")
    log(f"Genius lyrics output file: {result_metadata['genius_lyrics_filepath']}")


if __name__ == "__main__":
    main()
