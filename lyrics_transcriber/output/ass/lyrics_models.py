import logging
import copy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import timedelta

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.style import Style


@dataclass
class LyricsLine:
    segments: List[LyricsSegment] = field(default_factory=list)
    logger: Optional[logging.Logger] = None
    PRE_ROLL_TIME = 2.0  # Seconds to show lines before first word
    FADE_IN_MS = 300  # Milliseconds to fade in
    FADE_OUT_MS = 300  # Milliseconds to fade out

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def ts(self) -> Optional[float]:
        """Get earliest timestamp from all words."""
        if not self.segments:
            self.logger.debug("No segments in line when getting ts")
            return None

        earliest_time = float("inf")
        for segment in self.segments:
            if segment.words:  # Check if segment has words
                for word in segment.words:
                    if word.start_time < earliest_time:
                        earliest_time = word.start_time

        return earliest_time if earliest_time != float("inf") else None

    @property
    def end_ts(self) -> Optional[float]:
        """Get latest timestamp from all words."""
        if not self.segments:
            self.logger.debug("No segments in line when getting end_ts")
            return None

        latest_time = 0
        for segment in self.segments:
            if segment.words:  # Check if segment has words
                for word in segment.words:
                    if word.end_time and word.end_time > latest_time:
                        latest_time = word.end_time

        return latest_time if latest_time > 0 else None

    @ts.setter
    def ts(self, value):
        self.segments[0].start_time = value

    @end_ts.setter
    def end_ts(self, value):
        self.segments[-1].end_time = value

    def __str__(self):
        return "".join([f"{{{s.text}}}" for s in self.segments])

    def as_ass_event(self, screen_start: timedelta, screen_end: timedelta, style: Style, y_position: int):
        """Create ASS event with proper timing."""
        self.logger.debug(f"Creating ASS event for line: {self}")

        # Start showing line PRE_ROLL_TIME seconds before first word
        start_time = timedelta(seconds=max(0, self.ts - self.PRE_ROLL_TIME))
        end_time = timedelta(seconds=self.end_ts)

        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = start_time.total_seconds()
        e.End = end_time.total_seconds()
        e.MarginV = y_position

        # Add fade effect before the alignment and karaoke tags
        e.Text = rf"{{\fad({self.FADE_IN_MS},{self.FADE_OUT_MS})}}{{\an8}}" + self.decorate_ass_line(self.segments, start_time)

        self.logger.debug(f"Created ASS event: {e.Text}")
        return e

    def decorate_ass_line(self, segments, start_ts: timedelta):
        """Create ASS line with word-level karaoke timing."""
        self.logger.debug(f"Decorating ASS line with {len(segments)} segments")

        first_word_time = self.ts
        start_time = max(0, (first_word_time - start_ts.total_seconds()) * 100)
        line = rf"{{\k{int(start_time)}}}"

        prev_end_time = first_word_time

        for segment in segments:
            # Split segment text to get actual word count
            expected_words = [w for w in segment.text.split() if w.strip()]
            self.logger.debug(f"Processing segment with {len(segment.words)} words (expected {len(expected_words)}): {segment.text}")

            if not segment.words:
                continue

            for i, word in enumerate(segment.words):
                # Add gap between words if needed
                gap = word.start_time - prev_end_time
                if gap > 0.1:
                    line += rf"{{\k{int(gap * 100)}}}"

                # Add the word with its duration
                duration = (word.end_time - word.start_time) * 100
                word_text = word.text.rstrip()
                line += rf"{{\kf{int(duration)}}}{word_text} "  # Always add space after word

                prev_end_time = word.end_time
                self.logger.debug(f"Added word: '{word_text}' with duration {duration}")

        # Remove trailing space
        line = line.rstrip()
        self.logger.debug(f"Final decorated line: {line}")
        return line

    def adjust_timestamps(self, offset: timedelta) -> "LyricsLine":
        """Adjust all timestamps by the given offset."""
        new_line = copy.deepcopy(self)
        offset_seconds = offset.total_seconds()

        for segment in new_line.segments:
            # Adjust segment times
            segment.start_time += offset_seconds
            if segment.end_time is not None:
                segment.end_time += offset_seconds

            # Adjust word times
            for word in segment.words:
                word.start_time += offset_seconds
                if word.end_time is not None:
                    word.end_time += offset_seconds

        return new_line

    def to_dict(self) -> dict:
        return {"segments": [segment.to_dict() for segment in self.segments]}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricsLine":
        segments = [LyricsSegment.from_dict(segment_data) for segment_data in data["segments"]]
        return cls(segments=segments)


@dataclass
class LyricsScreen:
    """Represents a screen of lyrics (multiple lines)."""

    video_size: Tuple[int, int]
    line_height: int
    lines: List[LyricsLine] = field(default_factory=list)
    _start_ts: timedelta = field(default=timedelta(0))
    _end_ts: timedelta = field(default=timedelta(0))
    logger: Optional[logging.Logger] = None
    PRE_ROLL_TIME = 5.0  # Seconds to show screen before first word

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def start_ts(self) -> timedelta:
        """Get screen start timestamp."""
        # Start showing screen PRE_ROLL_TIME seconds before first word
        earliest_ts = min(line.ts for line in self.lines)
        return timedelta(seconds=max(0, earliest_ts - self.PRE_ROLL_TIME))

    @start_ts.setter
    def start_ts(self, value: timedelta):
        """Set screen start timestamp."""
        self._start_ts = value

    @property
    def end_ts(self) -> timedelta:
        """Get screen end timestamp."""
        return timedelta(seconds=max(line.end_ts for line in self.lines))

    @end_ts.setter
    def end_ts(self, value: timedelta):
        """Set screen end timestamp."""
        self._end_ts = value

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
        return (self.video_size[1] - total_height) // 4  # Position in top quarter

    def get_line_y(self, line_num: int) -> int:
        _, h = self.video_size
        line_count = len(self.lines)
        total_height = line_count * self.line_height
        top_margin = (h - total_height) / 2
        line_y = top_margin + (line_num * self.line_height)

        self.logger.debug(f"Calculated y position for line {line_num}: {line_y}")
        self.logger.debug(f"Video height: {h}, Lines: {line_count}, Line height: {self.line_height}")

        return int(line_y)

    def __str__(self):
        lines = [f"{self.start_ts} - {self.end_ts}:"]
        for line in self.lines:
            lines.append(f"\t{line}")
        return "\n".join(lines)

    def adjust_timestamps(self, adjustment: timedelta) -> "LyricsScreen":
        new_lines = [l.adjust_timestamps(adjustment) for l in self.lines]
        start_ts = self.start_ts + adjustment if self.start_ts else None
        return LyricsScreen(new_lines, start_ts)

    def to_dict(self) -> dict:
        return {"lines": [line.to_dict() for line in self.lines], "start_ts": self.start_ts.total_seconds() if self.start_ts else None}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricsScreen":
        lines = [LyricsLine.from_dict(line_data) for line_data in data["lines"]]
        start_ts = timedelta(seconds=float(data["start_ts"])) if data["start_ts"] is not None else None
        return cls(lines=lines, start_ts=start_ts)
