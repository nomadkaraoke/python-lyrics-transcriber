from dataclasses import dataclass
from typing import Optional
import logging
from datetime import timedelta

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.config import LineState


@dataclass
class LyricsLine:
    """Represents a single line of lyrics with timing and karaoke information."""

    segment: LyricsSegment
    logger: Optional[logging.Logger] = None

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def create_ass_event(self, state: LineState, style: Style, video_width: int, config) -> Event:
        """Create ASS event for this line."""
        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = state.timing.fade_in_time
        e.End = state.timing.end_time

        # Use absolute positioning
        x_pos = video_width // 2  # Center horizontally

        # Add fade effect using config values
        fade_in_ms = config.fade_in_ms
        fade_out_ms = config.fade_out_ms

        # fmt: off
        text = (
            f"{{\\an8}}{{\\pos({x_pos},{state.y_position})}}"
            f"{{\\fad({fade_in_ms},{fade_out_ms})}}"
            f"{self._create_ass_text(timedelta(seconds=state.timing.fade_in_time))}"
        )
        # fmt: on
        e.Text = text

        return e

    def _create_ass_text(self, start_ts: timedelta) -> str:
        """Create the ASS text with karaoke timing tags."""
        # Initial delay before first word
        first_word_time = self.segment.start_time
        start_time = max(0, (first_word_time - start_ts.total_seconds()) * 100)
        text = r"{\k" + str(int(round(start_time))) + r"}"

        prev_end_time = first_word_time

        for word in self.segment.words:
            # Add gap between words if needed
            gap = word.start_time - prev_end_time
            if gap > 0.1:  # Only add gap if significant
                text += r"{\k" + str(int(round(gap * 100))) + r"}"

            # Add the word with its duration
            duration = int(round((word.end_time - word.start_time) * 100))
            text += r"{\kf" + str(duration) + r"}" + word.text + " "

            prev_end_time = word.end_time  # Track the actual end time of the word

        return text.rstrip()

    def __str__(self):
        return f"{{{self.segment.text}}}"
