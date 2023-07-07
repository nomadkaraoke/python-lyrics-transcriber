#!/usr/bin/env python
import argparse
import logging
import pkg_resources
from lyrics_transcriber import LyricsTranscriber


def main():
    logger = logging.getLogger(__name__)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    logger.debug("Parsing CLI args")

    parser = argparse.ArgumentParser(
        description="Create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps, from any input song file",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=40),
    )

    parser.add_argument("audio_filepath", nargs="?", help="The audio file path to transcribe lyrics for.", default=argparse.SUPPRESS)

    package_version = pkg_resources.get_distribution("lyrics-transcriber").version
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {package_version}")
    parser.add_argument("--log_level", default="INFO", help="Optional: Logging level, e.g. info, debug, warning. Default: INFO")

    parser.add_argument(
        "--artist",
        default=None,
        help="Optional: song artist for lyrics lookup and auto-correction",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional: song title for lyrics lookup and auto-correction",
    )
    parser.add_argument(
        "--genius_api_token",
        default=None,
        help="Optional: Genius API token for lyrics fetching. Can also be set with GENIUS_API_TOKEN env var.",
    )
    parser.add_argument(
        "--spotify_cookie",
        default=None,
        help="Optional: Spotify sp_dc cookie value for lyrics fetching. Can also be set with SPOTIFY_COOKIE_SP_DC env var.",
    )

    parser.add_argument(
        "--cache_dir",
        default="/tmp/lyrics-transcriber-cache/",
        help="Optional: directory to cache files downloaded or generated during execution",
    )

    parser.add_argument(
        "--output_dir",
        default=None,
        help="Optional: directory where the output lyrics files will be saved. Default: current directory",
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)

    if not hasattr(args, "audio_filepath"):
        parser.print_help()
        exit(1)

    if 1 <= [args.genius_api_token, args.title, args.artist].count(True) < 3:
        print(f"To use genius lyrics auto-correction, all 3 args genius_api_token, artist, title must be provided")
        print(args)
        exit(1)

    logger.debug("Loading LyricsTranscriber class")

    transcriber = LyricsTranscriber(
        args.audio_filepath,
        genius_api_token=args.genius_api_token,
        spotify_cookie=args.spotify_cookie,
        artist=args.artist,
        title=args.title,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        log_formatter=log_formatter,
        log_level=log_level,
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
    logger.info(f"Spotify lyrics output file: {result_metadata['spotify_lyrics_filepath']}")


if __name__ == "__main__":
    main()
