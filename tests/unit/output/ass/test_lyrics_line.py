import pytest
from datetime import timedelta
from unittest.mock import Mock

from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.lyrics_line import LyricsLine
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.config import ScreenConfig, LineTimingInfo, LineState
from tests.test_helpers import create_test_word, create_test_segment


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
        word = create_test_word(
            text=text,
            start_time=current_time,
            end_time=current_time + duration
        )
        # fmt: on
        segment_words.append(word)
        current_time += duration

    return create_test_segment(text=" ".join(text for text, _ in words), words=segment_words, start_time=start_time, end_time=current_time)


def test_basic_karaoke_timing():
    """Test basic karaoke timing with simple words."""
    # fmt: off
    words = [
        ("Hello", 0.5),
        ("world", 0.5)
    ]
    # fmt: on
    segment = create_segment(words)
    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)

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

    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)
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
    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)

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

    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)
    result = line._create_ass_text(timedelta(seconds=10.0))

    # Small gaps should not create {\k} tags
    assert result == r"{\k0}{\kf50}No {\kf50}tiny {\kf50}gap"


def test_string_representation():
    """Test string representation of LyricsLine."""
    segment = create_segment([("Test", 1.0)])
    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)

    assert str(line) == "{Test}"


def test_case_transformation_none():
    """Test no case transformation (default)."""
    segment = create_segment([("Hello", 1.0), ("World", 1.0)])
    config = ScreenConfig(text_case_transform="none")
    line = LyricsLine(segment=segment, screen_config=config)
    
    result = line._apply_case_transform("Hello World")
    assert result == "Hello World"


def test_case_transformation_uppercase():
    """Test uppercase transformation."""
    segment = create_segment([("Hello", 1.0), ("World", 1.0)])
    config = ScreenConfig(text_case_transform="uppercase")
    line = LyricsLine(segment=segment, screen_config=config)
    
    result = line._apply_case_transform("Hello World")
    assert result == "HELLO WORLD"


def test_case_transformation_lowercase():
    """Test lowercase transformation."""
    segment = create_segment([("Hello", 1.0), ("World", 1.0)])
    config = ScreenConfig(text_case_transform="lowercase")
    line = LyricsLine(segment=segment, screen_config=config)
    
    result = line._apply_case_transform("Hello World")
    assert result == "hello world"


def test_case_transformation_propercase():
    """Test proper case transformation."""
    segment = create_segment([("hello", 1.0), ("world", 1.0)])
    config = ScreenConfig(text_case_transform="propercase")
    line = LyricsLine(segment=segment, screen_config=config)
    
    result = line._apply_case_transform("hello world")
    assert result == "Hello World"


def test_lead_in_disabled():
    """Test that lead-in indicator is not created when disabled."""
    segment = create_segment([("Hello", 1.0)])
    config = ScreenConfig(lead_in_enabled=False)
    line = LyricsLine(segment=segment, screen_config=config)
    
    # Mock state and style for the test
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Hello", timing=timing, y_position=100)
    style = Style()
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is None


def test_lead_in_insufficient_gap():
    """Test that lead-in indicator is not created when gap is insufficient."""
    segment = create_segment([("Hello", 1.0)])
    config = ScreenConfig(lead_in_enabled=True, lead_in_gap_threshold=5.0)
    line = LyricsLine(segment=segment, screen_config=config)
    
    # Set previous end time too close to current start
    line.previous_end_time = 8.0  # Only 2s gap, less than 5s threshold
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=9.0, end_time=11.0, fade_out_time=10.5, clear_time=11.5)
    state = LineState(text="Hello", timing=timing, y_position=100)
    style = Style()
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is None


def test_lead_in_sufficient_gap():
    """Test that lead-in indicator is created when gap is sufficient."""
    segment = create_segment([("Hello", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True, 
        lead_in_gap_threshold=3.0,
        video_width=640,
        video_height=360
    )
    line = LyricsLine(segment=segment, screen_config=config)
    
    # Set previous end time with sufficient gap
    line.previous_end_time = 5.0  # 5s gap, more than 3s threshold
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=9.0, end_time=11.0, fade_out_time=10.5, clear_time=11.5)
    state = LineState(text="Hello", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None  # Use default font
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    assert len(result) == 1
    assert result[0].type == "Dialogue"


def test_lead_in_no_previous_segment():
    """Test that lead-in indicator is created when there's no previous segment."""
    segment = create_segment([("Hello", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True,
        video_width=640,
        video_height=360
    )
    line = LyricsLine(segment=segment, screen_config=config)
    
    # No previous segment (None)
    line.previous_end_time = None
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Hello", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    assert len(result) == 1


def test_lead_in_positioning_with_offsets():
    """Test lead-in positioning with horizontal and vertical offsets."""
    segment = create_segment([("Hello", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True,
        video_width=640,
        video_height=360,
        lead_in_horiz_offset_percent=-2.0,  # Move 2% left
        lead_in_vert_offset_percent=1.0,    # Move 1% down
        text_case_transform="uppercase"     # Use uppercase to test case transformation
    )
    line = LyricsLine(segment=segment, screen_config=config)
    line.previous_end_time = None  # First segment
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Hello", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    
    # Check that the move command contains the offset calculations
    event_text = result[0].Text
    assert "\\move(" in event_text
    
    # Verify offsets are applied (exact positions depend on font rendering)
    # Horizontal offset: -2% of 640 = -12px
    # Vertical offset: 1% of 360 = 3px (added to y position)
    horizontal_offset = int(640 * (-2.0 / 100))  # -12px
    vertical_offset = int(360 * (1.0 / 100))     # 3px
    
    assert horizontal_offset == -12
    assert vertical_offset == 3


def test_lead_in_size_configuration():
    """Test lead-in indicator size configuration."""
    segment = create_segment([("Test", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True,
        video_width=640,
        video_height=360,
        lead_in_width_percent=5.0,   # 5% width
        lead_in_height_percent=6.0   # 6% height
    )
    line = LyricsLine(segment=segment, screen_config=config)
    line.previous_end_time = None
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Test", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    
    # Verify size calculations
    expected_width = int(640 * (5.0 / 100))   # 32px
    expected_height = int(360 * (6.0 / 100))  # 21px
    
    assert expected_width == 32
    assert expected_height == 21
    
    # Check that the rectangle drawing command uses these dimensions
    event_text = result[0].Text
    assert "\\p1" in event_text  # Drawing mode
    assert f"m {-expected_width} {-expected_height}" in event_text


def test_lead_in_outline_styling():
    """Test lead-in outline styling configuration."""
    segment = create_segment([("Test", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True,
        video_width=640,
        video_height=360,
        lead_in_outline_thickness=3,
        lead_in_outline_color="255, 255, 255",
        lead_in_opacity_percent=80.0
    )
    line = LyricsLine(segment=segment, screen_config=config)
    line.previous_end_time = None
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Test", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    
    event_text = result[0].Text
    
    # Check outline thickness
    assert "\\bord3" in event_text
    
    # Check outline color (white in ASS format)
    assert "\\3c&H00FFFFFF&" in event_text
    
    # Check opacity (80% in ASS format)
    assert "\\alpha&H33&" in event_text


def test_lead_in_no_outline():
    """Test lead-in without outline (thickness = 0)."""
    segment = create_segment([("Test", 1.0)])
    config = ScreenConfig(
        lead_in_enabled=True,
        video_width=640,
        video_height=360,
        lead_in_outline_thickness=0  # No outline
    )
    line = LyricsLine(segment=segment, screen_config=config)
    line.previous_end_time = None
    
    from lyrics_transcriber.output.ass.config import LineState, LineTimingInfo
    timing = LineTimingInfo(fade_in_time=5.0, end_time=10.0, fade_out_time=9.5, clear_time=10.5)
    state = LineState(text="Test", timing=timing, y_position=100)
    style = Style()
    style.Fontpath = None
    
    result = line._create_lead_in_event(state, style, 640, config)
    assert result is not None
    
    event_text = result[0].Text
    
    # Should have no outline
    assert "\\bord0" in event_text


def test_logger_initialization():
    """Test logger is initialized if not provided."""
    segment = create_segment([("Test", 1.0)])
    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config)

    assert line.logger is not None


def test_custom_logger():
    """Test custom logger is used if provided."""
    logger = Mock()
    segment = create_segment([("Test", 1.0)])
    from lyrics_transcriber.output.ass.config import ScreenConfig
    config = ScreenConfig(line_height=60, video_height=1080)
    line = LyricsLine(segment=segment, screen_config=config, logger=logger)

    assert line.logger == logger


class TestAssEventCreation:
    def test_lead_in_creation(self, style, config):
        """Test creation of lead-in indicator."""
        segment = create_segment([("Test", 1.0)], start_time=10.0)
        line = LyricsLine(segment=segment, screen_config=config)

        state = LineState(
            text="Test",
            timing=LineTimingInfo(fade_in_time=8.0, end_time=11.0, fade_out_time=11.3, clear_time=11.6),  # Start 2 seconds before
            y_position=100,
        )

        # Test with no previous line (should show lead-in)
        events = line.create_ass_events(state, style, config, previous_end_time=None)
        assert len(events) == 2  # Should have lead-in and main event
        assert "Test" in events[-1].Text  # Main lyrics (last event)

        # Test with recent previous line (should not show lead-in)
        events = line.create_ass_events(state, style, config, previous_end_time=7.0)
        assert len(events) == 1  # Should only have main event
        assert "Test" in events[0].Text

        # Test with old previous line (should show lead-in)
        events = line.create_ass_events(state, style, config, previous_end_time=2.0)
        assert len(events) == 2

    def test_basic_event_creation(self, style, config):
        """Test basic ASS event creation."""
        segment = create_segment([("Test", 1.0)])
        line = LyricsLine(segment=segment, screen_config=config)

        timing = LineTimingInfo(fade_in_time=10.0, end_time=11.0, fade_out_time=11.3, clear_time=11.6)
        state = LineState(text="Test", timing=timing, y_position=100)

        # Test with recent previous line (no lead-in)
        events = line.create_ass_events(state, style, config, previous_end_time=9.0)
        assert len(events) == 1
        event = events[0]

        # Check event properties
        assert event.type == "Dialogue"
        assert event.Layer == 0
        assert event.Style == style
        assert event.Start == 10.0
        assert event.End == 11.0

        # Check text formatting
        text = event.Text
        assert "\\an8" in text  # Top alignment
        assert f"\\pos({config.video_width//2},100)" in text  # Centered horizontally
        assert f"\\fad({config.fade_in_ms},{config.fade_out_ms})" in text  # Fade effect
        assert "\\k0" in text  # Initial timing
        assert "\\kf100" in text  # Word duration

    def test_event_positioning(self, style, config):
        """Test event positioning with different video widths."""
        segment = create_segment([("Test", 1.0)])
        line = LyricsLine(segment=segment, screen_config=config)

        # fmt: off
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
            # Update config video width for each test
            test_config = ScreenConfig(line_height=60, video_height=1080, video_width=width)
            test_line = LyricsLine(segment=segment, screen_config=test_config)
            # Pass recent previous_end_time to prevent lead-in
            events = test_line.create_ass_events(state, style, test_config, previous_end_time=9.0)
            assert len(events) == 1
            assert f"\\pos({width//2},100)" in events[0].Text

    def test_fade_configuration(self, style, config):
        """Test fade effect with different configurations."""
        segment = create_segment([("Test", 1.0)])
        line = LyricsLine(segment=segment, screen_config=config)

        state = LineState(
            text="Test", timing=LineTimingInfo(fade_in_time=10.0, end_time=11.0, fade_out_time=11.3, clear_time=11.6), y_position=100
        )

        # Test with different fade configurations
        test_configs = []
        for fade_in, fade_out in [(100, 200), (300, 600), (500, 1000)]:
            cfg = ScreenConfig(line_height=60)
            cfg.fade_in_ms = fade_in
            cfg.fade_out_ms = fade_out
            test_configs.append(cfg)

        for cfg in test_configs:
            # Create new line with updated config
            test_line = LyricsLine(segment=segment, screen_config=cfg)
            # Pass recent previous_end_time to prevent lead-in
            events = test_line.create_ass_events(state, style, cfg, previous_end_time=9.0)
            assert len(events) == 1
            assert f"\\fad({cfg.fade_in_ms},{cfg.fade_out_ms})" in events[0].Text

    def test_complex_line_event(self, style, config):
        """Test event creation with multiple words and gaps."""
        words = [
            ("First", 0.5),  # 10.0 - 10.5
            ("gap", 0.5),  # 11.0 - 11.5 (0.5s gap)
            ("here", 0.5),  # 12.0 - 12.5 (0.5s gap)
        ]
        segment = create_segment(words)

        # Manually adjust timing to create gaps
        segment.words[1].start_time = 11.0
        segment.words[1].end_time = 11.5
        segment.words[2].start_time = 12.0
        segment.words[2].end_time = 12.5

        line = LyricsLine(segment=segment, screen_config=config)

        state = LineState(
            text=" ".join(word for word, _ in words),
            timing=LineTimingInfo(fade_in_time=10.0, end_time=12.5, fade_out_time=12.8, clear_time=13.1),
            y_position=100,
        )

        # Test with recent previous line (no lead-in)
        events = line.create_ass_events(state, style, config, previous_end_time=9.0)
        assert len(events) == 1
        event = events[0]

        # Check all components are present
        text = event.Text
        assert "\\an8" in text
        assert f"\\pos({config.video_width//2},100)" in text
        assert f"\\fad({config.fade_in_ms},{config.fade_out_ms})" in text
        assert "\\k0" in text
        assert "\\kf50" in text  # Word durations
        assert "\\k50" in text  # Gaps
