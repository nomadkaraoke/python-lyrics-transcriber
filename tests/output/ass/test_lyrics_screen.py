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
        post_roll_time=1.0,
        fade_in_ms=300,
        fade_out_ms=300,
        cascade_delay_ms=200,
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
        # fmt: off
        lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
        ]
        # fmt: on
        timings = strategy.calculate_line_timings(lines)

        assert len(timings) == 2
        # First line should start with preshow
        assert timings[0].fade_in_time == 10.0 - config.target_preshow_time
        # Second line should follow after cascade delay
        assert timings[1].fade_in_time == timings[0].fade_in_time + (config.cascade_delay_ms / 1000)

    def test_timing_with_previous_lines(self, config, mock_logger):
        """Test timing calculation with previous active lines."""
        strategy = TimingStrategy(config, mock_logger)
        # fmt: off
        previous_lines = [
            (9.0, 100, "Previous 1"),  # Will clear at 9.6s
            (10.0, 160, "Previous 2"),  # Will clear at 10.6s
        ]
        # fmt: on
        current_lines = [create_line(11.0, 13.0, "New line")]

        timings = strategy.calculate_line_timings(current_lines, previous_lines)

        # Should wait for previous lines to clear
        clear_time = 10.0 + (config.fade_out_ms / 1000) + (config.position_clear_buffer_ms / 1000)
        assert timings[0].fade_in_time >= clear_time

    def test_timing_with_three_plus_lines(self, config, mock_logger):
        """Test timing calculation for third and subsequent lines."""
        # fmt: off
        strategy = TimingStrategy(config, mock_logger)
        lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(12.0, 14.0, "Line 2"),
            create_line(14.0, 16.0, "Line 3"),
            create_line(16.0, 18.0, "Line 4"),
        ]
        # fmt: on

        timings = strategy.calculate_line_timings(lines)

        # Each line should cascade after the first
        base_time = timings[0].fade_in_time
        for i, timing in enumerate(timings[1:], 1):
            expected = base_time + (i * config.cascade_delay_ms / 1000)
            assert timing.fade_in_time == expected

    def test_post_instrumental_detailed(self, config, mock_logger):
        """Test detailed timing aspects of post-instrumental screens."""
        # fmt: off
        strategy = TimingStrategy(config, mock_logger)
        lines = [
            create_line(20.0, 22.0, "Line 1"),
            create_line(22.0, 24.0, "Line 2"),
        ]
        # fmt: on

        timings = strategy.calculate_line_timings(lines, post_instrumental=True)

        # All lines should:
        # 1. Start at the same time
        # 2. Have individual end times
        # 3. Have correct fade out and clear times
        start_time = 20.0 - config.target_preshow_time
        assert all(t.fade_in_time == start_time for t in timings)

        for line, timing in zip(lines, timings):
            assert timing.end_time == line.segment.end_time + config.post_roll_time
            assert timing.fade_out_time == timing.end_time + (config.fade_out_ms / 1000)
            assert timing.clear_time == timing.fade_out_time + (config.position_clear_buffer_ms / 1000)

    def test_overlapping_previous_lines(self, config, mock_logger):
        """Test handling of overlapping previous lines."""
        # fmt: off
        strategy = TimingStrategy(config, mock_logger)
        previous_lines = [
            (10.0, 100, "Previous 1"),  # Line 1
            (11.0, 160, "Previous 2"),  # Line 2
            (12.0, 220, "Previous 3"),  # Line 3
        ]
        current_lines = [create_line(13.0, 15.0, "New line")]
        # fmt: on

        timings = strategy.calculate_line_timings(current_lines, previous_lines)

        # Should wait for all previous lines to clear
        latest_clear = 12.0 + (config.fade_out_ms / 1000) + (config.position_clear_buffer_ms / 1000)
        assert timings[0].fade_in_time >= latest_clear


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
        # fmt: off
        screen = LyricsScreen(
            video_size=video_size,
            line_height=config.line_height,
            config=config,
            logger=mock_logger
        )
        screen.lines = [
            create_line(10.0, 12.0, "Line 1"),
            create_line(11.0, 13.0, "Line 2"),  # Overlapping timing
            create_line(14.0, 16.0, "Line 3"),
        ]
        # fmt: on

        assert screen.start_ts == timedelta(seconds=10.0)
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
