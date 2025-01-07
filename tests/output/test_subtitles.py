import pytest
from datetime import timedelta
from lyrics_transcriber.output.subtitles import (
    LyricsLine,
    LyricsScreen,
    LyricsObjectJSONEncoder,
    SubtitlesGenerator,
)
from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.constants import ALIGN_TOP_CENTER
import json
import logging

@pytest.fixture
def logger():
    """Fixture to provide a logger for tests"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    return logger

def create_test_segment(text: str, start_time: float, end_time: float) -> LyricsSegment:
    """Helper function to create test segments"""
    word = Word(
        text=text,
        start_time=start_time,
        end_time=end_time
    )
    return LyricsSegment(
        text=text,
        words=[word],
        start_time=start_time,
        end_time=end_time
    )

def create_test_segment_no_end(text: str, start_time: float) -> LyricsSegment:
    """Helper function to create test segments with no end time"""
    word = Word(
        text=text,
        start_time=start_time,
        end_time=None
    )
    return LyricsSegment(
        text=text,
        words=[word],
        start_time=start_time,
        end_time=None
    )

def test_lyrics_line(logger):
    segments = [
        create_test_segment("Hello ", 1.0, 2.0),
        create_test_segment("world", 2.0, 3.0),
    ]
    line = LyricsLine(segments, logger=logger)

    # Test properties
    assert line.ts == 1.0
    assert line.end_ts == 3.0
    assert str(line) == "{Hello }{world}"

    # Test timestamp adjustment
    adjusted = line.adjust_timestamps(timedelta(seconds=1))
    assert adjusted.ts == 2.0
    assert adjusted.end_ts == 4.0

    # Test serialization
    data = line.to_dict()
    assert "segments" in data
    assert isinstance(data["segments"], list)
    assert len(data["segments"]) == 2
    assert all(isinstance(s, dict) for s in data["segments"])

def test_lyrics_screen(logger):
    line1 = LyricsLine([create_test_segment("Hello", 1.0, 2.0)], logger=logger)
    line2 = LyricsLine([create_test_segment("world", 2.0, 3.0)], logger=logger)
    screen = LyricsScreen(
        lines=[line1, line2],
        start_ts=timedelta(seconds=1),
        video_size=(1920, 1080),
        line_height=60,
        logger=logger
    )

    # Test properties
    assert screen.end_ts == timedelta(seconds=3)

    # Test line positioning
    y1 = screen.get_line_y(0)
    y2 = screen.get_line_y(1)
    assert y2 > y1
    assert y2 - y1 == 60

def test_set_segment_end_times(logger):
    segment1 = create_test_segment_no_end("Hello", 1.0)
    segment2 = create_test_segment_no_end("world", 2.0)
    
    screens = [
        LyricsScreen(
            lines=[LyricsLine([segment1, segment2], logger=logger)],
            logger=logger
        )
    ]

    generator = SubtitlesGenerator(
        output_dir="test_output",
        video_resolution=(1920, 1080),
        font_size=48,
        line_height=60,
        logger=logger
    )

    result = generator.set_segment_end_times(screens, 5)
    assert result[0].lines[0].segments[0].end_time == 2.0
    assert result[0].lines[0].segments[1].end_time == 5.0

def test_lyrics_line_blank_segments(logger):
    segments = [
        create_test_segment("Hello", 1.0, 2.0),
        # Gap between 2 and 3 seconds
        create_test_segment("world", 3.0, 4.0),
    ]
    line = LyricsLine(segments, logger=logger)

    style = Style()
    style.Name = "Default"
    event = line.as_ass_event(
        screen_start=timedelta(seconds=0),
        screen_end=timedelta(seconds=4),
        style=style,
        y_position=100
    )

    text = event.Text
    assert "Hello" in text
    assert "world" in text
    assert "\\k100.0" in text  # 1 second gap = 100 centiseconds

def test_subtitle_generator(logger):
    generator = SubtitlesGenerator(
        output_dir="test_output",
        video_resolution=(1920, 1080),
        font_size=48,
        line_height=60,
        logger=logger
    )

    # Test _get_output_path
    output_path = generator._get_output_path("test", "ass")
    assert output_path == "test_output/test.ass"

    # Test _create_screens
    segments = [
        create_test_segment("Hello", 1.0, 2.0),
        create_test_segment("World", 2.0, 3.0)
    ]
    
    screens = generator._create_screens(segments)
    assert len(screens) == 1
    assert len(screens[0].lines) == 2
    assert screens[0].lines[0].segments[0].text == "Hello"
    assert screens[0].lines[1].segments[0].text == "World"

def test_json_encoder(logger):
    segment = create_test_segment("test", 1.0, 2.0)
    line = LyricsLine([segment], logger=logger)
    screen = LyricsScreen([line], start_ts=timedelta(seconds=0), logger=logger)

    encoder = LyricsObjectJSONEncoder()

    # Test segment encoding
    segment_json = json.dumps(segment, cls=LyricsObjectJSONEncoder)
    assert isinstance(json.loads(segment_json), dict)

    # Test line encoding
    line_json = json.dumps(line, cls=LyricsObjectJSONEncoder)
    assert isinstance(json.loads(line_json), dict)

    # Test screen encoding
    screen_json = json.dumps(screen, cls=LyricsObjectJSONEncoder)
    assert isinstance(json.loads(screen_json), dict)
