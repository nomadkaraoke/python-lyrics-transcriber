#!/usr/bin/env python
import argparse
import datetime
import pkg_resources
from lyrics_transcriber import LyricsTranscriber


def main():
    parser = argparse.ArgumentParser(
        description="Create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps, from any input song file"
    )

    parser.add_argument("audio_file", nargs="?", help="The audio file path to transcribe lyrics for.", default=argparse.SUPPRESS)
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

    if not hasattr(args, "audio_file"):
        parser.print_help()
        exit(1)

    log(f"LyricsTranscriber instantiating with input file: {args.audio_file}")

    transcriber = LyricsTranscriber(args.audio_file, output_dir=args.output_dir, cache_dir=args.cache_dir)

    log("LyricsTranscriber beginning transcription")
    whisper_json_filepath, genius_lyrics_filepath, midico_lrc_filepath = transcriber.transcribe()

    print(f"Transcription complete! Output files: {whisper_json_filepath} {genius_lyrics_filepath} {midico_lrc_filepath}")


def log(message):
    timestamp = datetime.datetime.now().isoformat()
    print(f"{timestamp} - {message}")


if __name__ == "__main__":
    main()
