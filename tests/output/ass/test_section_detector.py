import pytest
from unittest.mock import Mock

from lyrics_transcriber.output.ass.section_detector import SectionDetector
from lyrics_transcriber.types import LyricsSegment, Word


def create_segment(start: float, end: float, text: str) -> LyricsSegment:
    """Helper to create a test segment with words."""
    words = [Word(text=text, start_time=start, end_time=end)]
    return LyricsSegment(text=text, start_time=start, end_time=end, words=words)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def detector(mock_logger):
    """Create a SectionDetector instance."""
    return SectionDetector(logger=mock_logger)


def test_intro_detection(detector):
    """Test intro section detection."""
    segments = [create_segment(15.0, 18.0, "First line")]
    screens = detector.process_segments(segments, (1920, 1080), 60, 180.0)

    # Should detect intro section
    intro_screens = [s for s in screens if s.section_type == "INTRO"]
    assert len(intro_screens) == 1
    intro = intro_screens[0]

    # The SectionScreen adds a 1s offset to start_time
    assert intro.start_time == 1.0  # Accounts for SectionScreen's internal offset
    assert intro.end_time == 10.0  # Should end 5s before first segment (15s)


def test_outro_detection(detector):
    """Test outro section detection."""
    segments = [create_segment(10.0, 15.0, "Last line")]
    song_duration = 30.0
    screens = detector.process_segments(segments, (1920, 1080), 60, song_duration)

    # Should detect outro section
    outro_screens = [s for s in screens if s.section_type == "OUTRO"]
    assert len(outro_screens) == 1
    outro = outro_screens[0]

    # OUTRO sections don't get the 1s offset that INTRO sections do
    assert outro.start_time == 16.0  # Start 1s after last segment
    assert outro.end_time == 25.0  # End 5s before song end (30s)


def test_instrumental_detection(detector):
    """Test instrumental section detection."""
    segments = [
        create_segment(10.0, 12.0, "First line"),
        create_segment(30.0, 32.0, "After instrumental"),
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 40.0)

    # Should detect instrumental section
    instrumentals = [s for s in screens if s.section_type == "INSTRUMENTAL"]
    assert len(instrumentals) == 1
    instrumental = instrumentals[0]

    # INSTRUMENTAL sections don't get the 1s offset that INTRO sections do
    assert instrumental.start_time == 13.0  # Start 1s after first segment
    assert instrumental.end_time == 25.0  # End 5s before next segment


def test_no_sections_short_gaps(detector):
    """Test that short gaps don't create sections."""
    segments = [
        create_segment(0.0, 2.0, "Line 1"),
        create_segment(5.0, 7.0, "Line 2"),  # 3s gap, less than threshold
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 10.0)

    # Should not detect any sections for short gaps
    assert len(screens) == 0


def test_multiple_instrumentals(detector):
    """Test detection of multiple instrumental sections."""
    segments = [
        create_segment(10.0, 12.0, "First"),
        create_segment(30.0, 32.0, "Middle"),
        create_segment(50.0, 52.0, "Last"),
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 60.0)

    # Should detect two instrumental sections
    instrumentals = [s for s in screens if s.section_type == "INSTRUMENTAL"]
    assert len(instrumentals) == 2

    # Verify timing of both instrumental sections
    assert instrumentals[0].start_time == 13.0
    assert instrumentals[0].end_time == 25.0
    assert instrumentals[1].start_time == 33.0
    assert instrumentals[1].end_time == 45.0


def test_custom_gap_threshold(mock_logger):
    """Test section detection with custom gap threshold."""
    detector = SectionDetector(gap_threshold=5.0, logger=mock_logger)
    segments = [
        create_segment(0.0, 2.0, "Line 1"),
        create_segment(10.0, 12.0, "Line 2"),  # 8s gap, well above threshold
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 15.0)

    # Should detect instrumental section with 5s threshold
    instrumentals = [s for s in screens if s.section_type == "INSTRUMENTAL"]
    assert len(instrumentals) == 1
    assert instrumentals[0].start_time == 3.0  # 1s after first segment
    assert instrumentals[0].end_time == 5.0  # 5s before second segment


def test_padding_configuration(mock_logger):
    """Test section detection with custom padding."""
    detector = SectionDetector(
        gap_threshold=10.0,
        logger=mock_logger,
    )
    detector.instrumental_start_padding = 2.0  # Custom start padding
    detector.instrumental_end_padding = 3.0  # Custom end padding

    segments = [
        create_segment(10.0, 12.0, "First"),
        create_segment(30.0, 32.0, "Second"),
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 40.0)

    # Verify instrumental timing with custom padding
    instrumental = [s for s in screens if s.section_type == "INSTRUMENTAL"][0]
    assert instrumental.start_time == 14.0  # segment_end + start_padding
    assert instrumental.end_time == 27.0  # next_segment_start - end_padding


def test_section_screen_text_format(detector):
    """Test the text formatting of section screens."""
    segments = [create_segment(15.0, 18.0, "First line")]
    screens = detector.process_segments(segments, (1920, 1080), 60, 180.0)

    intro = [s for s in screens if s.section_type == "INTRO"][0]

    # Duration is calculated from original times before INTRO adjustments
    # For INTRO: original end_time is first_segment.start_time (15.0)
    # and original start_time is 0.0
    original_duration = round(15.0 - 0.0)  # 15 seconds
    assert intro.text == f"♪ INTRO ({original_duration} seconds) ♪"


def test_section_screen_durations(detector):
    """Test duration calculations for different section types."""
    segments = [
        create_segment(15.0, 18.0, "First line"),
        create_segment(30.0, 32.0, "Second line"),
    ]
    screens = detector.process_segments(segments, (1920, 1080), 60, 180.0)

    # Get one of each type
    intro = [s for s in screens if s.section_type == "INTRO"][0]
    instrumental = [s for s in screens if s.section_type == "INSTRUMENTAL"][0]

    # INTRO duration is calculated before timing adjustments
    assert intro.text == "♪ INTRO (15 seconds) ♪"  # 15.0 - 0.0

    # INSTRUMENTAL duration is gap between segments minus padding
    # Start: previous_segment.end_time + start_padding (1s)
    # End: next_segment.start_time - end_padding (5s)
    # Duration: (30.0 - 5.0) - (18.0 + 1.0) = 6 seconds
    assert instrumental.text == "♪ INSTRUMENTAL (6 seconds) ♪"


def test_section_screen_event_formatting(detector):
    """Test the ASS event formatting of section screens."""
    segments = [create_segment(15.0, 18.0, "First line")]
    screens = detector.process_segments(segments, (1920, 1080), 60, 180.0)

    intro = [s for s in screens if s.section_type == "INTRO"][0]
    events, _ = intro.as_ass_events(style=Mock())
    assert len(events) == 1

    event = events[0]
    # Verify event has fade in/out and proper alignment
    assert "\\fad(" in event.Text
    assert "\\an8" in event.Text  # Top-center alignment
    # Verify karaoke timing for full duration
    duration_cs = int((intro.end_time - intro.start_time) * 100)
    assert f"\\K{duration_cs}" in event.Text
