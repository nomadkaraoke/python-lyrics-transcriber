import pytest
from unittest.mock import Mock, patch, mock_open, call
import os
import subprocess
from lyrics_transcriber.output.generator import OutputGenerator, OutputGeneratorConfig, OutputPaths
from lyrics_transcriber.core.corrector import CorrectionResult
from lyrics_transcriber.transcribers.base_transcriber import LyricsSegment, Word


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def config():
    return OutputGeneratorConfig(
        output_dir="/test/output", cache_dir="/test/cache", video_resolution="360p", video_background_color="black"
    )


@pytest.fixture
def generator(config, mock_logger):
    return OutputGenerator(config=config, logger=mock_logger)


@pytest.fixture
def sample_transcription_data():
    segments = [
        LyricsSegment(
            text="Line 1",
            words=[
                Word(text="Line", start_time=1.0, end_time=1.5, confidence=1.0),
                Word(text="1", start_time=1.5, end_time=2.0, confidence=1.0),
            ],
            start_time=1.0,
            end_time=2.0,
        ),
        LyricsSegment(
            text="Line 2",
            words=[
                Word(text="Line", start_time=3.0, end_time=3.5, confidence=1.0),
                Word(text="2", start_time=3.5, end_time=4.0, confidence=1.0),
            ],
            start_time=3.0,
            end_time=4.0,
        ),
    ]
    return CorrectionResult(segments=segments, text="Line 1 Line 2", confidence=1.0, corrections_made=0, source_mapping={}, metadata={})


class TestOutputGenerator:
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = OutputGeneratorConfig(output_dir="/test/output", cache_dir="/test/cache")
        generator = OutputGenerator(config=config)
        assert generator.config is not None
        assert generator.logger is not None
        assert generator.video_resolution_num == (640, 360)
        assert generator.font_size == 50
        assert generator.line_height == 50

    def test_init_with_invalid_resolution(self):
        """Test initialization with invalid video resolution."""
        with pytest.raises(ValueError, match="Invalid video_resolution value"):
            config = OutputGeneratorConfig(output_dir="/test/output", cache_dir="/test/cache", video_resolution="invalid")
            OutputGenerator(config=config)

    def test_get_output_path(self, generator):
        path = generator._get_output_path("test", "lrc")
        assert path == "/test/output/test.lrc"

    def test_get_output_path_fallback_to_cache(self, mock_logger):
        """Test output path fallback to cache directory."""
        # Create config with both directories set
        config = OutputGeneratorConfig(
            output_dir="/test/output",
            cache_dir="/test/cache"
        )
        generator = OutputGenerator(config=config, logger=mock_logger)
        
        # Test fallback by temporarily setting output_dir to None
        original_output_dir = generator.config.output_dir
        generator.config.output_dir = None
        try:
            path = generator._get_output_path("test", "lrc")
            assert path == "/test/cache/test.lrc"
        finally:
            # Restore the original output_dir
            generator.config.output_dir = original_output_dir

    @patch("builtins.open", new_callable=mock_open)
    def test_write_lrc_file(self, mock_file, generator, sample_transcription_data):
        generator._write_lrc_file("test.lrc", sample_transcription_data.segments)

        expected_calls = [call("[00:01.00]Line 1\n"), call("[00:03.00]Line 2\n")]
        mock_file().write.assert_has_calls(expected_calls)

    @patch("builtins.open", new_callable=mock_open)
    def test_write_ass_file(self, mock_file, generator, sample_transcription_data):
        generator._write_ass_file("test.ass", sample_transcription_data.segments)

        mock_file().write.assert_called()
        # Verify header was written
        assert "Script Info" in mock_file().write.call_args_list[0][0][0]
        # Verify segments were written
        calls = mock_file().write.call_args_list
        assert any("Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Line 1" in str(call) for call in calls)
        assert any("Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,Line 2" in str(call) for call in calls)

    def test_build_ffmpeg_command_with_background_color(self, generator):
        cmd = generator._build_ffmpeg_command("sub.ass", "audio.mp3", "output.mp4")
        assert cmd[0] == "ffmpeg"
        assert "-f" in cmd
        assert "lavfi" in cmd
        assert any("color=c=black" in arg for arg in cmd)

    def test_build_ffmpeg_command_with_background_image(self, generator):
        generator.config.video_background_image = "bg.jpg"
        cmd = generator._build_ffmpeg_command("sub.ass", "audio.mp3", "output.mp4")
        assert "-i" in cmd
        assert "bg.jpg" in cmd

    @patch("subprocess.run")
    def test_run_ffmpeg_command_success(self, mock_run, generator):
        cmd = ["ffmpeg", "-test"]
        generator._run_ffmpeg_command(cmd)
        mock_run.assert_called_once_with(cmd, check=True)

    @patch("subprocess.run")
    def test_run_ffmpeg_command_failure(self, mock_run, generator):
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        with pytest.raises(subprocess.CalledProcessError):
            generator._run_ffmpeg_command(["ffmpeg"])

    def test_format_lrc_timestamp(self, generator):
        assert generator._format_lrc_timestamp(61.5) == "01:01.50"
        assert generator._format_lrc_timestamp(3600) == "60:00.00"

    def test_format_ass_timestamp(self, generator):
        assert generator._format_ass_timestamp(61.5) == "0:01:01.50"
        assert generator._format_ass_timestamp(3661.5) == "1:01:01.50"

    @patch.object(OutputGenerator, "_write_lrc_file")
    def test_generate_lrc(self, mock_write, generator, sample_transcription_data):
        result = generator.generate_lrc(sample_transcription_data, "test")
        assert result == "/test/output/test.lrc"
        mock_write.assert_called_once()

    @patch.object(OutputGenerator, "_write_ass_file")
    def test_generate_ass(self, mock_write, generator, sample_transcription_data):
        result = generator.generate_ass(sample_transcription_data, "test")
        assert result == "/test/output/test.ass"
        mock_write.assert_called_once()

    @patch.object(OutputGenerator, "_run_ffmpeg_command")
    def test_generate_video(self, mock_run, generator):
        result = generator.generate_video("sub.ass", "audio.mp3", "test")
        assert result == "/test/output/test.mp4"
        mock_run.assert_called_once()

    def test_generate_outputs(self, generator, sample_transcription_data):
        with patch.multiple(
            OutputGenerator,
            generate_lrc=Mock(return_value="test.lrc"),
            generate_ass=Mock(return_value="test.ass"),
            generate_video=Mock(return_value="test.mp4"),
        ):

            result = generator.generate_outputs(sample_transcription_data, "test", "audio.mp3", render_video=True)

            assert isinstance(result, OutputPaths)
            assert result.lrc == "test.lrc"
            assert result.ass == "test.ass"
            assert result.video == "test.mp4"

    def test_generate_outputs_error_handling(self, generator, sample_transcription_data):
        with patch.object(OutputGenerator, "generate_lrc", side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                generator.generate_outputs(sample_transcription_data, "test", "audio.mp3")

    @pytest.mark.parametrize(
        "resolution,expected",
        [
            ("4k", ((3840, 2160), 250, 250)),
            ("1080p", ((1920, 1080), 120, 120)),
            ("720p", ((1280, 720), 100, 100)),
            ("360p", ((640, 360), 50, 50)),
        ],
    )
    def test_get_video_params(self, generator, resolution, expected):
        assert generator._get_video_params(resolution) == expected

    def test_init_with_nonexistent_background_image(self):
        """Test initialization with non-existent background image."""
        with pytest.raises(FileNotFoundError, match="Video background image not found"):
            OutputGeneratorConfig(output_dir="/test/output", cache_dir="/test/cache", video_background_image="/nonexistent/image.jpg")

    @patch("builtins.open")
    def test_generate_lrc_file_error(self, mock_open, generator, sample_transcription_data):
        """Test error handling in LRC file generation."""
        mock_open.side_effect = IOError("Permission denied")

        with pytest.raises(IOError, match="Permission denied"):
            generator.generate_lrc(sample_transcription_data, "test")

        generator.logger.error.assert_called_with("Failed to generate LRC file: Permission denied")

    @patch("builtins.open")
    def test_generate_ass_file_error(self, mock_open, generator, sample_transcription_data):
        """Test error handling in ASS file generation."""
        mock_open.side_effect = IOError("Permission denied")

        with pytest.raises(IOError, match="Permission denied"):
            generator.generate_ass(sample_transcription_data, "test")

        generator.logger.error.assert_called_with("Failed to generate ASS file: Permission denied")

    @patch("subprocess.run")
    def test_generate_video_error(self, mock_run, generator):
        """Test error handling in video generation."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["ffmpeg"], "FFmpeg error")

        with pytest.raises(subprocess.CalledProcessError):
            generator.generate_video("sub.ass", "audio.mp3", "test")

        generator.logger.error.assert_called_with("Failed to generate video: Command '['ffmpeg']' returned non-zero exit status 1.")
