import pytest
from datetime import timedelta
from lyrics_transcriber.output.subtitles import (
    LyricSegment,
    LyricsLine,
    LyricsScreen,
    set_segment_end_times,
    set_screen_start_times,
    LyricSegmentIterator,
    create_styled_subtitles,
    LyricsObjectJSONEncoder,
)
from lyrics_transcriber.output import ass
import json
import logging


def test_lyric_segment():
    # Test basic creation
    segment = LyricSegment("hello", timedelta(seconds=1), timedelta(seconds=2))
    assert segment.text == "hello"
    assert segment.ts == timedelta(seconds=1)
    assert segment.end_ts == timedelta(seconds=2)

    # Test timestamp adjustment
    adjusted = segment.adjust_timestamps(timedelta(seconds=1))
    assert adjusted.ts == timedelta(seconds=2)
    assert adjusted.end_ts == timedelta(seconds=3)

    # Test ASS rendering - account for float formatting
    assert segment.to_ass() == "{\\kf100.0}hello"

    # Test serialization - use total_seconds() for timestamps
    data = segment.to_dict()
    assert data["ts"] == segment.ts.total_seconds()
    assert data["end_ts"] == segment.end_ts.total_seconds()
    restored = LyricSegment.from_dict(data)
    assert restored.text == segment.text
    assert restored.ts == segment.ts
    assert restored.end_ts == segment.end_ts


def test_lyrics_line():
    segments = [
        LyricSegment("Hello ", timedelta(seconds=1), timedelta(seconds=2)),
        LyricSegment("world", timedelta(seconds=2), timedelta(seconds=3)),
    ]
    line = LyricsLine(segments)

    # Test properties
    assert line.ts == timedelta(seconds=1)
    assert line.end_ts == timedelta(seconds=3)
    assert str(line) == "{Hello }{world}"

    # Test timestamp adjustment
    adjusted = line.adjust_timestamps(timedelta(seconds=1))
    assert adjusted.ts == timedelta(seconds=2)
    assert adjusted.end_ts == timedelta(seconds=4)

    # Test serialization - verify the data structure
    data = line.to_dict()
    assert "segments" in data
    assert isinstance(data["segments"], list)
    assert len(data["segments"]) == 2
    assert all(isinstance(s, dict) for s in data["segments"])

    # Verify each segment's data format
    for segment_data in data["segments"]:
        assert isinstance(segment_data["ts"], float)
        assert isinstance(segment_data["end_ts"], float)
        assert isinstance(segment_data["text"], str)

    restored = LyricsLine.from_dict(data)
    assert len(restored.segments) == len(line.segments)
    assert restored.ts == line.ts
    assert restored.end_ts == line.end_ts


def test_lyrics_screen():
    line1 = LyricsLine([LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2))])
    line2 = LyricsLine([LyricSegment("world", timedelta(seconds=2), timedelta(seconds=3))])
    screen = LyricsScreen(lines=[line1, line2], start_ts=timedelta(seconds=1), video_size=(1920, 1080), line_height=60)

    # Test properties
    assert screen.end_ts == timedelta(seconds=3)

    # Test line positioning
    y1 = screen.get_line_y(0)
    y2 = screen.get_line_y(1)
    assert y2 > y1  # Second line should be below first line
    assert y2 - y1 == 60  # Line height difference

    # Test timestamp adjustment
    adjusted = screen.adjust_timestamps(timedelta(seconds=1))
    assert adjusted.start_ts == timedelta(seconds=2)
    assert adjusted.end_ts == timedelta(seconds=4)


def test_set_segment_end_times():
    screens = [
        LyricsScreen(
            lines=[LyricsLine([LyricSegment("Hello", timedelta(seconds=1), None), LyricSegment("world", timedelta(seconds=2), None)])]
        )
    ]

    result = set_segment_end_times(screens, 5)
    assert result[0].lines[0].segments[0].end_ts == timedelta(seconds=2)
    assert result[0].lines[0].segments[1].end_ts == timedelta(seconds=5)


def test_set_screen_start_times():
    screens = [
        LyricsScreen(lines=[LyricsLine([LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2))])]),
        LyricsScreen(lines=[LyricsLine([LyricSegment("world", timedelta(seconds=3), timedelta(seconds=4))])]),
    ]

    result = set_screen_start_times(screens)
    assert result[0].start_ts == timedelta(seconds=0)
    assert result[1].start_ts == timedelta(seconds=2.1)  # Previous end + 0.1s


def test_lyric_segment_iterator():
    segments = ["one", "two", "three"]
    iterator = LyricSegmentIterator(segments)

    assert len(iterator) == 3

    # Test iteration
    items = [item for item in iterator]
    assert items == segments

    # Test StopIteration
    iterator = LyricSegmentIterator(segments)
    for _ in range(3):
        next(iterator)
    with pytest.raises(StopIteration):
        next(iterator)


def test_lyrics_line_empty():
    line = LyricsLine([])
    assert line.ts is None
    assert line.end_ts is None


def test_lyrics_line_ass_event():
    line = LyricsLine(
        [
            LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2)),
            LyricSegment("world", timedelta(seconds=2), timedelta(seconds=3)),
        ]
    )

    style = ass.ASS.Style()
    style.Name = "Default"

    event = line.as_ass_event(screen_start=timedelta(seconds=0), screen_end=timedelta(seconds=3), style=style, y_position=100)

    assert event.Style.Name == "Default"
    assert event.Start == 0
    assert event.End == 3
    assert event.MarginV == 100
    assert "\\an8" in event.Text


def test_lyrics_screen_serialization():
    screen = LyricsScreen(
        lines=[LyricsLine([LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2))])],
        start_ts=timedelta(seconds=1),
        video_size=(1920, 1080),
        line_height=60,
    )

    # Test to_dict
    data = screen.to_dict()
    assert "lines" in data
    assert "start_ts" in data

    # Test from_dict
    restored = LyricsScreen.from_dict(data)
    assert restored.start_ts == screen.start_ts
    assert len(restored.lines) == len(screen.lines)


def test_json_encoder():
    segment = LyricSegment("test", timedelta(seconds=1), timedelta(seconds=2))
    line = LyricsLine([segment])
    screen = LyricsScreen([line], start_ts=timedelta(seconds=0))

    # Test encoding different objects
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

    # Test fallback for non-lyrics objects
    with pytest.raises(TypeError):
        json.dumps(object(), cls=LyricsObjectJSONEncoder)


def test_create_styled_subtitles():
    screen = LyricsScreen(
        lines=[LyricsLine([LyricSegment("Test", timedelta(seconds=1), timedelta(seconds=2))])],
        start_ts=timedelta(seconds=1),
        video_size=(1920, 1080),
        line_height=60,
    )

    subtitles = create_styled_subtitles(lyric_screens=[screen], resolution=(1920, 1080), fontsize=48)

    assert isinstance(subtitles, ass.ASS)
    assert len(subtitles.styles) == 1
    assert len(subtitles.events) > 0

    style = subtitles.styles[0]
    assert style.Fontsize == 48
    assert style.Alignment == ass.ASS.ALIGN_TOP_CENTER


def test_lyrics_screen_str_representation():
    screen = LyricsScreen(
        lines=[LyricsLine([LyricSegment("Test", timedelta(seconds=1), timedelta(seconds=2))])], start_ts=timedelta(seconds=1)
    )

    str_repr = str(screen)
    assert "0:00:01" in str_repr
    assert "0:00:02" in str_repr
    assert "Test" in str_repr


def test_lyrics_screen_with_logger():
    logger = logging.getLogger("test_logger")
    screen = LyricsScreen(
        lines=[LyricsLine([LyricSegment("Test", timedelta(seconds=1), timedelta(seconds=2))])],
        start_ts=timedelta(seconds=1),
        video_size=(1920, 1080),
        line_height=60,
        logger=logger,
    )

    # Test that having a logger doesn't break functionality
    y_pos = screen.get_line_y(0)
    assert isinstance(y_pos, int)


def test_lyrics_line_timestamp_setters():
    segments = [
        LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2)),
        LyricSegment("world", timedelta(seconds=2), timedelta(seconds=3)),
    ]
    line = LyricsLine(segments)

    # Test ts setter
    line.ts = timedelta(seconds=5)
    assert line.segments[0].ts == timedelta(seconds=5)

    # Test end_ts setter
    line.end_ts = timedelta(seconds=7)
    assert line.segments[-1].end_ts == timedelta(seconds=7)


def test_lyrics_line_blank_segments():
    segments = [
        LyricSegment("Hello", timedelta(seconds=1), timedelta(seconds=2)),
        # Gap between 2 and 3 seconds
        LyricSegment("world", timedelta(seconds=3), timedelta(seconds=4)),
    ]
    line = LyricsLine(segments)

    # Create ASS event with blank segment handling
    style = ass.ASS.Style()
    style.Name = "Default"
    event = line.as_ass_event(screen_start=timedelta(seconds=0), screen_end=timedelta(seconds=4), style=style, y_position=100)

    # The Text should contain a blank segment between "Hello" and "world"
    text = event.Text
    assert "Hello" in text
    assert "world" in text
    # Check for the blank segment timing tag
    assert "\\k100.0" in text  # 1 second gap = 100 centiseconds
