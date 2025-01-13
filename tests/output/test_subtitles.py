import pytest
import os
from datetime import timedelta
import logging
from typing import List, Tuple

from lyrics_transcriber.output.subtitles import SubtitlesGenerator
from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen


def create_word(text: str, start: float, end: float, confidence: float = 1.0) -> Word:
    """Helper to create a Word."""
    return Word(text=text, start_time=start, end_time=end, confidence=confidence)


def create_segment(start: float, end: float, text: str) -> LyricsSegment:
    """Helper to create a LyricsSegment with words."""
    words = [create_word(text=text, start=start, end=end)]
    return LyricsSegment(text=text, words=words, start_time=start, end_time=end)


@pytest.fixture
def mock_logger():
    return logging.getLogger("test")


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary directory for output files."""
    return str(tmp_path)


@pytest.fixture
def video_resolution() -> Tuple[int, int]:
    """Standard video resolution for testing."""
    return (1920, 1080)


@pytest.fixture
def generator(output_dir, video_resolution, mock_logger):
    """Create a SubtitlesGenerator instance."""
    return SubtitlesGenerator(output_dir=output_dir, video_resolution=video_resolution, font_size=48, line_height=60, logger=mock_logger)


@pytest.fixture
def sample_segments() -> List[LyricsSegment]:
    """Create sample lyrics segments for testing."""
    return [
        create_segment(17.98, 19.94, "I know I have good judgement"),
        create_segment(20.26, 22.10, "I know I have good taste"),
        create_segment(22.36, 24.40, "It's funny and it's ironic"),
        create_segment(24.62, 26.58, "That only I feel that way"),
        create_segment(26.62, 28.60, "I promise em that you're different"),
        create_segment(29.08, 30.96, "And everyone makes mistakes,"),
        create_segment(31.02, 32.84, "but just don't"),
        create_segment(35.98, 37.82, "I heard that you're an actor"),
    ]


def test_generate_ass_success(generator, sample_segments):
    """Test successful ASS file generation."""
    output_prefix = "test_lyrics"
    output_path = generator.generate_ass(sample_segments, output_prefix)

    # Verify output file exists
    assert os.path.exists(output_path)
    assert output_path.endswith(".ass")
    assert "Lyrics Corrected" in output_path

    # Read and verify file contents
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Check for required sections
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        # Check for style definition
        assert "Style: Nomad" in content
        # Check for some dialogue lines
        assert "Dialogue:" in content
        assert "I know I have good judgement" in content


def test_generate_ass_empty_segments(generator):
    """Test ASS generation with empty segments list."""
    with pytest.raises(Exception) as exc_info:
        generator.generate_ass([], "test_empty")
    assert "segments" in str(exc_info.value).lower()


def test_generate_ass_invalid_output_dir(video_resolution, mock_logger):
    """Test with invalid output directory."""
    invalid_generator = SubtitlesGenerator(
        output_dir="/nonexistent/directory", video_resolution=video_resolution, font_size=48, line_height=60, logger=mock_logger
    )

    with pytest.raises(Exception):
        invalid_generator.generate_ass([create_segment(1.0, 2.0, "Test")], "test")


def test_screen_creation(generator, sample_segments):
    """Test internal screen creation logic."""
    screens = generator._create_screens(sample_segments)

    # Verify screen creation
    assert len(screens) > 0
    for screen in screens:
        assert isinstance(screen, LyricsScreen)
        assert len(screen.lines) <= screen.MAX_VISIBLE_LINES


def test_styled_subtitles_creation(generator, sample_segments):
    """Test creation of styled ASS subtitles."""
    screens = generator._create_screens(sample_segments)
    ass = generator._create_styled_subtitles(screens, generator.video_resolution, generator.font_size)

    # Verify ASS object properties
    assert ass.styles_format is not None
    assert ass.events_format is not None
    assert len(ass.styles) > 0
    assert len(ass.events) > 0


def test_output_path_generation(generator):
    """Test output path generation."""
    prefix = "test_lyrics"
    path = generator._get_output_path(prefix, "ass")

    assert path.endswith(".ass")
    assert os.path.dirname(path) == generator.output_dir
    assert "test_lyrics" in path


def test_generate_ass_with_unicode(generator):
    """Test ASS generation with Unicode characters."""
    segments = [
        create_segment(1.0, 2.0, "Hello こんにちは"),
        create_segment(2.5, 3.5, "World 世界"),
    ]

    output_path = generator.generate_ass(segments, "unicode_test")

    # Verify file exists and contains Unicode
    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "こんにちは" in content
        assert "世界" in content


def test_generate_ass_style_customization(output_dir, video_resolution, mock_logger):
    """Test ASS generation with custom style parameters."""
    generator = SubtitlesGenerator(
        output_dir=output_dir,
        video_resolution=video_resolution,
        font_size=72,  # Larger font
        line_height=90,  # Larger line height
        logger=mock_logger,
    )

    segments = [create_segment(1.0, 2.0, "Test")]
    output_path = generator.generate_ass(segments, "style_test")

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Fontsize: 72" in content
