import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from lyrics_transcriber.cli.main import create_arg_parser, create_configs, validate_args, setup_logging, get_config_from_env, main


def test_create_arg_parser():
    parser = create_arg_parser()
    assert parser is not None

    # Test parsing of various arguments
    args = parser.parse_args(["test.mp3", "--artist", "Test Artist", "--title", "Test Song"])
    assert args.audio_filepath == "test.mp3"
    assert args.artist == "Test Artist"
    assert args.title == "Test Song"

    # Test default values
    args = parser.parse_args(["test.mp3"])
    assert args.log_level == "INFO"
    assert args.video_resolution == "360p"
    assert args.video_background_color == "black"
    assert args.cache_dir == Path("/tmp/lyrics-transcriber-cache/")
    assert not args.render_video


def test_validate_args_no_audio_file(capsys, test_logger):
    parser = create_arg_parser()
    args = parser.parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        validate_args(args, parser, test_logger)
    assert exc_info.value.code == 1


def test_validate_args_missing_title(sample_audio_file, test_logger):
    parser = create_arg_parser()
    args = parser.parse_args([sample_audio_file, "--artist", "Test Artist"])

    with pytest.raises(SystemExit) as exc_info:
        validate_args(args, parser, test_logger)
    assert exc_info.value.code == 1


def test_validate_args_nonexistent_file(test_logger):
    parser = create_arg_parser()
    args = parser.parse_args(["nonexistent.mp3"])

    with pytest.raises(SystemExit) as exc_info:
        validate_args(args, parser, test_logger)
    assert exc_info.value.code == 1


def test_validate_args_valid(sample_audio_file, test_logger):
    parser = create_arg_parser()
    args = parser.parse_args([sample_audio_file, "--artist", "Test Artist", "--title", "Test Song"])

    # Should not raise any exceptions
    validate_args(args, parser, test_logger)


def test_setup_logging():
    logger = setup_logging("DEBUG")
    assert logger.level == 10  # DEBUG level

    logger = setup_logging("INFO")
    assert logger.level == 20  # INFO level

    # Test formatter
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert handler.formatter is not None
    assert "%(asctime)s.%(msecs)03d" in handler.formatter._fmt


@patch("os.getenv")
def test_get_config_from_env(mock_getenv):
    # Setup mock environment variables
    mock_getenv.side_effect = lambda x: {
        "AUDIOSHAKE_API_TOKEN": "test_audioshake",
        "GENIUS_API_TOKEN": "test_genius",
        "SPOTIFY_COOKIE_SP_DC": "test_spotify",
        "RUNPOD_API_KEY": "test_runpod",
        "WHISPER_RUNPOD_ID": "test_whisper",
    }.get(x)

    config = get_config_from_env()

    assert config["audioshake_api_token"] == "test_audioshake"
    assert config["genius_api_token"] == "test_genius"
    assert config["spotify_cookie"] == "test_spotify"
    assert config["runpod_api_key"] == "test_runpod"
    assert config["whisper_runpod_id"] == "test_whisper"


def test_create_configs():
    parser = create_arg_parser()
    args = parser.parse_args(
        [
            "test.mp3",
            "--audioshake_api_token",
            "cli_audioshake",
            "--genius_api_token",
            "cli_genius",
            "--spotify_cookie",
            "cli_spotify",
            "--output_dir",
            "test_output",
            "--render_video",
            "--video_resolution",
            "1080p",
            "--video_background_color",
            "blue",
        ]
    )

    env_config = {
        "audioshake_api_token": "env_audioshake",
        "genius_api_token": "env_genius",
        "spotify_cookie": "env_spotify",
        "runpod_api_key": "env_runpod",
        "whisper_runpod_id": "env_whisper",
    }

    transcriber_config, lyrics_config, output_config = create_configs(args, env_config)

    # CLI args should take precedence over env vars
    assert transcriber_config.audioshake_api_token == "cli_audioshake"
    assert lyrics_config.genius_api_token == "cli_genius"
    assert lyrics_config.spotify_cookie == "cli_spotify"

    # Env vars should be used when CLI args aren't provided
    assert transcriber_config.runpod_api_key == "env_runpod"
    assert transcriber_config.whisper_runpod_id == "env_whisper"

    # Output config should reflect CLI args
    assert output_config.output_dir == "test_output"
    assert output_config.render_video is True
    assert output_config.video_resolution == "1080p"
    assert output_config.video_background_color == "blue"


@patch("lyrics_transcriber.cli.main.LyricsTranscriber")
def test_main_successful_run(mock_transcriber_class, sample_audio_file, test_logger):
    mock_transcriber = Mock()
    mock_transcriber_class.return_value = mock_transcriber

    # Setup mock results
    mock_results = Mock()
    mock_results.lrc_filepath = "output.lrc"
    mock_results.ass_filepath = "output.ass"
    mock_results.video_filepath = "output.mp4"
    mock_transcriber.process.return_value = mock_results

    # Run main with test arguments
    with patch("sys.argv", ["lyrics-transcriber", sample_audio_file]):
        main()

    # Verify transcriber was initialized and process was called
    mock_transcriber_class.assert_called_once()
    mock_transcriber.process.assert_called_once()


@patch("lyrics_transcriber.cli.main.LyricsTranscriber")
def test_main_error_handling(mock_transcriber_class, sample_audio_file):
    mock_transcriber = Mock()
    mock_transcriber_class.return_value = mock_transcriber
    mock_transcriber.process.side_effect = Exception("Test error")

    # Run main with test arguments
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["lyrics-transcriber", sample_audio_file]):
            main()

    assert exc_info.value.code == 1
