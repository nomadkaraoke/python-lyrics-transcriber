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
    POST_ROLL_TIME = 2.0
    FADE_IN_MS = 300
    FADE_OUT_MS = 300
    TARGET_PRESHOW_TIME = 5.0

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
        y_position = self._calculate_first_line_position()

        # Initialize active_lines with any still-visible lines from previous screens
        active_lines = previous_active_lines.copy() if previous_active_lines else []
        self.logger.debug(f"Starting with {len(active_lines)} previous active lines:")
        for end, pos, text in active_lines:
            self.logger.debug(f"  - '{text}' ends at {end:.2f}s")

        if is_unified_screen:
            screen_fade_in_start = self.start_ts - timedelta(seconds=self.TARGET_PRESHOW_TIME)
            self.logger.debug(f"Unified screen fade in at {screen_fade_in_start} (all lines together)")

            for line in self.lines:
                line_end = line.segment.end_time + self.POST_ROLL_TIME + (self.FADE_OUT_MS / 1000)
                self.logger.debug(f"Adding unified line: '{line.segment.text}' ending at {line_end:.2f}s")
                active_lines.append((line_end, y_position, line.segment.text))
                events.append(
                    self._create_line_event(line=line, y_position=y_position, style=style, screen_fade_in_start=screen_fade_in_start)
                )
                y_position += self.line_height

            self.logger.debug(f"After unified screen, active lines: {[(end, text) for end, _, text in active_lines]}")
        else:
            for i, line in enumerate(self.lines):
                line_end = line.segment.end_time + self.POST_ROLL_TIME
                fade_out_end = line_end + (self.FADE_OUT_MS / 1000)  # Include fade out time
                target_start = line.segment.start_time - self.TARGET_PRESHOW_TIME

                self.logger.debug(f"Processing line {i+1}: '{line.segment.text}'")
                self.logger.debug(f"Target start: {target_start:.2f}s, Must show by: {line.segment.start_time:.2f}s")

                # Start with target time
                fade_in_time = target_start

                while True:
                    # Remove only fully expired lines (including fade out time)
                    prev_active_count = len(active_lines)
                    current_time = fade_in_time
                    active_lines = [
                        (end, pos, text) for end, pos, text in active_lines 
                        if (end + (self.FADE_OUT_MS / 1000)) > current_time
                    ]
                    if prev_active_count != len(active_lines):
                        self.logger.debug(f"Removed {prev_active_count - len(active_lines)} expired lines at {fade_in_time:.2f}s")

                    self._visualize_timeline(active_lines, fade_in_time, fade_out_end, line.segment.text)

                    if len(active_lines) < self.MAX_VISIBLE_LINES:
                        self.logger.debug(f"Found space for line at {fade_in_time:.2f}s ({len(active_lines)} active lines)")
                        break

                    # No room yet, wait until next line fully expires (including fade out)
                    if active_lines:
                        prev_time = fade_in_time
                        active_lines.sort()  # Sort by end time
                        next_available = active_lines[0][0] + (self.FADE_OUT_MS / 1000)
                        fade_in_time = next_available
                        self.logger.debug(f"No space available at {prev_time:.2f}s, waiting until {fade_in_time:.2f}s")

                    # Safety check: ensure we don't delay past when line needs to be shown
                    if fade_in_time > line.segment.start_time:
                        self.logger.error(
                            f"Cannot find space for line before it needs to be shown! Required: {line.segment.start_time:.2f}s"
                        )
                        break

                # Calculate y_position based on current active lines
                y_position = self._calculate_line_position(active_lines, fade_in_time)
                
                # Add this line to active lines
                active_lines.append((line_end, y_position, line.segment.text))
                active_lines.sort()  # Sort by end time

                self.logger.debug(f"Final decision: fade in at {fade_in_time:.2f}s with {len(active_lines)} active lines")

                events.append(
                    self._create_line_event(
                        line=line,
                        y_position=y_position,
                        style=style,
                        screen_fade_in_start=timedelta(seconds=fade_in_time)
                    )
                )

        return events, active_lines

    def _create_line_event(self, line: LyricsLine, y_position: int, style: Style, screen_fade_in_start: Optional[timedelta]) -> Event:
        """Create ASS event for a single line, handling screen transitions."""
        if screen_fade_in_start is not None:
            # During screen transitions, all lines appear at once
            start_time = screen_fade_in_start
            end_time = timedelta(seconds=line.segment.end_time + self.POST_ROLL_TIME)
        else:
            # Normal line timing with individual pre-roll
            start_time = timedelta(seconds=max(0, line.segment.start_time - self.PRE_ROLL_TIME))
            end_time = timedelta(seconds=line.segment.end_time + self.POST_ROLL_TIME)

        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = start_time.total_seconds()
        e.End = end_time.total_seconds()
        e.MarginV = y_position

        e.Text = line._create_ass_text(start_time)
        self.logger.debug(f"Created ASS event: {e.Text}")
        return e

    def _calculate_first_line_position(self) -> int:
        """Calculate vertical position of first line."""
        total_height = len(self.lines) * self.line_height
        top_padding = self.line_height  # Add one line height of padding at the top
        return top_padding + (self.video_size[1] - total_height - top_padding) // 4

    def _calculate_line_position(self, active_lines: List[Tuple[float, int, str]], current_time: float) -> int:
        """Calculate vertical position for a new line based on current active lines."""
        base_position = self._calculate_first_line_position()
        
        # Consider a position occupied until the line has completely faded out
        used_positions = set(
            pos for end, pos, _ in active_lines 
            if (end + (self.FADE_OUT_MS / 1000)) > current_time
        )
        
        # Find the first available position from top to bottom
        for i in range(self.MAX_VISIBLE_LINES):
            candidate_position = base_position + (i * self.line_height)
            if candidate_position not in used_positions:
                return candidate_position
                
        # If no slots are available, use the last position as fallback
        return base_position + ((self.MAX_VISIBLE_LINES - 1) * self.line_height)

    def __str__(self):
        return "\n".join([f"{self.start_ts} - {self.end_ts}:", *[f"\t{line}" for line in self.lines]])
