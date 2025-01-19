import pytest
from unittest.mock import Mock
from datetime import timedelta

from lyrics_transcriber.output.ass.lyrics_screen import PositionCalculator, TimingStrategy
from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass import LyricsScreen, Style, ScreenConfig
from lyrics_transcriber.output.ass.lyrics_line import LyricsLine


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
    return ScreenConfig(
        max_visible_lines=4,
        line_height=60,
        top_padding=60,
        video_height=1080,
    )


@pytest.fixture
def video_size():
    return (1920, 1080)


def create_line(start: float, end: float, text: str, logger=None) -> LyricsLine:
    """Helper to create a LyricsLine with a single word."""
    segment = LyricsSegment(text=text, words=[Word(text=text, start_time=start, end_time=end)], start_time=start, end_time=end)
    return LyricsLine(segment=segment, logger=logger)


class TestPositionCalculator:
    def test_first_line_position(self, config):
        """Test calculation of first line position."""
        pos = PositionCalculator.calculate_first_line_position(config)

        # First line should be in top quarter of usable space
        total_height = config.max_visible_lines * config.line_height
        expected = config.top_padding + (config.video_height - total_height - config.top_padding) // 4
        assert pos == expected

    def test_line_positions(self, config):
        """Test calculation of all line positions."""
        positions = PositionCalculator.calculate_line_positions(config)

        assert len(positions) == config.max_visible_lines
        # Verify consistent spacing
        for i in range(1, len(positions)):
            assert positions[i] - positions[i - 1] == config.line_height

    def test_position_line_index_conversion(self, config):
        """Test conversion between positions and line indices."""
        # fmt: off
        test_indices = [0, 1, 2, 3]
        
        # Convert index -> position -> index
        for idx in test_indices:
            pos = PositionCalculator.line_index_to_position(idx, config)
            back_to_idx = PositionCalculator.position_to_line_index(pos, config)
            assert back_to_idx == idx
        # fmt: on


class TestTimingStrategy:
    def test_basic_timing(self, config, mock_logger):
        """Test basic timing calculation without previous lines."""
        strategy = TimingStrategy(config, mock_logger)
        lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
        ]

        # Without previous lines or instrumental end, should start at 0
        timings = strategy.calculate_line_timings(lines)
        assert len(timings) == 2
        assert timings[0].fade_in_time == 0.0  # Changed: starts at 0 without previous lines
        assert timings[1].fade_in_time == 0.0  # Changed: simultaneous timing

    def test_timing_with_previous_lines(self, config, mock_logger):
        """Test timing calculation with previous active lines."""
        strategy = TimingStrategy(config, mock_logger)
        previous_lines = [
            (9.0, 100, "Previous 1"),
            (10.0, 160, "Previous 2"),
        ]
        current_lines = [create_line(11.0, 13.0, "New line")]

        timings = strategy.calculate_line_timings(current_lines, previous_lines)

        # Lines should start at their natural start time since we want simultaneous timing
        assert timings[0].fade_in_time == 0.0
        # Verify other timing aspects
        assert timings[0].end_time == 14.0  # 13.0 + post_roll
        assert timings[0].fade_out_time == pytest.approx(14.4)  # end + fade_out
        assert timings[0].clear_time == pytest.approx(14.7)  # fade_out + clear_buffer

    def test_timing_with_three_plus_lines(self, config, mock_logger):
        """Test timing calculation for third and subsequent lines."""
        strategy = TimingStrategy(config, mock_logger)
        lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
            create_line(14.0, 16.0, "Line 3"),
            create_line(16.0, 18.0, "Line 4"),
        ]

        timings = strategy.calculate_line_timings(lines)

        # All lines should start simultaneously at 0 when no previous lines
        assert all(t.fade_in_time == 0.0 for t in timings)
        # Each line should end at its own time
        for line, timing in zip(lines, timings):
            assert timing.end_time == line.segment.end_time + config.post_roll_time

    def test_post_instrumental_detailed(self, config, mock_logger):
        """Test detailed timing aspects of post-instrumental screens."""
        strategy = TimingStrategy(config, mock_logger)
        lines = [
            create_line(20.0, 22.0, "Line 1"),
            create_line(22.0, 24.0, "Line 2"),
        ]

        # Set previous_instrumental_end to simulate post-instrumental timing
        timings = strategy.calculate_line_timings(lines, previous_instrumental_end=15.0)

        # All lines should start at instrumental end time
        assert all(t.fade_in_time == 15.0 for t in timings)
        # Each line should have its own end time
        for line, timing in zip(lines, timings):
            assert timing.end_time == line.segment.end_time + config.post_roll_time
            assert timing.fade_out_time == timing.end_time + (config.fade_out_ms / 1000)
            assert timing.clear_time == timing.fade_out_time + (config.position_clear_buffer_ms / 1000)

    def test_overlapping_previous_lines(self, config, mock_logger):
        """Test handling of overlapping previous lines."""
        strategy = TimingStrategy(config, mock_logger)
        previous_lines = [
            (10.0, 100, "Previous 1"),  # Line 1
            (11.0, 160, "Previous 2"),  # Line 2
            (12.0, 220, "Previous 3"),  # Line 3
        ]
        current_lines = [create_line(13.0, 15.0, "New line")]

        timings = strategy.calculate_line_timings(current_lines, previous_lines)

        # Lines should start at their natural start time
        assert timings[0].fade_in_time == 0.0
        # Verify other timing aspects
        assert timings[0].end_time == 16.0  # 15.0 + post_roll
        assert timings[0].fade_out_time == pytest.approx(16.4)  # end + fade_out
        assert timings[0].clear_time == pytest.approx(16.7)  # fade_out + clear_buffer


class TestLyricsScreen:
    def test_screen_initialization(self, video_size, config, mock_logger):
        """Test screen initialization and configuration."""
        # fmt: off
        screen = LyricsScreen(
            video_size=video_size,
            line_height=config.line_height,
            config=config,
            logger=mock_logger
        )
        # fmt: on

        assert screen.video_size == video_size
        assert screen.config.line_height == config.line_height
        assert screen.config.video_height == video_size[1]
        assert screen.lines == []

    def test_event_generation(self, video_size, config, style, mock_logger):
        """Test generation of ASS events."""
        # fmt: off
        screen = LyricsScreen(
            video_size=video_size,
            line_height=config.line_height,
            config=config,
            logger=mock_logger
        )
        screen.lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
        ]
        # fmt: on

        events, active_lines = screen.as_ass_events(style)

        assert len(events) == 2
        assert len(active_lines) == 2
        # Verify event formatting
        assert all("\\an8" in e.Text for e in events)  # Top alignment
        assert all("\\pos" in e.Text for e in events)  # Position tag
        assert all(e.Style == style for e in events)

    def test_post_instrumental_timing(self, video_size, config, style, mock_logger):
        """Test timing for post-instrumental screens."""
        # fmt: off
        screen = LyricsScreen(
            video_size=video_size,
            line_height=config.line_height,
            config=config,
            logger=mock_logger,
            post_instrumental=True
        )
        screen.lines = [
            create_line(20.0, 22.0, "Line 1"),
            create_line(22.0, 24.0, "Line 2"),
        ]
        # fmt: on

        events, _ = screen.as_ass_events(style)

        # All lines should start at the same time
        assert all(e.Start == events[0].Start for e in events)

    def test_config_initialization(self, video_size, mock_logger):
        """Test configuration initialization and overrides."""
        # fmt: off
        custom_config = ScreenConfig(
            line_height=70,  # Different from default
            max_visible_lines=3
        )
        
        # Test with custom config
        screen1 = LyricsScreen(
            video_size=video_size,
            line_height=70,
            config=custom_config,
            logger=mock_logger
        )
        assert screen1.config.line_height == 70
        assert screen1.config.max_visible_lines == 3
        
        # Test with default config
        screen2 = LyricsScreen(
            video_size=video_size,
            line_height=80,
            logger=mock_logger
        )
        assert screen2.config.line_height == 80  # Should override default
        assert screen2.config.max_visible_lines == 4  # Should use default
        # fmt: on

    def test_screen_timestamps(self, video_size, config, mock_logger):
        """Test screen start and end timestamp calculations."""
        screen = LyricsScreen(video_size=video_size, line_height=config.line_height, config=config, logger=mock_logger)
        screen.lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(11.0, 13.0, "Line 2"),  # Overlapping timing
            create_line(14.0, 16.0, "Line 3"),
        ]

        assert screen.start_ts == timedelta(seconds=10.0)
        # End timestamp should include post_roll_time
        assert screen.end_ts == timedelta(seconds=16.0 + config.post_roll_time)

    def test_string_representation(self, video_size, config, mock_logger):
        """Test string representation of screen."""
        # fmt: off
        screen = LyricsScreen(
            video_size=video_size,
            line_height=config.line_height,
            config=config,
            logger=mock_logger
        )
        screen.lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
        ]
        # fmt: on

        result = str(screen)
        assert "0:00:10" in result  # Start time
        assert "0:00:15" in result  # End time (14.0 + post_roll)
        assert "Line 1" in result
        assert "Line 2" in result
