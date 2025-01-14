from dataclasses import dataclass
from typing import List, Optional, Literal, Tuple
import logging
from datetime import timedelta

from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.event import Event
from .lyrics_screen import LyricsScreen
from .lyrics_line import LyricsLine


class SectionScreen(LyricsScreen):
    """Special screen for instrumental sections."""

    def __init__(
        self,
        section_type: Literal["INTRO", "OUTRO", "INSTRUMENTAL"],
        start_time: float,
        end_time: float,
        video_size: Tuple[int, int],
        line_height: int,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(video_size=video_size, line_height=line_height, logger=logger)
        self.section_type = section_type
        
        # Adjust timing for intro sections
        if section_type == "INTRO":
            self.start_time = 1.0  # Start after 1 second
            self.end_time = end_time - 5.0  # End 5 seconds before next section
        else:
            self.start_time = start_time
            self.end_time = end_time
            
        # Calculate duration in seconds
        duration_secs = int(self.end_time - self.start_time)
        
        # Create a synthetic segment for the instrumental marker
        text = f"INSTRUMENTAL - {duration_secs} seconds"
        word = Word(
            text=text,
            start_time=self.start_time,
            end_time=self.end_time,
            confidence=1.0
        )
        segment = LyricsSegment(
            text=text,
            start_time=self.start_time,
            end_time=self.end_time,
            words=[word]
        )
        self.lines = [LyricsLine(segment=segment, logger=self.logger)]

    def as_ass_events(
        self,
        style: Style,
        next_screen_start: Optional[timedelta],
        is_unified: bool,
        active_lines: List[Tuple[float, int, str]] = None,
    ) -> Tuple[List[Event], List[Tuple[float, int, str]]]:
        """Create ASS events for instrumental markers with karaoke highlighting."""
        self.logger.debug(f"Creating instrumental marker event for {self.section_type}")
        
        event = Event()
        event.type = "Dialogue"
        event.Layer = 0
        event.Style = style
        event.Start = self.start_time
        event.End = self.end_time
        
        # Calculate vertical position (centered on screen)
        y_position = (self.video_size[1] - self.line_height) // 2
        event.MarginV = y_position
        
        # Add karaoke timing for the entire duration
        duration = int((self.end_time - self.start_time) * 100)  # Convert to centiseconds
        event.Text = f"{{\\fad(300,300)}}{{\\an8}}{{\\K{duration}}}{self.lines[0].segment.text}"
        
        self.logger.debug(f"Created instrumental event: {event.Text} ({event.Start}s - {event.End}s)")
        return [event], []  # No active lines to track for sections

    @property
    def start_ts(self) -> timedelta:
        """Get start timestamp."""
        return timedelta(seconds=self.start_time)

    @property
    def end_ts(self) -> timedelta:
        """Get end timestamp."""
        return timedelta(seconds=self.end_time)
