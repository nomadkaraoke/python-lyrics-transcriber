#!/usr/bin/env python
import argparse
import logging
import os
from pathlib import Path
from typing import Dict
from importlib.metadata import version
from dotenv import load_dotenv

from lyrics_transcriber import LyricsTranscriber
from lyrics_transcriber.core.controller import TranscriberConfig, LyricsConfig, OutputConfig


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Create synchronised lyrics files in ASS and MidiCo LRC formats with word-level timestamps",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=52),
    )

    # Required arguments
    parser.add_argument(
        "audio_filepath",
        nargs="?",
        help="The audio file path to transcribe lyrics for.",
        default=argparse.SUPPRESS,
    )

    # Version
    package_version = version("lyrics-transcriber")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {package_version}")

    # Optional arguments
    parser.add_argument(
        "--log_level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level. Default: INFO"
    )

    # Song identification
    song_group = parser.add_argument_group("Song Identification")
    song_group.add_argument("--artist", help="Song artist for lyrics lookup and auto-correction")
    song_group.add_argument("--title", help="Song title for lyrics lookup and auto-correction")

    # API Credentials
    api_group = parser.add_argument_group("API Credentials")
    api_group.add_argument(
        "--audioshake_api_token", help="AudioShake API token for lyrics transcription. Can also use AUDIOSHAKE_API_TOKEN env var."
    )
    api_group.add_argument("--genius_api_token", help="Genius API token for lyrics fetching. Can also use GENIUS_API_TOKEN env var.")
    api_group.add_argument(
        "--spotify_cookie", help="Spotify sp_dc cookie value for lyrics fetching. Can also use SPOTIFY_COOKIE_SP_DC env var."
    )
    api_group.add_argument("--runpod_api_key", help="RunPod API key for Whisper transcription. Can also use RUNPOD_API_KEY env var.")
    api_group.add_argument(
        "--whisper_runpod_id", help="RunPod endpoint ID for Whisper transcription. Can also use WHISPER_RUNPOD_ID env var."
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--output_dir", type=Path, help="Directory where output files will be saved. Default: current directory")

    output_group.add_argument(
        "--cache_dir",
        type=Path,
        help="Directory to cache downloaded/generated files. Default: /tmp/lyrics-transcriber-cache/",
    )

    # Video options
    video_group = parser.add_argument_group("Video Options")
    video_group.add_argument("--render_video", action="store_true", help="Render a karaoke video with the generated lyrics")
    video_group.add_argument(
        "--video_resolution", choices=["4k", "1080p", "720p", "360p"], default="360p", help="Resolution of the karaoke video. Default: 360p"
    )
    video_group.add_argument("--video_background_image", type=Path, help="Image file to use for karaoke video background")
    video_group.add_argument(
        "--video_background_color",
        default="black",
        help="Color for karaoke video background (hex format or FFmpeg color name). Default: black",
    )

    return parser


def parse_args(parser: argparse.ArgumentParser, args_list: list[str] | None = None) -> argparse.Namespace:
    """Parse and process command line arguments."""
    # Use provided args_list for testing, otherwise use sys.argv
    args = parser.parse_args(args_list)

    # Set default cache_dir if not provided
    if not hasattr(args, "cache_dir") or args.cache_dir is None:
        args.cache_dir = Path(os.getenv("LYRICS_TRANSCRIBER_CACHE_DIR", "/tmp/lyrics-transcriber-cache/"))

    return args


def get_config_from_env() -> Dict[str, str]:
    """Load configuration from environment variables."""
    load_dotenv()
    return {
        "audioshake_api_token": os.getenv("AUDIOSHAKE_API_TOKEN"),
        "genius_api_token": os.getenv("GENIUS_API_TOKEN"),
        "spotify_cookie": os.getenv("SPOTIFY_COOKIE_SP_DC"),
        "runpod_api_key": os.getenv("RUNPOD_API_KEY"),
        "whisper_runpod_id": os.getenv("WHISPER_RUNPOD_ID"),
    }


def setup_logging(log_level: str) -> logging.Logger:
    """Configure logging with consistent format."""
    logger = logging.getLogger("lyrics_transcriber")
    log_level_enum = getattr(logging, log_level.upper())
    logger.setLevel(log_level_enum)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def create_configs(args: argparse.Namespace, env_config: Dict[str, str]) -> tuple[TranscriberConfig, LyricsConfig, OutputConfig]:
    """Create configuration objects from arguments and environment variables."""
    transcriber_config = TranscriberConfig(
        audioshake_api_token=args.audioshake_api_token or env_config.get("audioshake_api_token"),
        runpod_api_key=args.runpod_api_key or env_config.get("runpod_api_key"),
        whisper_runpod_id=args.whisper_runpod_id or env_config.get("whisper_runpod_id"),
    )

    lyrics_config = LyricsConfig(
        genius_api_token=args.genius_api_token or env_config.get("genius_api_token"),
        spotify_cookie=args.spotify_cookie or env_config.get("spotify_cookie"),
    )

    output_config = OutputConfig(
        output_dir=str(args.output_dir) if args.output_dir else os.getcwd(),
        cache_dir=str(args.cache_dir),
        render_video=args.render_video,
        video_resolution=args.video_resolution,
        video_background_image=str(args.video_background_image) if args.video_background_image else None,
        video_background_color=args.video_background_color,
    )

    return transcriber_config, lyrics_config, output_config


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser, logger: logging.Logger) -> None:
    """Validate command line arguments."""
    if not hasattr(args, "audio_filepath"):
        parser.print_help()
        logger.error("No audio filepath provided")
        exit(1)

    if not os.path.exists(args.audio_filepath):
        logger.error(f"Audio file not found: {args.audio_filepath}")
        exit(1)

    if args.artist and not args.title or args.title and not args.artist:
        logger.error("Both artist and title must be provided together")
        exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_arg_parser()
    args = parse_args(parser)

    # Set up logging first
    logger = setup_logging(args.log_level)

    # Validate arguments
    validate_args(args, parser, logger)

    # Load environment variables
    env_config = get_config_from_env()

    # Create configuration objects
    transcriber_config, lyrics_config, output_config = create_configs(args, env_config)

    try:
        # Initialize and run transcriber
        transcriber = LyricsTranscriber(
            audio_filepath=args.audio_filepath,
            artist=args.artist,
            title=args.title,
            transcriber_config=transcriber_config,
            lyrics_config=lyrics_config,
            output_config=output_config,
            logger=logger,
        )

        results = transcriber.process()

        # Log results
        logger.info("*** Success! ***")

        if results.lrc_filepath:
            logger.info(f"Generated LRC file: {results.lrc_filepath}")
        if results.ass_filepath:
            logger.info(f"Generated ASS file: {results.ass_filepath}")
        if results.video_filepath:
            logger.info(f"Generated video file: {results.video_filepath}")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        exit(1)
