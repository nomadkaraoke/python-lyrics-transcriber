#!/usr/bin/env python
import argparse
import logging
import pkg_resources
from lyrics_transcriber import LyricsTranscriber


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter("%(asctime)s - %(module)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    logger.debug("Parsing CLI args")

    parser = argparse.ArgumentParser(
        description="Create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps, from any input song file"
    )

    parser.add_argument("audio_filepath", nargs="?", help="The audio file path to transcribe lyrics for.", default=argparse.SUPPRESS)

    parser.add_argument(
        "--song_artist",
        default=None,
        help="Optional: specify song artist for Genius lyrics lookup and auto-correction",
    )
    parser.add_argument(
        "--song_title",
        default=None,
        help="Optional: specify song title for Genius lyrics lookup and auto-correction",
    )
    parser.add_argument(
        "--genius_api_token",
        default=None,
        help="Optional: specify Genius API token for lyrics lookup and auto-correction",
    )

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

    if 1 <= [args.genius_api_token, args.song_title, args.song_artist].count(True) < 3:
        print(f"To use genius lyrics auto-correction, all 3 args genius_api_token, song_artist, song_title must be provided")
        print(args)
        exit(1)

    logger.debug("Loading LyricsTranscriber class")

    transcriber = LyricsTranscriber(
        args.audio_filepath,
        genius_api_token=args.genius_api_token,
        song_artist=args.song_artist,
        song_title=args.song_title,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
    )

    result_metadata = transcriber.generate()

    logger.info(f"*** Success! ***")

    formatted_duration = f'{int(result_metadata["song_duration"] // 60):02d}:{int(result_metadata["song_duration"] % 60):02d}'
    logger.info(f"Total Song Duration: {formatted_duration}")

    formatted_singing_duration = (
        f'{int(result_metadata["total_singing_duration"] // 60):02d}:{int(result_metadata["total_singing_duration"] % 60):02d}'
    )
    logger.info(f"Total Singing Duration: {formatted_singing_duration}")
    logger.info(f"Singing Percentage: {result_metadata['singing_percentage']}%")

    logger.info(f"*** Outputs: ***")
    logger.info(f"Whisper transcription output JSON file: {result_metadata['whisper_json_filepath']}")
    logger.info(f"MidiCo LRC output file: {result_metadata['midico_lrc_filepath']}")
    logger.info(f"Genius lyrics output file: {result_metadata['genius_lyrics_filepath']}")


if __name__ == "__main__":
    main()
