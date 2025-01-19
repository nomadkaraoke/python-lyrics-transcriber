from dataclasses import dataclass
from typing import Optional, Tuple, List
import logging
from datetime import timedelta

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.config import LineState, ScreenConfig


@dataclass
class LyricsLine:
    """Represents a single line of lyrics with timing and karaoke information."""

    segment: LyricsSegment
    logger: Optional[logging.Logger] = None
    previous_end_time: Optional[float] = None

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    # fmt: off
    def _create_lead_in_text(self, state: LineState) -> Tuple[str, bool]:
        """Create lead-in indicator text if needed.
        
        Returns:
            Tuple of (text, has_lead_in)
        """
        has_lead_in = (self.previous_end_time is None or 
                      self.segment.start_time - self.previous_end_time >= 5.0)
        
        if not has_lead_in:
            return "", False
            
        # Add a hyphen with karaoke timing for the last 2 seconds before the line
        lead_in_start = max(state.timing.fade_in_time, self.segment.start_time - 2.0)
        gap_before_highlight = int((lead_in_start - state.timing.fade_in_time) * 100)
        highlight_duration = int((self.segment.start_time - lead_in_start) * 100)
        
        text = ""
        # Add initial gap if needed
        if gap_before_highlight > 0:
            text += f"{{\\k{gap_before_highlight}}}"
        # Add the hyphen with highlight
        text += f"{{\\kf{highlight_duration}}}→ "
        
        return text, True

    def _create_lead_in_event(self, state: LineState, style: Style, video_width: int, config) -> Optional[Event]:
        """Create a separate event for the lead-in indicator if needed."""
        if not (self.previous_end_time is None or 
                self.segment.start_time - self.previous_end_time >= 5.0):
            return None
            
        e = Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        
        # Calculate timing for the 2-second highlight
        lead_in_start = max(state.timing.fade_in_time, self.segment.start_time - 2.0)
        
        # Start slightly before the highlight to allow for fade in
        e.Start = lead_in_start - 0.2  # 200ms before highlight starts
        # End after the highlight plus fade out duration
        e.End = self.segment.start_time + 0.4  # 400ms fade out after highlight
        
        # Calculate position: 15% from left, and vertically offset by line_height/6
        x_pos = video_width * 0.15
        y_pos = state.y_position - (config.line_height // 6)
        
        gap_before_highlight = 20  # 200ms for fade in
        highlight_duration = int((self.segment.start_time - lead_in_start) * 100)
        
        # Create text with absolute positioning and fade
        # Fade in quickly before highlight, fade out after highlight is complete
        text = (
            f"{{\\an8}}{{\\pos({x_pos},{y_pos})}}"
            f"{{\\fad(200,400)}}"  # 200ms fade in, 400ms fade out
            f"{{\\t({(self.segment.start_time - e.Start)*1000},{(self.segment.start_time - e.Start)*1000 + 1000},\\alpha&HFF&)}}"  # Start fade out at line start
        )
        
        # Add timing for fade-in period
        text += f"{{\\k{gap_before_highlight}}}"
            
        # Add the indicator with karaoke fade
        text += f"{{\\kf{highlight_duration}}}⟶"
        
        e.Text = text
        return e

    def create_ass_events(
        self, 
        state: LineState, 
        style: Style, 
        video_width: int, 
        config: ScreenConfig,
        previous_end_time: Optional[float] = None
    ) -> List[Event]:
        """Create ASS events for this line. Returns [main_event] or [lead_in_event, main_event]."""
        self.previous_end_time = previous_end_time
        events = []
        
        # Create lead-in event if needed
        lead_in_event = self._create_lead_in_event(state, style, video_width, config)
        if lead_in_event:
            events.append(lead_in_event)
        
        # Create main lyrics event
        main_event = Event()
        main_event.type = "Dialogue"
        main_event.Layer = 0
        main_event.Style = style
        main_event.Start = state.timing.fade_in_time
        main_event.End = state.timing.end_time

        # Use absolute positioning
        x_pos = video_width // 2  # Center horizontally

        # Main lyrics text with positioning and fade
        text = (
            f"{{\\an8}}{{\\pos({x_pos},{state.y_position})}}"
            f"{{\\fad({config.fade_in_ms},{config.fade_out_ms})}}"
        )

        # Add the main lyrics text with karaoke timing
        text += self._create_ass_text(timedelta(seconds=state.timing.fade_in_time))

        main_event.Text = text
        events.append(main_event)

        return events

    def _create_ass_text(self, start_ts: timedelta) -> str:
        """Create the ASS text with karaoke timing tags."""
        # Initial delay before first word
        first_word_time = self.segment.start_time
        
        # Add initial delay for regular lines
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
