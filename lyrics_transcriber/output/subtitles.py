import logging
import os
from typing import List, Optional, Tuple
from datetime import timedelta
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional, Tuple
import json
import itertools
import logging
import copy

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.constants import ALIGN_TOP_CENTER


class LyricSegmentIterator:
    def __init__(self, lyrics_segments: List[str]):
        self._segments = lyrics_segments
        self._current_segment = 0  # Initialize to 0 instead of None

    def __iter__(self):
        self._current_segment = 0
        return self

    def __next__(self):
        if self._current_segment >= len(self._segments):
            raise StopIteration
        val = self._segments[self._current_segment]
        self._current_segment += 1
        return val

    def __len__(self):
        return len(self._segments)


@dataclass
class LyricsLine:
    segments: List[LyricsSegment] = field(default_factory=list)
    logger: Optional[logging.Logger] = None
    PRE_ROLL_TIME = 5.0  # Seconds to show lines before first word

    def __post_init__(self):
        """Ensure logger is initialized"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @property
    def ts(self) -> Optional[float]:
        """Get earliest timestamp from all words in all segments."""
        if not self.segments:
            self.logger.debug("No segments in line when getting ts")
            return None

        # Find earliest word start time across all segments
        earliest_time = float("inf")
        for segment in self.segments:
            if segment.words and segment.words[0].start_time < earliest_time:
                earliest_time = segment.words[0].start_time

        self.logger.debug(f"Getting ts from earliest word: {earliest_time}")
        return earliest_time

    @property
    def end_ts(self) -> Optional[float]:
        """Get latest timestamp from all words in all segments."""
        if not self.segments:
            self.logger.debug("No segments in line when getting end_ts")
            return None

        # Find latest word end time across all segments
        latest_time = 0
        for segment in self.segments:
            if segment.words:  # Check if segment has words
                for word in segment.words:
                    if word.end_time > latest_time:
                        latest_time = word.end_time

        self.logger.debug(f"Getting end_ts from latest word: {latest_time}")
        return latest_time

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
        e.Text = self.decorate_ass_line(self.segments, start_time)
        e.Text = "{\\an8}" + e.Text

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

    def adjust_timestamps(self, adjustment: timedelta) -> "LyricsLine":
        new_segments = []
        for s in self.segments:
            new_segment = copy.deepcopy(s)
            new_segment.start_time += adjustment.total_seconds()
            new_segment.end_time += adjustment.total_seconds()
            new_segments.append(new_segment)
        return LyricsLine(new_segments)

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


class LyricsObjectJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (LyricsSegment, LyricsLine, LyricsScreen)):
            return o.to_dict()
        return super().default(o)


class SubtitlesGenerator:
    """Handles generation of subtitle files in various formats."""

    def __init__(
        self,
        output_dir: str,
        video_resolution: Tuple[int, int],
        font_size: int,
        line_height: int,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize SubtitleGenerator.

        Args:
            output_dir: Directory where output files will be written
            video_resolution: Tuple of (width, height) for video resolution
            font_size: Font size for subtitles
            line_height: Line height for subtitle positioning
            logger: Optional logger instance
        """
        self.output_dir = output_dir
        self.video_resolution = video_resolution
        self.font_size = font_size
        self.line_height = line_height
        self.logger = logger or logging.getLogger(__name__)

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.output_dir, f"{output_prefix}.{extension}")

    def generate_ass(self, segments: List[LyricsSegment], output_prefix: str) -> str:
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "ass")

        try:
            self.logger.debug(f"Processing {len(segments)} segments")
            for i, segment in enumerate(segments):
                self.logger.debug(f"\nSegment {i}:")
                self.logger.debug(f"  Text: {segment.text}")
                self.logger.debug(f"  Timing: {segment.start_time:.3f}s - {segment.end_time:.3f}s")
                self.logger.debug(f"  Words ({len(segment.words)}):")
                for j, word in enumerate(segment.words):
                    self.logger.debug(f"    Word {j}: '{word.text}' ({word.start_time:.3f}s - {word.end_time:.3f}s)")
                    if word.confidence is not None:
                        self.logger.debug(f"      Confidence: {word.confidence:.3f}")

            initial_screens = self._create_screens(segments)
            self.logger.debug(f"Created {len(initial_screens)} initial screens")

            song_duration = int(segments[-1].end_time)
            self.logger.debug(f"Song duration: {song_duration} seconds")

            screens = self.set_segment_end_times(initial_screens, song_duration)
            self.logger.debug("Set segment end times")

            screens = self.set_screen_start_times(screens)
            self.logger.debug("Set screen start times")

            lyric_subtitles_ass = self.create_styled_subtitles(screens, self.video_resolution, self.font_size)
            self.logger.debug("Created styled subtitles")

            lyric_subtitles_ass.write(output_path)
            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}", exc_info=True)
            raise

    def _create_screens(self, segments: List[LyricsSegment]) -> List[LyricsScreen]:
        self.logger.debug("Creating screens from segments")
        screens: List[LyricsScreen] = []
        screen: Optional[LyricsScreen] = None

        max_lines_per_screen = 4

        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.text}")

            if screen is None or len(screen.lines) >= max_lines_per_screen:
                screen = LyricsScreen(video_size=self.video_resolution, line_height=self.line_height, logger=self.logger)
                screens.append(screen)
                self.logger.debug(f"Created new screen. Total screens: {len(screens)}")

            line = LyricsLine(logger=self.logger)
            line.segments.append(segment)
            screen.lines.append(line)
            self.logger.debug(f"Added line to screen: {line}")

        return screens

    def set_segment_end_times(self, screens: List[LyricsScreen], song_duration_seconds: int) -> List[LyricsScreen]:
        self.logger.debug("Setting segment end times")
        segments = list(itertools.chain.from_iterable([l.segments for s in screens for l in s.lines]))

        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.text}")
            if not segment.end_time:
                if i == len(segments) - 1:
                    self.logger.debug(f"Setting last segment end time to song duration: {song_duration_seconds}")
                    segment.end_time = song_duration_seconds
                else:
                    next_segment = segments[i + 1]
                    self.logger.debug(f"Setting segment end time to next segment start time: {next_segment.start_time}")
                    segment.end_time = next_segment.start_time

        return screens

    def set_screen_start_times(self, screens: List[LyricsScreen]) -> List[LyricsScreen]:
        """Set screen timings based on actual content."""
        self.logger.debug("Setting screen start times")

        for screen in screens:
            # Each screen's timing is based on its content
            screen.start_ts = timedelta(seconds=min(line.ts for line in screen.lines))
            screen.end_ts = timedelta(seconds=max(line.end_ts for line in screen.lines))

        return screens

    def create_styled_subtitles(
        self,
        lyric_screens: List[LyricsScreen],
        resolution,
        fontsize,
    ) -> ASS:
        a = ASS()
        a.set_resolution(resolution)

        a.styles_format = [
            "Name",  # The name of the Style. Case sensitive. Cannot include commas.
            "Fontname",  # The fontname as used by Windows. Case-sensitive.
            "Fontsize",  # Font size
            "PrimaryColour",  # This is the colour that a subtitle will normally appear in.
            "SecondaryColour",  # This colour may be used instead of the Primary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
            "OutlineColour",  # This colour may be used instead of the Primary or Secondary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
            "BackColour",  # This is the colour of the subtitle outline or shadow, if these are used
            "Bold",  # This defines whether text is bold (true) or not (false). -1 is True, 0 is False
            "Italic",  # This defines whether text is italic (true) or not (false). -1 is True, 0 is False
            "Underline",  # [-1 or 0]
            "StrikeOut",  # [-1 or 0]
            "ScaleX",  # Modifies the width of the font. [percent]
            "ScaleY",  # Modifies the height of the font. [percent]
            "Spacing",  # Extra space between characters. [pixels]
            "Angle",  # The origin of the rotation is defined by the alignment. Can be a floating point number. [degrees]
            "BorderStyle",  # 1=Outline + drop shadow, 3=Opaque box
            "Outline",  # If BorderStyle is 1,  then this specifies the width of the outline around the text, in pixels. Values may be 0, 1, 2, 3 or 4.
            "Shadow",  # If BorderStyle is 1,  then this specifies the depth of the drop shadow behind the text, in pixels. Values may be 0, 1, 2, 3 or 4. Drop shadow is always used in addition to an outline - SSA will force an outline of 1 pixel if no outline width is given.
            "Alignment",  # This sets how text is "justified" within the Left/Right onscreen margins, and also the vertical placing. Values may be 1=Left, 2=Centered, 3=Right. Add 4 to the value for a "Toptitle". Add 8 to the value for a "Midtitle". eg. 5 = left-justified toptitle
            "MarginL",  # This defines the Left Margin in pixels. It is the distance from the left-hand edge of the screen.The three onscreen margins (MarginL, MarginR, MarginV) define areas in which the subtitle text will be displayed.
            "MarginR",  # This defines the Right Margin in pixels. It is the distance from the right-hand edge of the screen.
            "MarginV",  # MarginV. This defines the vertical Left Margin in pixels. For a subtitle, it is the distance from the bottom of the screen. For a toptitle, it is the distance from the top of the screen. For a midtitle, the value is ignored - the text will be vertically centred
            "Encoding",  #
        ]

        style = Style()
        style.type = "Style"
        style.Name = "Nomad"
        style.Fontname = "Avenir Next Bold"
        style.Fontsize = fontsize

        style.PrimaryColour = (112, 112, 247, 255)
        style.SecondaryColour = (255, 255, 255, 255)
        style.OutlineColour = (26, 58, 235, 255)
        style.BackColour = (0, 255, 0, 255)  # (26, 58, 235, 255)

        style.Bold = False
        style.Italic = False
        style.Underline = False
        style.StrikeOut = False

        style.ScaleX = 100
        style.ScaleY = 100
        style.Spacing = 0
        style.Angle = 0.0
        style.BorderStyle = 1
        style.Outline = 1
        style.Shadow = 0
        style.Alignment = ALIGN_TOP_CENTER
        style.MarginL = 0
        style.MarginR = 0
        style.MarginV = 0
        style.Encoding = 0

        a.add_style(style)

        a.events_format = ["Layer", "Style", "Start", "End", "MarginV", "Text"]
        for screen in lyric_screens:
            [a.add(event) for event in screen.as_ass_events(style)]

        return a
