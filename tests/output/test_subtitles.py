import pytest
from datetime import timedelta
from lyrics_transcriber.output.ass.lyrics_models import LyricsLine, LyricsScreen
from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.subtitles import SubtitlesGenerator
from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.style import Style
import logging


@pytest.fixture
def logger():
    """Fixture to provide a logger for tests"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    return logger


def create_test_segment(text: str, start_time: float, end_time: float) -> LyricsSegment:
    """Helper function to create test segments"""
    word = Word(text=text, start_time=start_time, end_time=end_time)
    return LyricsSegment(text=text, words=[word], start_time=start_time, end_time=end_time)


def create_test_segment_no_end(text: str, start_time: float) -> LyricsSegment:
    """Helper function to create test segments with no end time"""
    word = Word(text=text, start_time=start_time, end_time=None)
    return LyricsSegment(text=text, words=[word], start_time=start_time, end_time=None)


def test_lyrics_line(logger):
    segments = [
        create_test_segment("Hello ", 1.0, 2.0),
        create_test_segment("world", 2.0, 3.0),
    ]
    line = LyricsLine(segments=segments, logger=logger)

    # Test properties - start time is now PRE_ROLL_TIME seconds earlier
    assert line.ts == 1.0  # This should still be the actual start time
    assert line.end_ts == 3.0
    assert str(line) == "{Hello }{world}"

    # Test timestamp adjustment - should still adjust by the given amount
    adjusted = line.adjust_timestamps(timedelta(seconds=1))
    assert adjusted.ts == 2.0  # Actual start time is adjusted
    assert adjusted.end_ts == 4.0

    # Test that the ASS event starts PRE_ROLL_TIME seconds earlier
    style = Style()
    style.Name = "Default"
    event = line.as_ass_event(screen_start=timedelta(seconds=0), screen_end=timedelta(seconds=4), style=style, y_position=100)
    assert event.Start == max(0, 1.0 - line.PRE_ROLL_TIME)  # Event starts earlier
    assert event.End == 3.0  # But ends at the actual end time


def test_lyrics_screen(logger):
    line1 = LyricsLine([create_test_segment("Hello", 1.0, 2.0)], logger=logger)
    line2 = LyricsLine([create_test_segment("world", 2.0, 3.0)], logger=logger)
    screen = LyricsScreen(lines=[line1, line2], video_size=(1920, 1080), line_height=60, logger=logger)

    # Test properties
    assert screen.end_ts == timedelta(seconds=3)

    # Test line positioning
    y1 = screen.get_line_y(0)
    y2 = screen.get_line_y(1)
    assert y2 > y1
    assert y2 - y1 == 60


def test_lyrics_line_blank_segments(logger):
    segments = [
        create_test_segment("Hello", 1.0, 2.0),
        # Gap between 2 and 3 seconds
        create_test_segment("world", 3.0, 4.0),
    ]
    line = LyricsLine(segments=segments, logger=logger)

    style = Style()
    style.Name = "Default"
    event = line.as_ass_event(screen_start=timedelta(seconds=0), screen_end=timedelta(seconds=4), style=style, y_position=100)

    text = event.Text
    assert "Hello" in text
    assert "world" in text
    # Check for gap between words (100 centiseconds = 1 second)
    assert "\\k100" in text
