import logging
from datetime import timedelta
from unittest.mock import Mock

import pytest

from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen, LyricsLine
from lyrics_transcriber.output.ass.style import Style


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


@pytest.fixture
def style():
    style = Style()
    style.Name = "Test"
    return style


@pytest.fixture
def video_size():
    return (1920, 1080)


@pytest.fixture
def line_height():
    return 60


@pytest.fixture
def screen(video_size, line_height, mock_logger):
    return LyricsScreen(video_size=video_size, line_height=line_height, logger=mock_logger)


def create_word(text: str, start: float, end: float, confidence: float = 1.0) -> Word:
    """Helper to create a Word."""
    return Word(text=text, start_time=start, end_time=end, confidence=confidence)


def create_segment(start: float, end: float, text: str) -> LyricsSegment:
    """Helper to create a LyricsSegment with words."""
    # Create a single word spanning the entire segment
    words = [create_word(text=text, start=start, end=end)]
    return LyricsSegment(text=text, words=words, start_time=start, end_time=end)


def create_line(start: float, end: float, text: str, logger=None) -> LyricsLine:
    """Helper to create a LyricsLine."""
    return LyricsLine(segment=create_segment(start, end, text), logger=logger)


class TestLyricsScreen:
    def test_initialization(self, screen, video_size, line_height, mock_logger):
        assert screen.video_size == video_size
        assert screen.line_height == line_height
        assert screen.logger == mock_logger
        assert screen.lines == []
        assert screen.MAX_VISIBLE_LINES == 4

    def test_calculate_first_line_position(self, screen):
        # Add some lines to test position calculation
        screen.lines = [
            create_line(0, 1, "Line 1"),
            create_line(1, 2, "Line 2"),
        ]

        position = screen._calculate_first_line_position()

        # Position should include top padding and be in top quarter of screen
        expected_total_height = len(screen.lines) * screen.line_height
        expected_top_padding = screen.line_height
        expected_position = expected_top_padding + (screen.video_size[1] - expected_total_height - expected_top_padding) // 4

        assert position == expected_position

    def test_unified_screen_timing(self, screen, style):
        """Test timing of unified screen with multiple lines."""
        screen.lines = [
            create_line(1, 2, "Line 1"),
            create_line(2, 3, "Line 2"),
            create_line(3, 4, "Line 3"),
        ]

        events, active_lines = screen.as_ass_events(style=style, next_screen_start=None, is_unified_screen=True, previous_active_lines=None)

        assert len(events) == 3
        assert len(active_lines) == 3

        # All lines should start at the same time (with preshow)
        start_time = 1 - screen.TARGET_PRESHOW_TIME
        for event in events:
            assert abs(event.Start - start_time) < 0.001

    def test_non_unified_screen_timing(self, screen, style):
        """Test timing of non-unified screen with line limits."""
        screen.lines = [
            create_line(1, 2, "Line 1"),
            create_line(2, 3, "Line 2"),
            create_line(3, 4, "Line 3"),
            create_line(4, 5, "Line 4"),
            create_line(5, 6, "Line 5"),  # Should wait for space
        ]

        events, active_lines = screen.as_ass_events(
            style=style, next_screen_start=None, is_unified_screen=False, previous_active_lines=None
        )

        assert len(events) == 5
        # Verify MAX_VISIBLE_LINES is respected
        max_concurrent = 0
        current_lines = []

        for event in events:
            # Remove ended lines
            current_lines = [line for line in current_lines if line[1] > event.Start]
            current_lines.append((event.Start, event.End))
            max_concurrent = max(max_concurrent, len(current_lines))

        assert max_concurrent <= screen.MAX_VISIBLE_LINES

    def test_active_lines_tracking(self, screen, style):
        """Test that active lines are properly tracked between screens."""
        # Create previous active lines
        previous_active_lines = [
            (2.0, 100, "Previous line 1"),
            (3.0, 160, "Previous line 2"),
        ]

        screen.lines = [
            create_line(1, 4, "New line 1"),
            create_line(2, 5, "New line 2"),
        ]

        events, active_lines = screen.as_ass_events(
            style=style, next_screen_start=None, is_unified_screen=False, previous_active_lines=previous_active_lines
        )

        # Verify previous lines are considered
        assert len(active_lines) > 0
        # Verify lines are sorted by end time
        end_times = [end for end, _, _ in active_lines]
        assert end_times == sorted(end_times)

    def test_line_positioning(self, screen, style):
        """Test vertical positioning of lines."""
        screen.lines = [
            create_line(1, 2, "Line 1"),
            create_line(2, 3, "Line 2"),
        ]

        events, _ = screen.as_ass_events(style=style, next_screen_start=None, is_unified_screen=True, previous_active_lines=None)

        # Verify increasing vertical positions
        positions = [event.MarginV for event in events]
        assert positions == sorted(positions)
        # Verify line height spacing
        for i in range(1, len(positions)):
            assert positions[i] - positions[i - 1] == screen.line_height

    def test_screen_gap_handling(self, screen, style):
        """Test handling of gaps between screens."""
        next_screen_start = timedelta(seconds=10)
        screen.lines = [create_line(1, 2, "Line 1")]

        events, active_lines = screen.as_ass_events(
            style=style, next_screen_start=next_screen_start, is_unified_screen=False, previous_active_lines=None
        )

        # Verify lines don't extend past next screen
        for event in events:
            assert event.End <= next_screen_start.total_seconds()

    def test_empty_screen(self, screen, style):
        """Test handling of empty screen."""
        events, active_lines = screen.as_ass_events(
            style=style, next_screen_start=None, is_unified_screen=False, previous_active_lines=None
        )

        assert events == []
        assert active_lines == []

    def test_real_song_scenario(self, screen, style, mock_logger):
        """Test a real song scenario with multiple screens and complex timing."""
        # Screen 1 - Unified screen with 4 lines
        screen1 = LyricsScreen(video_size=screen.video_size, line_height=screen.line_height, logger=mock_logger)
        screen1.lines = [
            create_line(17.98, 19.94, "I know I have good judgement", mock_logger),
            create_line(20.26, 22.10, "I know I have good taste", mock_logger),
            create_line(22.36, 24.40, "It's funny and it's ironic", mock_logger),
            create_line(24.62, 26.58, "That only I feel that way", mock_logger),
        ]

        # Screen 2 - Non-unified screen with 4 lines
        screen2 = LyricsScreen(video_size=screen.video_size, line_height=screen.line_height, logger=mock_logger)
        screen2.lines = [
            create_line(26.62, 28.60, "I promise em that you're different", mock_logger),
            create_line(29.08, 30.96, "And everyone makes mistakes,", mock_logger),
            create_line(31.02, 32.84, "but just don't", mock_logger),
            create_line(35.98, 37.82, "I heard that you're an actor", mock_logger),
        ]

        # Process Screen 1 (unified)
        events1, active_lines = screen1.as_ass_events(
            style=style,
            next_screen_start=screen2.start_ts,
            is_unified_screen=True,
            previous_active_lines=[]
        )

        # Verify Screen 1 behavior
        assert len(events1) == 4
        assert len(active_lines) == 4

        # All lines in unified screen should start at the same time
        first_start = events1[0].Start
        for event in events1:
            assert abs(event.Start - first_start) < 0.001

        # Verify active lines are properly tracked
        active_ends = [end for end, _, _ in active_lines]
        assert len(active_ends) == 4
        assert active_ends == sorted(active_ends)  # Should be sorted by end time

        # Process Screen 2 (non-unified)
        events2, active_lines = screen2.as_ass_events(
            style=style,
            next_screen_start=None,
            is_unified_screen=False,
            previous_active_lines=active_lines
        )

        # Verify Screen 2 behavior
        assert len(events2) == 4

        # Verify line timing constraints
        max_concurrent = 0
        current_lines = []
        for event in events2:
            # Remove ended lines
            current_lines = [line for line in current_lines if line[1] > event.Start]
            current_lines.append((event.Start, event.End))
            max_concurrent = max(max_concurrent, len(current_lines))

        # Verify MAX_VISIBLE_LINES is respected
        assert max_concurrent <= screen2.MAX_VISIBLE_LINES

        # Verify specific timing behaviors for each line
        for i, event in enumerate(events2):
            original_line = screen2.lines[i]
            # Line should not start before its target start time minus pre-roll
            assert event.Start >= original_line.segment.start_time - LyricsLine.PRE_ROLL_TIME, \
                f"Line {i+1} at {event.Start} starts too early (before {original_line.segment.start_time - LyricsLine.PRE_ROLL_TIME})"
            # Line should end after its target end time plus post-roll
            assert event.End >= original_line.segment.end_time + LyricsLine.POST_ROLL_TIME, \
                f"Line {i+1} at {event.End} ends too early (before {original_line.segment.end_time + LyricsLine.POST_ROLL_TIME})"
        
        # Verify fade effects and formatting
        for event in events2:
            assert "\\fad(300,300)" in event.Text  # Fade effect
            assert "\\an8" in event.Text  # Top-center alignment
            assert event.MarginV > 0  # Vertical position set

        # Verify vertical positioning
        positions = [event.MarginV for event in events2]
        assert positions == sorted(positions)  # Increasing positions
        for i in range(1, len(positions)):
            assert positions[i] - positions[i-1] == screen.line_height  # Consistent spacing


class TestLyricsLine:
    def test_karaoke_timing(self, mock_logger):
        """Test karaoke text generation with multiple words."""
        words = [
            create_word("Hello", 1.0, 1.5),
            create_word("world", 2.0, 2.8),
        ]
        segment = LyricsSegment(text="Hello world", words=words, start_time=1.0, end_time=2.8)
        line = LyricsLine(segment=segment, logger=mock_logger)

        text = line._create_karaoke_text(timedelta(seconds=0))

        # Verify timing tags are present
        assert "\\k100" in text  # 1.0s initial delay
        assert "\\kf50" in text  # Hello (0.5s)
        assert "\\k50" in text  # Gap between words (0.5s)
        assert "\\kf79" in text  # world (0.8s, rounded to centiseconds)

    def test_line_timing(self, mock_logger, style):
        """Test line timing with pre/post roll."""
        segment = create_segment(10.0, 12.0, "Test line")
        line = LyricsLine(segment=segment, logger=mock_logger)

        # Test with screen bounds that allow full pre/post roll
        event = line.as_ass_event(
            screen_start=timedelta(seconds=0.0), screen_end=timedelta(seconds=15.0), style=style, y_position=100  # Allow full pre-roll
        )

        # Should start 5s before segment (PRE_ROLL_TIME)
        assert event.Start == 5.0  # 10.0 - 5.0
        # Should end 2s after segment (POST_ROLL_TIME)
        assert event.End == 14.0  # 12.0 + 2.0

    def test_line_timing_with_screen_bounds(self, mock_logger, style):
        """Test line timing when constrained by screen bounds."""
        segment = create_segment(10.0, 12.0, "Test line")
        line = LyricsLine(segment=segment, logger=mock_logger)

        # Test with screen bounds that constrain timing
        event = line.as_ass_event(
            screen_start=timedelta(seconds=8.0),  # Constrains pre-roll
            screen_end=timedelta(seconds=13.0),  # Constrains post-roll
            style=style,
            y_position=100,
        )

        # Should be constrained by screen bounds
        assert event.Start == 8.0  # Constrained by screen_start
        assert event.End == 13.0  # Constrained by screen_end
