from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging
from datetime import timedelta

from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.lyrics_models.lyrics_line import LyricsLine


@dataclass
class LyricsScreen:
    """Represents a screen of lyrics (multiple lines)."""

    video_size: Tuple[int, int]
    line_height: int
    lines: List[LyricsLine] = field(default_factory=list)
    logger: Optional[logging.Logger] = None
    MAX_VISIBLE_LINES = 4
    SCREEN_GAP_THRESHOLD = 5.0
    POST_ROLL_TIME = 0.0
    FADE_IN_MS = 100
    FADE_OUT_MS = 100
    TARGET_PRESHOW_TIME = 5.0
    POSITION_CLEAR_BUFFER_MS = 300

    def __post_init__(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def start_ts(self) -> timedelta:
        """Get screen start timestamp."""
        return timedelta(seconds=min(line.segment.start_time for line in self.lines))

    @property
    def end_ts(self) -> timedelta:
        """Get screen end timestamp."""
        latest_ts = max(line.segment.end_time for line in self.lines)
        return timedelta(seconds=latest_ts + self.POST_ROLL_TIME)

    def _visualize_timeline(self, active_lines: List[Tuple[float, int, str]], current_time: float, new_line_end: float, new_line_text: str):
        """Create ASCII visualization of line timing."""
        timeline = ["Timeline:"]
        timeline.append(f"Current time: {current_time:.2f}s")
        timeline.append("Active lines:")
        for end_time, y_pos, text in active_lines:
            position = y_pos // self.line_height - (self._calculate_first_line_position() // self.line_height)
            timeline.append(f"  Line {position}: '{text}' ends at {end_time:.2f}s")
        timeline.append(f"New line would end at: {new_line_end:.2f}s ('{new_line_text}')")
        self.logger.debug("\n".join(timeline))

    def as_ass_events(
        self,
        style: Style,
        next_screen_start: Optional[timedelta] = None,
        is_unified_screen: bool = False,
        previous_active_lines: List[Tuple[float, int, str]] = None,
    ) -> Tuple[List[Event], List[Tuple[float, int, str]]]:
        """Convert screen to ASS events. Returns (events, active_lines)."""
        events = []
        active_lines = previous_active_lines.copy() if previous_active_lines else []

        if active_lines:
            self.logger.debug("  Active lines from previous screen:")
            for end, pos, text in active_lines:
                self.logger.debug(f"    Line at y={pos}: '{text}' (ends {end:.2f}s)")

        if is_unified_screen:
            fade_in_start = self.start_ts - timedelta(seconds=self.TARGET_PRESHOW_TIME)
            self.logger.debug(f"  Unified screen fade in at {fade_in_start}")

            y_position = self._calculate_first_line_position()
            for line in self.lines:
                line_end = line.segment.end_time + self.POST_ROLL_TIME
                active_lines.append((line_end, y_position, line.segment.text))
                events.append(self._create_line_event(line, y_position, style, fade_in_start))
                y_position += self.line_height
        else:
            for i, line in enumerate(self.lines):
                fade_in_time = line.segment.start_time - self.TARGET_PRESHOW_TIME
                self.logger.debug(f"  Processing line {i+1}:")
                self.logger.debug(f"    Text: '{line.segment.text}'")
                self.logger.debug(f"    Target timing: {fade_in_time:.2f}s -> {line.segment.start_time:.2f}s")

                while True:
                    if i == 0 and previous_active_lines:
                        top_lines = sorted([(end, pos, text) for end, pos, text in active_lines], key=lambda x: x[1])[:2]
                        if top_lines:
                            latest_clear_time = max(
                                end + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000) for end, _, _ in top_lines
                            )
                            if latest_clear_time > fade_in_time:
                                fade_in_time = latest_clear_time
                                self.logger.debug(f"    Waiting for top positions to clear until {fade_in_time:.2f}s")
                                continue

                    # Remove expired lines and get available positions
                    active_lines = [
                        (end, pos, text)
                        for end, pos, text in active_lines
                        if (end + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)) > fade_in_time
                    ]

                    if len(active_lines) < self.MAX_VISIBLE_LINES:
                        break

                    # Wait for next line to expire
                    if active_lines:
                        active_lines.sort()
                        next_available = active_lines[0][0] + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)
                        fade_in_time = next_available

                y_position = self._calculate_line_position(active_lines, fade_in_time)
                self.logger.debug(f"    Final position: y={y_position}, fade in at {fade_in_time:.2f}s")

                line_end = line.segment.end_time + self.POST_ROLL_TIME
                active_lines.append((line_end, y_position, line.segment.text))
                events.append(self._create_line_event(line, y_position, style, timedelta(seconds=fade_in_time)))

        return events, active_lines

    def _create_line_event(self, line: LyricsLine, y_position: int, style: Style, screen_fade_in_start: Optional[timedelta]) -> Event:
        """Create ASS event for a single line, handling screen transitions."""
        if screen_fade_in_start is not None:
            start_time = screen_fade_in_start
            end_time = timedelta(seconds=line.segment.end_time + self.POST_ROLL_TIME)
        else:
            start_time = timedelta(seconds=max(0, line.segment.start_time - self.PRE_ROLL_TIME))
            end_time = timedelta(seconds=line.segment.end_time + self.POST_ROLL_TIME)

        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = start_time.total_seconds()
        e.End = end_time.total_seconds()

        # Instead of using MarginV, use absolute positioning
        x_pos = self.video_size[0] // 2  # Center horizontally
        text = f"{{\\an8}}{{\\pos({x_pos},{y_position})}}{line._create_ass_text(start_time)}"
        e.Text = text

        # self.logger.debug(f"Created ASS event: {e.Text}")
        return e

    def _calculate_first_line_position(self) -> int:
        """Calculate vertical position of first line."""
        total_height = len(self.lines) * self.line_height
        top_padding = self.line_height  # Add one line height of padding at the top
        return top_padding + (self.video_size[1] - total_height - top_padding) // 4

    def _calculate_line_position(self, active_lines: List[Tuple[float, int, str]], current_time: float) -> int:
        """Calculate vertical position for a new line based on current active lines."""
        base_position = self._calculate_first_line_position()
        line_positions = [
            base_position,
            base_position + self.line_height,
            base_position + (2 * self.line_height),
            base_position + (3 * self.line_height),
        ]

        # Sort active lines by their vertical position
        active_lines_sorted = sorted(
            [(end, pos, text) for end, pos, text in active_lines if (end + (self.FADE_OUT_MS / 1000)) > current_time],
            key=lambda x: x[1],  # Sort by position
        )

        # Check if first two positions are still in use (including fade out and buffer)
        buffer_time = 0.3  # 300ms additional buffer
        positions_in_use = {}  # Changed to dict to track when positions become free

        for end, pos, text in active_lines_sorted:
            clear_time = end + (self.FADE_OUT_MS / 1000) + buffer_time
            if clear_time > current_time:
                positions_in_use[pos] = (text, end, clear_time)

        self.logger.debug(f"    Position status at {current_time:.2f}s:")
        for pos in line_positions:
            if pos in positions_in_use:
                text, end, clear = positions_in_use[pos]
                self.logger.debug(f"      Position {pos}: occupied by '{text}' until {clear:.2f}s (ends {end:.2f}s + fade + buffer)")
            else:
                self.logger.debug(f"      Position {pos}: available")

        # Find first available position from top
        for position in line_positions:
            if position not in positions_in_use:
                self.logger.debug(f"    Selected position {position} (first available from top)")
                return position

        # If all positions are in use, log details and use last position
        self.logger.debug("    All positions in use, using last position as fallback")
        return line_positions[-1]

    def __str__(self):
        return "\n".join([f"{self.start_ts} - {self.end_ts}:", *[f"\t{line}" for line in self.lines]])
