from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging
from datetime import timedelta

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.event import Event


@dataclass
class LyricsLine:
    """Represents a single line of lyrics with timing and display information."""

    segment: LyricsSegment
    logger: Optional[logging.Logger] = None
    PRE_ROLL_TIME = 2.0
    POST_ROLL_TIME = 2.0
    FADE_IN_MS = 300
    FADE_OUT_MS = 300

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def as_ass_event(self, screen_start: timedelta, screen_end: timedelta, style: Style, y_position: int) -> Event:
        """Create ASS event with proper timing."""
        self.logger.debug(f"Creating ASS event for line: {self}")

        # Calculate line timing with pre-roll and post-roll
        line_start = timedelta(seconds=max(0, self.segment.start_time - self.PRE_ROLL_TIME))
        line_end = timedelta(seconds=self.segment.end_time + self.POST_ROLL_TIME)  # Add post-roll delay

        # Ensure line timing stays within screen bounds
        start_time = max(line_start, screen_start)
        end_time = min(line_end, screen_end)

        self.logger.debug(f"Line timing: {start_time} -> {end_time} (screen: {screen_start} -> {screen_end})")

        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = start_time.total_seconds()
        e.End = end_time.total_seconds()
        e.MarginV = y_position

        e.Text = self._create_ass_text(start_time)
        self.logger.debug(f"Created ASS event: {e.Text}")
        return e

    def _create_ass_text(self, start_ts: timedelta) -> str:
        """Create the ASS text with all formatting tags."""
        return f"{self._fade_tag()}" f"{self._alignment_tag()}" f"{self._create_karaoke_text(start_ts)}"

    def _fade_tag(self) -> str:
        """Create fade effect tag."""
        return rf"{{\fad({self.FADE_IN_MS},{self.FADE_OUT_MS})}}"

    def _alignment_tag(self) -> str:
        """Create alignment tag."""
        return r"{\an8}"

    def _create_karaoke_text(self, start_ts: timedelta) -> str:
        """Create karaoke-timed text with word highlighting."""
        self.logger.debug(f"Creating karaoke text for {len(self.segment.words)} words")

        # Initial delay before first word
        first_word_time = self.segment.start_time
        start_time = max(0, (first_word_time - start_ts.total_seconds()) * 100)
        text = rf"{{\k{int(start_time)}}}"

        prev_end_time = first_word_time

        for word in self.segment.words:
            # Add gap between words if needed
            gap = word.start_time - prev_end_time
            if gap > 0.1:
                text += rf"{{\k{int(gap * 100)}}}"

            # Add the word with its duration
            duration = (word.end_time - word.start_time) * 100
            text += rf"{{\kf{int(duration)}}}{word.text} "

            prev_end_time = word.end_time
            self.logger.debug(f"Added word: '{word.text}' with duration {duration}")

        return text.rstrip()

    def __str__(self):
        return f"{{{self.segment.text}}}"


@dataclass
class LyricsScreen:
    """Represents a screen of lyrics (multiple lines)."""

    video_size: Tuple[int, int]
    line_height: int
    lines: List[LyricsLine] = field(default_factory=list)
    logger: Optional[logging.Logger] = None
    PRE_ROLL_TIME = 5.0

    def __post_init__(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def start_ts(self) -> timedelta:
        """Get screen start timestamp."""
        earliest_ts = min(line.segment.start_time for line in self.lines)
        return timedelta(seconds=max(0, earliest_ts - self.PRE_ROLL_TIME))

    @property
    def end_ts(self) -> timedelta:
        """Get screen end timestamp."""
        return timedelta(seconds=max(line.segment.end_time for line in self.lines))

    def as_ass_events(self, style: Style) -> List[Event]:
        """Convert screen to ASS events."""
        events = []
        y_position = self._calculate_first_line_position()

        for line in self.lines:
            events.append(line.as_ass_event(self.start_ts, self.end_ts, style, y_position))
            y_position += self.line_height

        return events

    def _calculate_first_line_position(self) -> int:
        """Calculate vertical position of first line."""
        total_height = len(self.lines) * self.line_height
        return (self.video_size[1] - total_height) // 4

    def __str__(self):
        return "\n".join([f"{self.start_ts} - {self.end_ts}:", *[f"\t{line}" for line in self.lines]])
