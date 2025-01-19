from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging
from datetime import timedelta

from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.lyrics_line import LyricsLine
from lyrics_transcriber.output.ass.config import ScreenConfig, LineTimingInfo, LineState


class PositionStrategy:
    """Handles calculation of vertical positions for lines."""

    def __init__(self, video_size: Tuple[int, int], config: ScreenConfig):
        self.video_size = video_size
        self.config = config

    def calculate_line_positions(self) -> List[int]:
        """Calculate vertical positions for all possible lines."""
        return PositionCalculator.calculate_line_positions(self.config)


class PositionCalculator:
    """Shared position calculation logic."""

    @staticmethod
    def calculate_first_line_position(config: ScreenConfig) -> int:
        """Calculate vertical position of first line."""
        total_height = config.max_visible_lines * config.line_height
        return config.top_padding + (config.video_height - total_height - config.top_padding) // 4

    @staticmethod
    def calculate_line_positions(config: ScreenConfig) -> List[int]:
        """Calculate vertical positions for all possible lines."""
        first_pos = PositionCalculator.calculate_first_line_position(config)
        return [first_pos + (i * config.line_height) for i in range(config.max_visible_lines)]

    @staticmethod
    def position_to_line_index(y_position: int, config: ScreenConfig) -> int:
        """Convert y-position to 0-based line index."""
        first_pos = PositionCalculator.calculate_first_line_position(config)
        return (y_position - first_pos) // config.line_height

    @staticmethod
    def line_index_to_position(index: int, config: ScreenConfig) -> int:
        """Convert 0-based line index to y-position."""
        first_pos = PositionCalculator.calculate_first_line_position(config)
        return first_pos + (index * config.line_height)


class TimingStrategy:
    """Handles calculation of line timings during screen transitions."""

    def __init__(self, config: ScreenConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def calculate_line_timings(
        self,
        current_lines: List[LyricsLine],
        previous_active_lines: Optional[List[Tuple[float, int, str]]] = None,
        post_instrumental: bool = False,
    ) -> List[LineTimingInfo]:
        """Calculate timing information for each line in the screen."""
        if post_instrumental:
            return self._calculate_post_instrumental_timings(current_lines)

        previous_active_lines = previous_active_lines or []

        # Get first line timing as anchor point
        first_line = current_lines[0]
        first_line_fade_in = first_line.segment.start_time - self.config.target_preshow_time

        # Check if we need to wait for previous lines to clear
        if previous_active_lines:
            # Calculate latest clear time from ALL previous lines
            latest_clear_time = max(
                end + (self.config.fade_out_ms / 1000) + (self.config.position_clear_buffer_ms / 1000)
                for end, _, _ in previous_active_lines
            )
            first_line_fade_in = max(first_line_fade_in, latest_clear_time)
            self.logger.debug(f"    Waiting for lines to clear at {latest_clear_time:.2f}s")

        timings = []
        for i, line in enumerate(current_lines):
            timing = self._calculate_line_timing(
                line=line, line_index=i, first_line_fade_in=first_line_fade_in, previous_active_lines=previous_active_lines
            )
            timings.append(timing)

        return timings

    def _calculate_line_timing(
        self, line: LyricsLine, line_index: int, first_line_fade_in: float, previous_active_lines: List[Tuple[float, int, str]]
    ) -> LineTimingInfo:
        """Calculate timing for a single line."""
        # Base fade in time depends on line position
        if line_index == 0:
            fade_in_time = first_line_fade_in
        elif line_index == 1:
            # Line 2 follows after cascade delay, but must wait for previous line 2 to clear
            fade_in_time = first_line_fade_in + (self.config.cascade_delay_ms / 1000)
            if previous_active_lines:
                target_pos = PositionCalculator.line_index_to_position(1, self.config)
                line2_positions = [(end, pos, text) for end, pos, text in previous_active_lines if pos == target_pos]
                if line2_positions:
                    prev_line2 = line2_positions[0]
                    line2_clear_time = prev_line2[0] + (self.config.fade_out_ms / 1000) + (self.config.position_clear_buffer_ms / 1000)
                    fade_in_time = max(fade_in_time, line2_clear_time)
                    self.logger.debug(
                        f"    Previous Line 2 '{prev_line2[2]}' "
                        f"ends {prev_line2[0]:.2f}s, "
                        f"fade out {prev_line2[0] + (self.config.fade_out_ms / 1000):.2f}s, "
                        f"clears {line2_clear_time:.2f}s"
                    )
        else:
            # Lines 3+ must wait for all previous lines to clear
            if previous_active_lines:
                last_line = max(previous_active_lines, key=lambda x: x[0])
                last_line_index = PositionCalculator.position_to_line_index(last_line[1], self.config)
                last_line_clear_time = last_line[0] + (self.config.fade_out_ms / 1000) + (self.config.position_clear_buffer_ms / 1000)
                fade_in_time = last_line_clear_time + ((line_index - 2) * self.config.cascade_delay_ms / 1000)
                self.logger.debug(f"    Waiting for Line {last_line_index + 1} '{last_line[2]}' to clear at {last_line_clear_time:.2f}s")
            else:
                fade_in_time = first_line_fade_in + (line_index * self.config.cascade_delay_ms / 1000)

        # Calculate remaining timing information
        end_time = line.segment.end_time + self.config.post_roll_time
        fade_out_time = end_time + (self.config.fade_out_ms / 1000)
        clear_time = fade_out_time + (self.config.position_clear_buffer_ms / 1000)

        return LineTimingInfo(fade_in_time=fade_in_time, end_time=end_time, fade_out_time=fade_out_time, clear_time=clear_time)

    def _calculate_post_instrumental_timings(self, lines: List[LyricsLine]) -> List[LineTimingInfo]:
        """Calculate timings for post-instrumental screens where all lines appear together."""
        fade_in_start = lines[0].segment.start_time - self.config.target_preshow_time

        return [
            LineTimingInfo(
                fade_in_time=fade_in_start,
                end_time=line.segment.end_time + self.config.post_roll_time,
                fade_out_time=line.segment.end_time + self.config.post_roll_time + (self.config.fade_out_ms / 1000),
                clear_time=line.segment.end_time
                + self.config.post_roll_time
                + (self.config.fade_out_ms / 1000)
                + (self.config.position_clear_buffer_ms / 1000),
            )
            for line in lines
        ]


@dataclass
class LyricsScreen:
    """Represents a screen of lyrics (multiple lines)."""

    video_size: Tuple[int, int]
    line_height: int
    lines: List[LyricsLine] = None  # Make lines optional
    logger: Optional[logging.Logger] = None
    post_instrumental: bool = False
    config: Optional[ScreenConfig] = None

    def __post_init__(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        if self.config is None:
            self.config = ScreenConfig(line_height=self.line_height)
        else:
            # Ensure line_height is consistent
            self.config.line_height = self.line_height

        # Initialize empty lines list if None
        if self.lines is None:
            self.lines = []

        # Update video height in config
        self.config.video_height = self.video_size[1]

        # Initialize strategies
        self.position_strategy = PositionStrategy(self.video_size, self.config)
        self.timing_strategy = TimingStrategy(self.config, self.logger)

    def as_ass_events(
        self,
        style: Style,
        next_screen_start: Optional[timedelta] = None,
        previous_active_lines: List[Tuple[float, int, str]] = None,
    ) -> Tuple[List[Event], List[Tuple[float, int, str]]]:
        """Convert screen to ASS events. Returns (events, active_lines)."""
        events = []
        active_lines = []
        previous_active_lines = previous_active_lines or []

        # Log active lines from previous screen
        if previous_active_lines:
            self.logger.debug("  Active lines from previous screen:")
            for end, pos, text in previous_active_lines:
                # Convert y-position back to line index (0-based)
                line_index = PositionCalculator.position_to_line_index(pos, self.config)
                clear_time = end + (self.config.fade_out_ms / 1000) + (self.config.position_clear_buffer_ms / 1000)
                self.logger.debug(
                    f"    Line {line_index + 1}: '{text}' "
                    f"(ends {end:.2f}s, fade out {end + (self.config.fade_out_ms / 1000):.2f}s, clear {clear_time:.2f}s)"
                )

        # Calculate positions and timings
        positions = self.position_strategy.calculate_line_positions()
        timings = self.timing_strategy.calculate_line_timings(
            current_lines=self.lines, previous_active_lines=previous_active_lines, post_instrumental=self.post_instrumental
        )

        # Create line states and events
        for i, (line, timing) in enumerate(zip(self.lines, timings)):
            y_position = positions[i]

            # Create line state
            line_state = LineState(text=line.segment.text, timing=timing, y_position=y_position)

            # Create ASS event
            event = self._create_line_event(line, line_state, style)
            events.append(event)

            # Track active line
            active_lines.append((timing.end_time, y_position, line.segment.text))

            # Log line placement with index
            self.logger.debug(f"    Line {i + 1}: '{line.segment.text}'")

        return events, active_lines

    def _create_line_event(self, line: LyricsLine, state: LineState, style: Style) -> Event:
        """Create ASS event for a single line."""
        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = state.timing.fade_in_time
        e.End = state.timing.end_time

        # Use absolute positioning
        x_pos = self.video_size[0] // 2  # Center horizontally
        text = f"{{\\an8}}{{\\pos({x_pos},{state.y_position})}}{line._create_ass_text(timedelta(seconds=state.timing.fade_in_time))}"
        e.Text = text

        return e

    @property
    def start_ts(self) -> timedelta:
        """Get screen start timestamp."""
        return timedelta(seconds=min(line.segment.start_time for line in self.lines))

    @property
    def end_ts(self) -> timedelta:
        """Get screen end timestamp."""
        latest_ts = max(line.segment.end_time for line in self.lines)
        return timedelta(seconds=latest_ts + self.config.post_roll_time)

    def __str__(self):
        return "\n".join([f"{self.start_ts} - {self.end_ts}:", *[f"\t{line}" for line in self.lines]])
