import pytest
from datetime import timedelta
from unittest.mock import Mock

from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.lyrics_line import LyricsLine
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.config import ScreenConfig, LineTimingInfo, LineState


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def style():
    style = Style()
    style.Name = "Test"
    return style


@pytest.fixture
def config():
    config = ScreenConfig(line_height=60, video_height=1080)
    # Set fade values after construction
    config.fade_in_ms = 300
    config.fade_out_ms = 600
    return config


def create_segment(words, start_time=10.0):
    """Helper to create a segment with words and timing."""
    segment_words = []
    current_time = start_time

    for text, duration in words:
        # fmt: off
        word = Word(
            text=text,
            start_time=current_time,
            end_time=current_time + duration
        )
        # fmt: on
        segment_words.append(word)
        current_time += duration

    return LyricsSegment(text=" ".join(text for text, _ in words), words=segment_words, start_time=start_time, end_time=current_time)


def test_basic_karaoke_timing():
    """Test basic karaoke timing with simple words."""
    # fmt: off
    words = [
        ("Hello", 0.5),
        ("world", 0.5)
    ]
    # fmt: on
    segment = create_segment(words)
    line = LyricsLine(segment=segment)

    # Start at the beginning of the line
    result = line._create_ass_text(timedelta(seconds=10.0))

    # Should have no initial delay, then timing for each word
    assert result == r"{\k0}{\kf50}Hello {\kf50}world"


def test_karaoke_with_gaps():
    """Test karaoke timing with gaps between words."""
    words = [("First", 0.5), ("gap", 0.5), ("here", 0.5)]  # 10.0 - 10.5  # 11.0 - 11.5 (0.5s gap)  # 12.0 - 12.5 (0.5s gap)
    segment = create_segment(words)

    # Manually adjust timing to create gaps
    segment.words[1].start_time = 11.0  # Add 0.5s gap after "First"
    segment.words[1].end_time = 11.5
    segment.words[2].start_time = 12.0  # Add 0.5s gap after "gap"
    segment.words[2].end_time = 12.5

    line = LyricsLine(segment=segment)
    result = line._create_ass_text(timedelta(seconds=10.0))

    # Should include gaps between words
    assert result == r"{\k0}{\kf50}First {\k50}{\kf50}gap {\k50}{\kf50}here"


def test_karaoke_with_early_start():
    """Test karaoke timing when ASS event starts before first word."""
    # fmt: off
    words = [
        ("Wait", 0.5),
        ("for", 0.3),
        ("it", 0.2)
    ]
    # fmt: on
    segment = create_segment(words, start_time=15.0)
    line = LyricsLine(segment=segment)

    # Start event 2 seconds before first word
    result = line._create_ass_text(timedelta(seconds=13.0))

    # Should have initial delay of 200 (2 seconds * 100)
    assert result == r"{\k200}{\kf50}Wait {\kf30}for {\kf20}it"


def test_karaoke_with_small_gaps():
    """Test that small gaps (<0.1s) between words are ignored."""
    # fmt: off
    words = [
        ("No", 0.5),     # 10.0 - 10.5
        ("tiny", 0.5),   # 10.55 - 11.05 (0.05s gap - should be ignored)
        ("gap", 0.5)     # 11.05 - 11.55
    ]
    segment = create_segment([
        ("No", 0.5),
        ("tiny", 0.5),
        ("gap", 0.5)
    ])
    # fmt: on

    # Manually adjust timing to create small gaps
    segment.words[1].start_time = 10.55
    segment.words[1].end_time = 11.05
    segment.words[2].start_time = 11.05
    segment.words[2].end_time = 11.55

    line = LyricsLine(segment=segment)
    result = line._create_ass_text(timedelta(seconds=10.0))

    # Small gaps should not create {\k} tags
    assert result == r"{\k0}{\kf50}No {\kf50}tiny {\kf50}gap"


def test_string_representation():
    """Test string representation of LyricsLine."""
    segment = create_segment([("Test", 1.0)])
    line = LyricsLine(segment=segment)

    assert str(line) == "{Test}"


def test_logger_initialization():
    """Test logger is initialized if not provided."""
    segment = create_segment([("Test", 1.0)])
    line = LyricsLine(segment=segment)

    assert line.logger is not None


def test_custom_logger():
    """Test custom logger is used if provided."""
    logger = Mock()
    segment = create_segment([("Test", 1.0)])
    line = LyricsLine(segment=segment, logger=logger)

    assert line.logger == logger


class TestAssEventCreation:
    def test_basic_event_creation(self, style, config):
        """Test basic ASS event creation."""
        # fmt: off
        segment = create_segment([
            ("Test", 1.0)  # 10.0 - 11.0
        ])
        line = LyricsLine(segment=segment)
        
        timing = LineTimingInfo(
            fade_in_time=10.0,
            end_time=11.0,
            fade_out_time=11.3,
            clear_time=11.6
        )
        state = LineState(
            text="Test",
            timing=timing,
            y_position=100
        )
        
        event = line.create_ass_event(
            state=state,
            style=style,
            video_width=1920,
            config=config
        )
        # fmt: on

        # Check event properties
        assert event.type == "Dialogue"
        assert event.Layer == 0
        assert event.Style == style
        assert event.Start == 10.0
        assert event.End == 11.0

        # Check text formatting
        text = event.Text
        assert "\\an8" in text  # Top alignment
        assert "\\pos(960,100)" in text  # Centered horizontally
        assert f"\\fad({config.fade_in_ms},{config.fade_out_ms})" in text  # Fade effect
        assert "\\k0" in text  # Initial timing
        assert "\\kf100" in text  # Word duration

    def test_event_positioning(self, style, config):
        """Test event positioning with different video widths."""
        # fmt: off
        segment = create_segment([("Test", 1.0)])
        line = LyricsLine(segment=segment)
        
        state = LineState(
            text="Test",
            timing=LineTimingInfo(
                fade_in_time=10.0,
                end_time=11.0,
                fade_out_time=11.3,
                clear_time=11.6
            ),
            y_position=100
        )
        # fmt: on

        # Test with different video widths
        widths = [1920, 1280, 640]
        for width in widths:
            event = line.create_ass_event(state, style, width, config)
            assert f"\\pos({width//2},100)" in event.Text

    def test_fade_configuration(self, style, config):
        """Test fade effect with different configurations."""
        # fmt: off
        segment = create_segment([("Test", 1.0)])
        line = LyricsLine(segment=segment)
        
        state = LineState(
            text="Test",
            timing=LineTimingInfo(
                fade_in_time=10.0,
                end_time=11.0,
                fade_out_time=11.3,
                clear_time=11.6
            ),
            y_position=100
        )
        
        # Test with different fade configurations
        test_configs = []
        for fade_in, fade_out in [(100, 200), (300, 600), (500, 1000)]:
            cfg = ScreenConfig(line_height=60)
            cfg.fade_in_ms = fade_in
            cfg.fade_out_ms = fade_out
            test_configs.append(cfg)

        for cfg in test_configs:
            event = line.create_ass_event(state, style, 1920, cfg)
            assert f"\\fad({cfg.fade_in_ms},{cfg.fade_out_ms})" in event.Text

    def test_complex_line_event(self, style, config):
        """Test event creation with multiple words and gaps."""
        # fmt: off
        words = [
            ("First", 0.5),    # 10.0 - 10.5
            ("gap", 0.5),      # 11.0 - 11.5 (0.5s gap)
            ("here", 0.5),     # 12.0 - 12.5 (0.5s gap)
        ]
        segment = create_segment(words)
        
        # Manually adjust timing to create gaps
        segment.words[1].start_time = 11.0
        segment.words[1].end_time = 11.5
        segment.words[2].start_time = 12.0
        segment.words[2].end_time = 12.5
        
        line = LyricsLine(segment=segment)
        
        state = LineState(
            text=" ".join(word for word, _ in words),
            timing=LineTimingInfo(
                fade_in_time=10.0,
                end_time=12.5,
                fade_out_time=12.8,
                clear_time=13.1
            ),
            y_position=100
        )
        # fmt: on

        event = line.create_ass_event(state, style, 1920, config)

        # Check all components are present
        text = event.Text
        assert "\\an8" in text
        assert "\\pos(960,100)" in text
        assert f"\\fad({config.fade_in_ms},{config.fade_out_ms})" in text
        assert "\\k0" in text
        assert "\\kf50" in text  # Word durations
        assert "\\k50" in text  # Gaps
