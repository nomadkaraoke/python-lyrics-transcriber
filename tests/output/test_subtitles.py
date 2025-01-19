import subprocess
import pytest
import os
from unittest.mock import Mock, patch

from lyrics_transcriber.output.ass.constants import ALIGN_TOP_CENTER
from lyrics_transcriber.output.ass.lyrics_line import LyricsLine
from lyrics_transcriber.output.ass.section_screen import SectionScreen
from lyrics_transcriber.output.ass.lyrics_screen import LyricsScreen
from lyrics_transcriber.output.subtitles import SubtitlesGenerator
from lyrics_transcriber.types import LyricsSegment, Word


def create_segment(start: float, end: float, text: str) -> LyricsSegment:
    """Helper to create a test segment with words."""
    words = [Word(text=text, start_time=start, end_time=end)]
    return LyricsSegment(text=text, start_time=start, end_time=end, words=words)


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary directory for output files."""
    return str(tmp_path)


@pytest.fixture
def video_resolution() -> tuple[int, int]:
    """Standard video resolution for testing."""
    return (1920, 1080)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def generator(output_dir, video_resolution, mock_logger):
    """Create a SubtitlesGenerator instance."""
    return SubtitlesGenerator(output_dir=output_dir, video_resolution=video_resolution, font_size=48, line_height=60, logger=mock_logger)


@pytest.fixture
def sample_segments() -> list[LyricsSegment]:
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


def test_get_output_path(generator):
    """Test output path generation."""
    path = generator._get_output_path("test_lyrics", "ass")
    assert path.endswith(".ass")
    assert os.path.dirname(path) == generator.output_dir
    assert "test_lyrics" in path


@patch("subprocess.check_output")
def test_get_audio_duration_success(mock_check_output, generator):
    """Test successful audio duration detection."""
    mock_check_output.return_value = '{"format": {"duration": "180.5"}}'
    duration = generator._get_audio_duration("test.mp3")
    assert duration == 180.5
    assert mock_check_output.called


@patch("subprocess.check_output")
def test_get_audio_duration_failure(mock_check_output, generator):
    """Test audio duration detection failure."""
    mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")
    duration = generator._get_audio_duration("nonexistent.mp3")
    assert duration == 0.0
    assert mock_check_output.called


def test_create_section_screens(generator, sample_segments):
    """Test creation of section screens."""
    song_duration = 180.0
    section_screens = generator._create_section_screens(sample_segments, song_duration)

    # Verify section screens are created
    assert isinstance(section_screens, list)
    for screen in section_screens:
        assert isinstance(screen, SectionScreen)


def test_get_instrumental_times(generator):
    """Test extraction of instrumental section times."""
    # Create mock section screens
    section_screens = [
        SectionScreen("INSTRUMENTAL", 10.0, 20.0, (1920, 1080), 60),
        SectionScreen("INTRO", 0.0, 5.0, (1920, 1080), 60),
        SectionScreen("INSTRUMENTAL", 30.0, 40.0, (1920, 1080), 60),
    ]

    times = generator._get_instrumental_times(section_screens)
    assert len(times) == 2
    assert times[0] == (10.0, 20.0)
    assert times[1] == (30.0, 40.0)


def test_create_lyric_screens(generator, sample_segments):
    """Test creation of lyric screens."""
    # Test with no instrumental sections
    instrumental_times = []
    screens = generator._create_lyric_screens(sample_segments, instrumental_times)

    # Verify screens are created correctly
    assert len(screens) == 2  # Should split into 2 screens with MAX_LINES_PER_SCREEN=4
    assert all(isinstance(screen, LyricsScreen) for screen in screens)
    assert len(screens[0].lines) == 4  # First screen should be full
    assert len(screens[1].lines) == 4  # Second screen has remaining lines


def test_create_lyric_screens_with_instrumental(generator, sample_segments):
    """Test creation of lyric screens with instrumental sections."""
    # Create an instrumental section in the middle of the segments
    instrumental_times = [(22.0, 25.0)]  # This should split the segments
    screens = generator._create_lyric_screens(sample_segments, instrumental_times)

    # Verify screens are created and split correctly
    assert len(screens) >= 2  # Should have at least 2 screens due to instrumental split

    # Check that no lines fall within instrumental section
    for screen in screens:
        for line in screen.lines:
            # Check that no line overlaps with instrumental section
            assert not (line.segment.start_time >= 22.0 and line.segment.start_time < 25.0)


def test_should_start_new_screen(generator, sample_segments):
    """Test conditions for starting new screens."""
    screen = LyricsScreen(video_size=(1920, 1080), line_height=generator.config.line_height, logger=generator.logger)

    # Test empty screen
    assert generator._should_start_new_screen(None, sample_segments[0], []) is True

    # Test full screen
    for i in range(generator.config.max_visible_lines):
        screen.lines.append(LyricsLine(segment=sample_segments[i], logger=generator.logger))
    assert generator._should_start_new_screen(screen, sample_segments[4], []) is True

    # Test instrumental boundary
    screen = LyricsScreen(video_size=(1920, 1080), line_height=generator.config.line_height, logger=generator.logger)
    screen.lines.append(LyricsLine(segment=create_segment(5.0, 8.0, "test"), logger=generator.logger))
    instrumental_times = [(8.0, 12.0)]
    new_segment = create_segment(12.1, 15.0, "after instrumental")
    assert generator._should_start_new_screen(screen, new_segment, instrumental_times) is True


def test_merge_and_process_screens(generator):
    """Test merging section and lyric screens."""
    # Create test screens
    section_screens = [
        SectionScreen("INTRO", 0.0, 5.0, generator.video_resolution, generator.config.line_height),
        SectionScreen("INSTRUMENTAL", 20.0, 25.0, generator.video_resolution, generator.config.line_height),
    ]

    lyric_screens = [
        LyricsScreen(video_size=generator.video_resolution, line_height=generator.config.line_height, logger=generator.logger),
        LyricsScreen(video_size=generator.video_resolution, line_height=generator.config.line_height, logger=generator.logger),
    ]

    # Add some lines to lyric screens
    lyric_screens[0].lines.append(LyricsLine(segment=create_segment(6.0, 8.0, "test1"), logger=generator.logger))
    lyric_screens[1].lines.append(LyricsLine(segment=create_segment(26.0, 28.0, "test2"), logger=generator.logger))

    # Merge screens
    all_screens = generator._merge_and_process_screens(section_screens, lyric_screens)

    # Verify results
    assert len(all_screens) == 4  # All screens combined
    assert isinstance(all_screens[0], SectionScreen)  # INTRO
    assert isinstance(all_screens[1], LyricsScreen)  # First lyrics
    assert isinstance(all_screens[2], SectionScreen)  # INSTRUMENTAL
    assert isinstance(all_screens[3], LyricsScreen)  # Second lyrics


@pytest.mark.parametrize(
    "screen,expected_lines",
    [
        (SectionScreen("INTRO", 0.0, 5.0, (1920, 1080), 60), 3),  # 3 log lines for section
        (LyricsScreen(video_size=(1920, 1080), line_height=60), 1),  # 1 line for empty screen
    ],
)
def test_log_final_screens(generator, screen, expected_lines):
    """Test logging of final screens."""
    # Add a line to LyricsScreen if testing that type
    if isinstance(screen, LyricsScreen):
        screen.lines.append(LyricsLine(segment=create_segment(1.0, 2.0, "test"), logger=generator.logger))

    generator._log_final_screens([screen])

    # Verify logging calls
    assert generator.logger.debug.call_count >= expected_lines


def test_create_styled_ass_instance(generator):
    """Test creation of styled ASS instance."""
    ass, style = generator._create_styled_ass_instance(generator.video_resolution, generator.font_size)

    # Verify ASS instance setup
    resolution = ass.resolution()
    assert resolution[0] == generator.video_resolution[0]
    assert resolution[1] == generator.video_resolution[1]
    assert len(ass.styles) == 1  # Should have one style
    assert ass.events_format == ["Layer", "Style", "Start", "End", "MarginV", "Text"]

    # Verify style settings
    assert style.Name == "Nomad"
    assert style.Fontsize == generator.font_size
    assert style.Alignment == ALIGN_TOP_CENTER
    assert style.BorderStyle == 1
    assert style.Outline == 1
    assert style.Shadow == 0


def test_create_styled_subtitles(generator, sample_segments):
    """Test creation of styled subtitles."""
    # Create a mix of section and lyric screens
    screens = [
        SectionScreen("INTRO", 0.0, 5.0, generator.video_resolution, generator.config.line_height, logger=generator.logger),
        LyricsScreen(video_size=generator.video_resolution, line_height=generator.config.line_height, logger=generator.logger),
    ]

    # Add some lines to the lyric screen
    screens[1].lines.append(LyricsLine(segment=sample_segments[0], logger=generator.logger))

    # Generate styled subtitles
    ass = generator._create_styled_subtitles(screens, generator.video_resolution, generator.font_size)

    # Verify ASS file content
    assert len(ass.events) > 0  # Should have generated events
    assert all(hasattr(event, "Style") for event in ass.events)
    assert all(hasattr(event, "Text") for event in ass.events)


@patch("subprocess.check_output")
def test_generate_ass_success(mock_check_output, generator, sample_segments, tmp_path):
    """Test successful ASS file generation."""
    # Mock audio duration check
    mock_check_output.return_value = '{"format": {"duration": "180.5"}}'

    # Generate ASS file
    output_path = generator.generate_ass(segments=sample_segments, output_prefix="test", audio_filepath="test.mp3")

    # Verify file creation
    assert os.path.exists(output_path)
    assert output_path.endswith(".ass")
    assert "test" in output_path


@patch("subprocess.check_output")
def test_generate_ass_failure(mock_check_output, generator, sample_segments):
    """Test ASS generation failure handling."""
    # Force an error in audio duration check
    mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")

    # Call generate_ass - it should still work with fallback duration
    output_path = generator.generate_ass(segments=sample_segments, output_prefix="test", audio_filepath="nonexistent.mp3")

    # Verify the file was still created
    assert os.path.exists(output_path)
    assert output_path.endswith(".ass")

    # Verify that error was logged
    generator.logger.error.assert_called_once()


def test_is_in_instrumental_section(generator):
    """Test instrumental section detection."""
    instrumental_times = [(10.0, 20.0), (30.0, 40.0)]

    # Test segment within instrumental
    segment = create_segment(15.0, 18.0, "test")
    assert generator._is_in_instrumental_section(segment, instrumental_times) is True

    # Test segment outside instrumental
    segment = create_segment(25.0, 28.0, "test")
    assert generator._is_in_instrumental_section(segment, instrumental_times) is False

    # Test segment at boundary
    segment = create_segment(20.0, 22.0, "test")
    assert generator._is_in_instrumental_section(segment, instrumental_times) is False


def test_end_to_end(generator, sample_segments):
    """Test end-to-end screen creation process."""
    song_duration = 180.0

    # Create all screens
    screens = generator._create_screens(sample_segments, song_duration)

    # Verify screen creation
    assert len(screens) > 0
    assert any(isinstance(screen, SectionScreen) for screen in screens)
    assert any(isinstance(screen, LyricsScreen) for screen in screens)

    # Verify screen ordering
    screen_times = [(screen.start_ts, screen.end_ts) for screen in screens]
    for i in range(1, len(screen_times)):
        assert screen_times[i][0] >= screen_times[i - 1][0]  # Should be in chronological order
