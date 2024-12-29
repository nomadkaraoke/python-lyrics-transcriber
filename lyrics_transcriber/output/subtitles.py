from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
import json
import itertools
from pathlib import Path
from enum import IntEnum
import logging

from . import ass


"""
Functions for generating ASS subtitles from lyric data
"""


class LyricSegmentIterator:
    def __init__(self, lyrics_segments: List[str]):
        self._segments = lyrics_segments
        self._current_segment = 0

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
class LyricSegment:
    text: str
    ts: timedelta
    end_ts: Optional[timedelta] = None

    def adjust_timestamps(self, adjustment) -> "LyricSegment":
        ts = self.ts + adjustment
        end_ts = self.end_ts + adjustment if self.end_ts else None
        return LyricSegment(self.text, ts, end_ts)

    def to_ass(self) -> str:
        """Render this segment as part of an ASS event line"""
        duration = (self.end_ts - self.ts).total_seconds() * 100
        return rf"{{\kf{duration}}}{self.text}"

    def to_dict(self) -> dict:
        return {"text": self.text, "ts": self.ts.total_seconds(), "end_ts": self.end_ts.total_seconds() if self.end_ts else None}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricSegment":
        return cls(
            text=data["text"],
            ts=timedelta(seconds=data["ts"]),
            end_ts=timedelta(seconds=data["end_ts"]) if data["end_ts"] is not None else None,
        )


@dataclass
class LyricsLine:
    segments: List[LyricSegment] = field(default_factory=list)

    @property
    def ts(self) -> Optional[timedelta]:
        return self.segments[0].ts if len(self.segments) else None

    @property
    def end_ts(self) -> Optional[timedelta]:
        return self.segments[-1].end_ts if self.segments else None

    @ts.setter
    def ts(self, value):
        self.segments[0].ts = value

    @end_ts.setter
    def end_ts(self, value):
        self.segments[-1].end_ts = value

    def __str__(self):
        return "".join([f"{{{s.text}}}" for s in self.segments])

    def as_ass_event(self, screen_start: timedelta, screen_end: timedelta, style: ass.ASS.Style, y_position: int):
        e = ass.ASS.Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = screen_start.total_seconds()
        e.End = screen_end.total_seconds()
        e.MarginV = y_position
        e.Text = self.decorate_ass_line(self.segments, screen_start)

        # Set alignment to top-center
        e.Text = "{\\an8}" + e.Text

        return e

    def decorate_ass_line(self, segments, screen_start_ts: timedelta):
        """Decorate line with karaoke tags"""
        # Prefix the tag with centisecs prior to line in screen
        start_time = (self.ts - screen_start_ts).total_seconds() * 100
        line = rf"{{\k{start_time}}}"
        prev_end: Optional[timedelta] = None
        for s in self.segments:
            if prev_end is not None and prev_end < s.ts:
                blank_segment = LyricSegment("", prev_end, s.ts)
                line += blank_segment.to_ass()
            line += s.to_ass()
            prev_end = s.end_ts

        return line

    def adjust_timestamps(self, adjustment) -> "LyricsLine":
        new_segments = [s.adjust_timestamps(adjustment) for s in self.segments]
        start_ts = self.ts + adjustment if self.ts else None
        return LyricsLine(new_segments)

    def to_dict(self) -> dict:
        return {"segments": [segment.to_dict() for segment in self.segments]}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricsLine":
        segments = [LyricSegment.from_dict(segment_data) for segment_data in data["segments"]]
        return cls(segments=segments)


@dataclass
class LyricsScreen:
    lines: List[LyricsLine] = field(default_factory=list)
    start_ts: Optional[timedelta] = None
    video_size: Tuple[int, int] = None
    line_height: int = None
    logger: logging.Logger = None

    @property
    def end_ts(self) -> timedelta:
        return self.lines[-1].end_ts

    def get_line_y(self, line_num: int) -> int:
        _, h = self.video_size
        line_count = len(self.lines)
        total_height = line_count * self.line_height

        # Calculate the top margin to center the lyrics block
        top_margin = (h - total_height) / 2

        # Calculate the y-position for this specific line
        line_y = top_margin + (line_num * self.line_height)

        # if self.logger:
        #     self.logger.debug(f"Line {line_num + 1} positioning:")
        #     self.logger.debug(f"  Video height: {h}")
        #     self.logger.debug(f"  Total lines: {line_count}")
        #     self.logger.debug(f"  Line height: {self.line_height}")
        #     self.logger.debug(f"  Total lyrics height: {total_height}")
        #     self.logger.debug(f"  Top margin: {top_margin}")
        #     self.logger.debug(f"  Line y: {line_y}")

        return int(line_y)

    def as_ass_events(self, style: ass.ASS.Style) -> List[ass.ASS.Event]:
        events = []
        for i, line in enumerate(self.lines):
            y_position = self.get_line_y(i)

            # if self.logger:
            #     self.logger.debug(f"Creating ASS event for line {i + 1} at y-position: {y_position}")

            event = line.as_ass_event(self.start_ts, self.end_ts, style, y_position)
            events.append(event)
        return events

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
        start_ts = timedelta(seconds=data["start_ts"]) if data["start_ts"] is not None else None
        return cls(lines=lines, start_ts=start_ts)


class LyricsObjectJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (LyricSegment, LyricsLine, LyricsScreen)):
            return o.to_dict()
        return super().default(o)


def set_segment_end_times(screens: List[LyricsScreen], song_duration_seconds: int) -> List[LyricsScreen]:
    """
    Infer end times of lines for screens where they are not already set.
    """
    segments = list(itertools.chain.from_iterable([l.segments for s in screens for l in s.lines]))
    for i, segment in enumerate(segments):
        if not segment.end_ts:
            if i == len(segments) - 1:
                segment.end_ts = timedelta(seconds=song_duration_seconds)
            else:
                next_segment = segments[i + 1]
                segment.end_ts = next_segment.ts
    return screens


def set_screen_start_times(screens: List[LyricsScreen]) -> List[LyricsScreen]:
    """
    Set start times for screens to the end times of the previous screen.
    """
    prev_screen = None
    for screen in screens:
        if prev_screen is None:
            screen.start_ts = timedelta()
        else:
            screen.start_ts = prev_screen.end_ts + timedelta(seconds=0.1)
        prev_screen = screen
    return screens


def create_styled_subtitles(
    lyric_screens: List[LyricsScreen],
    resolution,
    fontsize,
) -> ass.ASS:
    a = ass.ASS()
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

    style = ass.ASS.Style()
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
    style.Alignment = ass.ASS.ALIGN_TOP_CENTER
    style.MarginL = 0
    style.MarginR = 0
    style.MarginV = 0
    style.Encoding = 0

    a.add_style(style)

    a.events_format = ["Layer", "Style", "Start", "End", "MarginV", "Text"]
    for screen in lyric_screens:
        [a.add(event) for event in screen.as_ass_events(style)]

    return a
