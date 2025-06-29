import pytest
from unittest.mock import Mock
from datetime import timedelta

from lyrics_transcriber.output.ass.section_screen import SectionScreen
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.config import ScreenConfig


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def video_size():
    return (1920, 1080)


@pytest.fixture
def line_height():
    return 60


@pytest.fixture
def style():
    style = Style()
    style.Name = "Default"
    return style


@pytest.fixture
def default_config():
    """Provide access to default config values in tests."""
    return ScreenConfig()


def test_intro_section_timing():
    """Test INTRO section timing adjustments."""
    screen = SectionScreen(section_type="INTRO", start_time=0.0, end_time=15.0, video_size=(1920, 1080), line_height=60)

    # INTRO sections have special timing adjustments
    assert screen.start_time == 1.0  # Start after 1 second
    assert screen.end_time == 10.0  # End 5 seconds before next section
    assert screen.text == "♪ INTRO (15 seconds) ♪"  # Duration from original times


def test_instrumental_section_timing():
    """Test INSTRUMENTAL section timing."""
    screen = SectionScreen(section_type="INSTRUMENTAL", start_time=20.0, end_time=30.0, video_size=(1920, 1080), line_height=60)

    # INSTRUMENTAL sections keep their original timing
    assert screen.start_time == 20.0
    assert screen.end_time == 30.0
    assert screen.text == "♪ INSTRUMENTAL (10 seconds) ♪"


def test_outro_section_timing():
    """Test OUTRO section timing."""
    screen = SectionScreen(section_type="OUTRO", start_time=160.0, end_time=180.0, video_size=(1920, 1080), line_height=60)

    # OUTRO sections keep their original timing
    assert screen.start_time == 160.0
    assert screen.end_time == 180.0
    assert screen.text == "♪ OUTRO (20 seconds) ♪"


def test_ass_event_generation(style, mock_logger, default_config):
    """Test ASS event generation."""
    # fmt: off
    screen = SectionScreen(
        section_type="INSTRUMENTAL",
        start_time=20.0,
        end_time=30.0,
        video_size=(1920, 1080),
        line_height=60,
        logger=mock_logger
    )
    # fmt: on

    events, active_lines = screen.as_ass_events(style)
    assert len(events) == 1
    event = events[0]

    # Verify event properties
    assert event.Start == 20.0
    assert event.End == 30.0
    assert event.Style == style
    assert event.Layer == 0

    # Use config values for verification
    assert f"\\fad({default_config.fade_in_ms},{default_config.fade_out_ms})" in event.Text
    assert "\\an8" in event.Text
    assert "INSTRUMENTAL (10 seconds)" in event.Text

    assert len(active_lines) == 0


def test_vertical_positioning(style, mock_logger):
    """Test vertical positioning of section text."""
    screen = SectionScreen(
        section_type="INSTRUMENTAL", start_time=20.0, end_time=30.0, video_size=(1920, 1080), line_height=60, logger=mock_logger
    )

    events, _ = screen.as_ass_events(style)
    event = events[0]

    # Text should be vertically centered
    expected_y = (1080 - 60) // 2
    assert event.MarginV == expected_y


def test_timestamp_properties():
    """Test timestamp conversion properties."""
    screen = SectionScreen(
        section_type="INSTRUMENTAL", start_time=61.5, end_time=122.75, video_size=(1920, 1080), line_height=60  # 1:01.5  # 2:02.75
    )

    assert screen.start_ts == timedelta(seconds=61.5)
    assert screen.end_ts == timedelta(seconds=122.75)


def test_string_representation():
    """Test string representation of section screen."""
    screen = SectionScreen(section_type="INTRO", start_time=0.0, end_time=15.0, video_size=(1920, 1080), line_height=60)

    expected_str = "INTRO 0:00:01 - 0:00:10"  # Accounts for INTRO timing adjustments
    assert str(screen) == expected_str


def test_custom_config():
    """Test section screen with custom config."""
    config = ScreenConfig(line_height=80)
    # Manually set fade values since they're not constructor parameters
    config.fade_in_ms = 200
    config.fade_out_ms = 500

    # fmt: off
    screen = SectionScreen(
        section_type="INSTRUMENTAL",
        start_time=20.0,
        end_time=30.0,
        video_size=(1920, 1080),
        line_height=60,
        config=config
    )
    # fmt: on

    events, _ = screen.as_ass_events(style=Style())
    event = events[0]

    # Verify custom fade timing
    assert "\\fad(200,500)" in event.Text


def test_previous_lines_timing(style, mock_logger, default_config):
    """Test timing adjustment for previous active lines."""
    # fmt: off
    screen = SectionScreen(
        section_type="INSTRUMENTAL",
        start_time=20.0,
        end_time=30.0,
        video_size=(1920, 1080),
        line_height=60,
        logger=mock_logger
    )
    # fmt: on

    previous_lines = [(21.0, 0, "Previous line")]
    events, _ = screen.as_ass_events(style, previous_active_lines=previous_lines)

    # Use config value for fade calculation
    expected_start = 21.0 + (default_config.fade_out_ms / 1000)
    assert events[0].Start == expected_start


def test_original_duration_preserved():
    """Test that original duration is preserved in text."""
    screen = SectionScreen(section_type="INTRO", start_time=0.0, end_time=20.0, video_size=(1920, 1080), line_height=60)

    # Even though timing is adjusted, text shows original duration
    assert screen.text == "♪ INTRO (20 seconds) ♪"
    assert screen.start_time == 1.0
    assert screen.end_time == 15.0
