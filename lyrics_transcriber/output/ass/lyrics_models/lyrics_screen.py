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
    post_instrumental: bool = False
    MAX_VISIBLE_LINES = 4
    SCREEN_GAP_THRESHOLD = 5.0
    POST_ROLL_TIME = 1.0
    FADE_IN_MS = 100
    FADE_OUT_MS = 400
    CASCADE_DELAY_MS = 200
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
        previous_active_lines: List[Tuple[float, int, str]] = None,
    ) -> Tuple[List[Event], List[Tuple[float, int, str]]]:
        """Convert screen to ASS events. Returns (events, active_lines)."""
        events = []
        active_lines = previous_active_lines.copy() if previous_active_lines else []

        # Filter to only show lines that are still active
        current_time = self.lines[0].segment.start_time - self.TARGET_PRESHOW_TIME
        active_previous_lines = [(end, pos, text) for end, pos, text in active_lines if end + (self.FADE_OUT_MS / 1000) > current_time]

        if active_previous_lines:
            self.logger.debug("  Active lines from previous screen:")
            for end, pos, text in active_previous_lines:
                clear_time = end + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)
                self.logger.debug(
                    f"    Line at y={pos}: '{text}' (ends {end:.2f}s, fade out {end + (self.FADE_OUT_MS / 1000):.2f}s, clear {clear_time:.2f}s)"
                )

        # Use unified screen behavior for post-instrumental screens
        if self.post_instrumental:
            fade_in_start = self.start_ts - timedelta(seconds=self.TARGET_PRESHOW_TIME)
            self.logger.debug(f"  Post-instrumental screen fade in at {fade_in_start}")

            y_position = self._calculate_first_line_position()
            for line in self.lines:
                line_end = line.segment.end_time + self.POST_ROLL_TIME
                active_lines.append((line_end, y_position, line.segment.text))
                events.append(self._create_line_event(line, y_position, style, fade_in_start))
                y_position += self.line_height
        else:
            # Calculate when first line should appear
            first_line = self.lines[0]
            first_line_fade_in = first_line.segment.start_time - self.TARGET_PRESHOW_TIME

            # For first line of new screen, wait for top positions to clear if needed
            if previous_active_lines:
                top_lines = sorted([(end, pos, text) for end, pos, text in active_lines], key=lambda x: x[1])[:2]
                if top_lines:
                    latest_clear_time = max(
                        end + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000) for end, _, _ in top_lines
                    )
                    first_line_fade_in = max(first_line_fade_in, latest_clear_time)

            # Calculate when line 2 can appear (after previous screen's line 2 fades out)
            second_line_fade_in = first_line_fade_in + (self.CASCADE_DELAY_MS / 1000)  # Default: 100ms after line 1
            if previous_active_lines:
                line2_y_pos = self._calculate_first_line_position() + self.line_height
                line2_positions = [(end, pos, text) for end, pos, text in active_previous_lines if pos == line2_y_pos]
                if line2_positions:
                    prev_line2 = line2_positions[0]
                    line2_clear_time = prev_line2[0] + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)
                    second_line_fade_in = max(second_line_fade_in, line2_clear_time)
                    self.logger.debug(
                        f"    Previous line 2 '{prev_line2[2]}' ends {prev_line2[0]:.2f}s, fade out {prev_line2[0] + (self.FADE_OUT_MS / 1000):.2f}s, clears {line2_clear_time:.2f}s"
                    )

            # Calculate when lines 3+ can appear (after previous screen's last line fades out)
            if previous_active_lines:
                last_line = max(active_lines, key=lambda x: x[0])
                last_line_clear_time = last_line[0] + (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)
                third_line_fade_in = last_line_clear_time
                fourth_line_fade_in = third_line_fade_in + (self.CASCADE_DELAY_MS / 1000)
            else:
                third_line_fade_in = second_line_fade_in + (self.CASCADE_DELAY_MS / 1000)
                fourth_line_fade_in = third_line_fade_in + (self.CASCADE_DELAY_MS / 1000)

            # Log the screen timing strategy
            self.logger.debug(f"  Screen timing strategy:")
            self.logger.debug(f"    First line '{first_line.segment.text}' starts at {first_line.segment.start_time:.2f}s")
            self.logger.debug(f"    Fading in first line at {first_line_fade_in:.2f}s")
            if len(self.lines) > 1:
                self.logger.debug(f"    Fading in second line at {second_line_fade_in:.2f}s")
                if len(self.lines) > 2:
                    if previous_active_lines:
                        self.logger.debug(
                            f"    Previous screen last line '{last_line[2]}' ends {last_line[0]:.2f}s, clears {last_line_clear_time:.2f}s"
                        )
                    self.logger.debug(f"    Fading in third line at {third_line_fade_in:.2f}s")
                    if len(self.lines) > 3:
                        self.logger.debug(f"    Fading in fourth line at {fourth_line_fade_in:.2f}s")

            # Process lines with consistent cascade timing
            y_position = self._calculate_first_line_position()
            for i, line in enumerate(self.lines):
                if i == 0:
                    fade_in_time = first_line_fade_in
                elif i == 1:
                    fade_in_time = second_line_fade_in
                elif i == 2:
                    fade_in_time = third_line_fade_in
                else:
                    fade_in_time = fourth_line_fade_in

                self.logger.debug(f"    Placing '{line.segment.text}' at position {y_position}")
                line_end = line.segment.end_time + self.POST_ROLL_TIME
                active_lines.append((line_end, y_position, line.segment.text))
                events.append(self._create_line_event(line, y_position, style, timedelta(seconds=fade_in_time)))
                y_position += self.line_height

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

        # Track which positions are in use and when they'll be free
        buffer_time = (self.FADE_OUT_MS / 1000) + (self.POSITION_CLEAR_BUFFER_MS / 1000)
        positions_in_use = {}

        for end, pos, text in active_lines:
            clear_time = end + buffer_time
            if clear_time > current_time:
                positions_in_use[pos] = (text, end, clear_time)

        self.logger.debug(f"    Position status at {current_time:.2f}s:")
        for pos in line_positions:
            if pos in positions_in_use:
                text, end, clear = positions_in_use[pos]
                self.logger.debug(f"      Position {pos}: occupied by '{text}' until {clear:.2f}s (ends {end:.2f}s + fade + buffer)")
            else:
                self.logger.debug(f"      Position {pos}: available")

        # Find the next available position in sequence
        used_positions = set(positions_in_use.keys())
        for position in line_positions:
            if position not in used_positions:
                self.logger.debug(f"    Selected position {position} (next available in sequence)")
                return position

        # If all positions are in use, wait for the first one to clear
        earliest_clear_pos = min(line_positions, key=lambda pos: positions_in_use.get(pos, (None, None, float("inf")))[2])
        self.logger.debug(f"    All positions in use, waiting for {earliest_clear_pos} to clear")
        return earliest_clear_pos

    def __str__(self):
        return "\n".join([f"{self.start_ts} - {self.end_ts}:", *[f"\t{line}" for line in self.lines]])
