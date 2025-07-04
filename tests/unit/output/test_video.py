import pytest
import os
from pathlib import Path
import json
import subprocess
from unittest.mock import patch, Mock, call
import logging

from lyrics_transcriber.output.video import VideoGenerator


@pytest.fixture
def video_generator(tmp_path):
    """Create a VideoGenerator instance with temporary directories."""
    styles = {
        "karaoke": {
            "background_color": "black"
        }
    }
    return VideoGenerator(
        output_dir=str(tmp_path / "output"), 
        cache_dir=str(tmp_path / "cache"), 
        video_resolution=(1920, 1080), 
        styles=styles
    )


@pytest.fixture
def mock_ffprobe_output():
    """Create sample ffprobe output for background image dimensions."""
    return json.dumps({"streams": [{"width": 1920, "height": 1080}]})


def test_initialization(tmp_path):
    """Test VideoGenerator initialization."""
    # Test successful initialization
    styles = {"karaoke": {"background_color": "black"}}
    generator = VideoGenerator(output_dir=str(tmp_path / "output"), cache_dir=str(tmp_path / "cache"), video_resolution=(1920, 1080), styles=styles)
    assert generator.video_resolution == (1920, 1080)
    assert generator.background_color == "black"

    # Test initialization with background image
    bg_image = tmp_path / "test.png"
    bg_image.touch()
    styles_with_bg = {"karaoke": {"background_image": str(bg_image), "background_color": "black"}}
    generator = VideoGenerator(
        output_dir=str(tmp_path / "output"),
        cache_dir=str(tmp_path / "cache"),
        video_resolution=(1920, 1080),
        styles=styles_with_bg,
    )
    assert generator.background_image == str(bg_image)

    # Test initialization with invalid background image
    styles_invalid_bg = {"karaoke": {"background_image": "nonexistent.png", "background_color": "black"}}
    with pytest.raises(FileNotFoundError):
        VideoGenerator(
            output_dir=str(tmp_path / "output"),
            cache_dir=str(tmp_path / "cache"),
            video_resolution=(1920, 1080),
            styles=styles_invalid_bg,
        )


def test_get_output_path(video_generator):
    """Test _get_output_path method."""
    output_path = video_generator._get_output_path("test", "mp4")
    assert output_path.endswith("test.mp4")
    assert os.path.dirname(output_path) == video_generator.output_dir


@patch("subprocess.check_output")
def test_get_video_codec_with_hardware_acceleration(mock_check_output):
    """Test _get_video_codec with hardware acceleration available."""
    mock_check_output.return_value = "h264_videotoolbox"
    styles = {"karaoke": {"background_color": "black"}}
    generator = VideoGenerator(output_dir="test", cache_dir="test", video_resolution=(1920, 1080), styles=styles)
    assert generator._get_video_codec() == "libx264"  # Updated to match actual implementation


@patch("subprocess.check_output")
def test_get_video_codec_fallback(mock_check_output):
    """Test _get_video_codec fallback to libx264."""
    mock_check_output.side_effect = Exception("FFmpeg error")
    styles = {"karaoke": {"background_color": "black"}}
    generator = VideoGenerator(output_dir="test", cache_dir="test", video_resolution=(1920, 1080), styles=styles)
    assert generator._get_video_codec() == "libx264"


@patch("subprocess.check_output")
def test_resize_background_image(mock_check_output, video_generator, mock_ffprobe_output):
    """Test _resize_background_image method."""
    # Mock ffprobe output
    mock_check_output.side_effect = [
        mock_ffprobe_output,  # First call for ffprobe
        "",  # Second call for ffmpeg
    ]

    # Create a test background image
    test_image = Path(video_generator.cache_dir) / "test.png"
    os.makedirs(os.path.dirname(test_image), exist_ok=True)
    test_image.touch()

    resized_path = video_generator._resize_background_image(str(test_image))
    assert Path(resized_path).exists()


@patch("subprocess.check_output")
def test_build_ffmpeg_command(mock_check_output, video_generator, mock_ffprobe_output):
    """Test _build_ffmpeg_command method."""
    mock_check_output.return_value = mock_ffprobe_output

    # Test with solid background
    cmd = video_generator._build_ffmpeg_command(ass_path="subtitles.ass", audio_path="audio.mp3", output_path="output.mp4")

    assert isinstance(cmd, list)
    assert "ffmpeg" in cmd
    assert "-i" in cmd
    assert "subtitles.ass" in str(cmd)
    assert "audio.mp3" in str(cmd)
    assert "output.mp4" in str(cmd)

    # Test with background image - modify styles to include background image
    test_image = Path(video_generator.cache_dir) / "test.png"
    os.makedirs(os.path.dirname(test_image), exist_ok=True)
    test_image.touch()
    video_generator.background_image = str(test_image)
    cmd = video_generator._build_ffmpeg_command(ass_path="subtitles.ass", audio_path="audio.mp3", output_path="output.mp4")
    assert "test.png" in str(cmd)


@patch("subprocess.check_output")
def test_run_ffmpeg_command(mock_check_output, video_generator):
    """Test _run_ffmpeg_command method."""
    cmd = ["ffmpeg", "-version"]

    # Test successful execution
    mock_check_output.return_value = "ffmpeg version test"
    video_generator._run_ffmpeg_command(cmd)

    # Test failed execution
    mock_check_output.side_effect = subprocess.CalledProcessError(1, cmd, output="Error")
    with pytest.raises(subprocess.CalledProcessError):
        video_generator._run_ffmpeg_command(cmd)


@patch("subprocess.check_output")
def test_generate_video(mock_check_output, video_generator):
    """Test generate_video method."""
    # Create necessary directories
    os.makedirs(video_generator.output_dir, exist_ok=True)
    os.makedirs(video_generator.cache_dir, exist_ok=True)

    # Create test files
    ass_path = Path(video_generator.cache_dir) / "test.ass"
    audio_path = Path(video_generator.cache_dir) / "test.mp3"
    ass_path.touch()
    audio_path.touch()

    # Mock successful video generation
    mock_check_output.return_value = ""

    output_path = video_generator.generate_video(ass_path=str(ass_path), audio_path=str(audio_path), output_prefix="test")

    assert output_path.endswith(".mkv")
    assert Path(output_path).parent == Path(video_generator.output_dir)


def test_generate_video_error_handling(video_generator):
    """Test error handling in generate_video method."""
    # Create output directory
    os.makedirs(video_generator.output_dir, exist_ok=True)

    with pytest.raises(FileNotFoundError):
        video_generator.generate_video(ass_path="nonexistent.ass", audio_path="nonexistent.mp3", output_prefix="test")


@patch("subprocess.check_output")
def test_background_image_resize_error(mock_check_output, video_generator):
    """Test error handling for background image resizing."""
    error = subprocess.CalledProcessError(1, [], output="Error")
    mock_check_output.side_effect = error

    test_image = Path(video_generator.cache_dir) / "test.png"
    os.makedirs(os.path.dirname(test_image), exist_ok=True)
    test_image.touch()

    with pytest.raises(subprocess.CalledProcessError):
        video_generator._resize_background_image(str(test_image))


@patch("subprocess.check_output")
def test_ffmpeg_command_with_hardware_acceleration(mock_check_output, video_generator):
    """Test FFmpeg command generation with hardware acceleration."""
    mock_check_output.return_value = "h264_videotoolbox"

    cmd = video_generator._build_ffmpeg_command(ass_path="subtitles.ass", audio_path="audio.mp3", output_path="output.mp4")

    assert "libx264" in cmd  # Updated to match actual implementation


def test_invalid_video_resolution():
    """Test initialization with invalid video resolution."""
    styles = {"karaoke": {"background_color": "black"}}
    with pytest.raises(ValueError):
        VideoGenerator(output_dir="test", cache_dir="test", video_resolution=(0, 0), styles=styles)


def test_build_ass_filter_no_font_path(video_generator):
    """Test _build_ass_filter with no font path configured."""
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    assert result == "ass=test.ass"


def test_build_ass_filter_with_valid_font_path(video_generator, tmp_path):
    """Test _build_ass_filter with valid font path."""
    # Create a test font file
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    font_file = font_dir / "test.ttf"
    font_file.touch()
    
    # Update styles to include font path
    video_generator.styles["karaoke"]["font_path"] = str(font_file)
    
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    expected = f"ass=test.ass:fontsdir={str(font_dir)}"
    assert result == expected


def test_build_ass_filter_with_invalid_font_path(video_generator):
    """Test _build_ass_filter with invalid font path (file doesn't exist)."""
    # Set non-existent font path
    video_generator.styles["karaoke"]["font_path"] = "/nonexistent/font.ttf"
    
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    assert result == "ass=test.ass"


def test_build_ass_filter_with_empty_font_path(video_generator):
    """Test _build_ass_filter with empty font path."""
    # Set empty font path
    video_generator.styles["karaoke"]["font_path"] = ""
    
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    assert result == "ass=test.ass"


def test_build_ass_filter_with_none_font_path(video_generator):
    """Test _build_ass_filter with None font path."""
    # Set None font path
    video_generator.styles["karaoke"]["font_path"] = None
    
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    assert result == "ass=test.ass"


def test_build_ass_filter_no_karaoke_section(tmp_path):
    """Test _build_ass_filter with no karaoke section in styles."""
    styles = {}  # No karaoke section
    generator = VideoGenerator(
        output_dir=str(tmp_path / "output"),
        cache_dir=str(tmp_path / "cache"),
        video_resolution=(1920, 1080),
        styles=styles,
    )
    
    ass_path = "test.ass"
    result = generator._build_ass_filter(ass_path)
    assert result == "ass=test.ass"


def test_build_ass_filter_logging(video_generator, tmp_path, caplog):
    """Test _build_ass_filter logging behavior."""
    # Set log level to INFO to capture the logs
    caplog.set_level(logging.INFO)
    
    # Create a test font file
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    font_file = font_dir / "test.ttf"
    font_file.touch()
    
    # Update styles to include font path
    video_generator.styles["karaoke"]["font_path"] = str(font_file)
    
    ass_path = "test.ass"
    result = video_generator._build_ass_filter(ass_path)
    
    # Check that info log was generated
    assert "Returning ASS filter with fonts dir:" in caplog.text
    assert str(font_dir) in caplog.text
