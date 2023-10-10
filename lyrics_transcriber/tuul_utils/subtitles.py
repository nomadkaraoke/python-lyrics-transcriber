from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional
import json
import itertools
from pathlib import Path

from . import ass, timing_data


"""
Functions for generating ASS subtitles from lyric data
"""

VIDEO_SIZE = (400, 320)
LINE_HEIGHT = 30


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
        return f"{{\kf{duration}}}{self.text}"

    def to_dict(self) -> dict:
        return {"text": self.text, "ts": str(self.ts), "end_ts": str(self.end_ts) if self.end_ts else None}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricSegment":
        return cls(
            text=data["text"],
            ts=timedelta(seconds=float(data["ts"])),
            end_ts=timedelta(seconds=float(data["end_ts"])) if data["end_ts"] else None,
        )


@dataclass
class LyricsLine:
    segments: List[LyricSegment] = field(default_factory=list)

    @property
    def ts(self) -> Optional[timedelta]:
        return self.segments[0].ts if len(self.segments) else None

    @property
    def end_ts(self) -> Optional[timedelta]:
        return self.segments[-1].end_ts

    @ts.setter
    def ts(self, value):
        self.segments[0].ts = value

    @end_ts.setter
    def end_ts(self, value):
        self.segments[-1].end_ts = value

    def __str__(self):
        return "".join([f"{{{s.text}}}" for s in self.segments])

    def as_ass_event(
        self,
        screen_start: timedelta,
        screen_end: timedelta,
        style: ass.ASS.Style,
        top_margin: int,
    ):
        e = ass.ASS.Event()
        e.type = "Dialogue"
        e.Layer = 0
        e.Style = style
        e.Start = screen_start.total_seconds()
        e.End = screen_end.total_seconds()
        e.MarginV = top_margin
        e.Text = self.decorate_ass_line(self.segments, screen_start)
        return e

    def decorate_ass_line(self, segments, screen_start_ts: timedelta):
        """Decorate line with karaoke tags"""
        # Prefix the tag with centisecs prior to line in screen
        start_time = (self.ts - screen_start_ts).total_seconds() * 100
        line = f"{{\k{start_time}}}"
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

    @property
    def end_ts(self) -> timedelta:
        return self.lines[-1].end_ts

    def get_line_y(self, line_num: int) -> int:
        _, h = VIDEO_SIZE
        line_count = len(self.lines)
        line_height = LINE_HEIGHT
        return (h / 2) - (line_count * line_height / 2) + (line_num * line_height)

    def as_ass_events(self, style: ass.ASS.Style) -> List[ass.ASS.Event]:
        return [line.as_ass_event(self.start_ts, self.end_ts, style, self.get_line_y(i)) for i, line in enumerate(self.lines)]

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
        return {"lines": [line.to_dict() for line in self.lines], "start_ts": str(self.start_ts) if self.start_ts else None}

    @classmethod
    def from_dict(cls, data: dict) -> "LyricsScreen":
        lines = [LyricsLine.from_dict(line_data) for line_data in data["lines"]]
        start_ts = timedelta(seconds=float(data["start_ts"])) if data["start_ts"] else None
        return cls(lines=lines, start_ts=start_ts)


class LyricsObjectJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (LyricSegment, LyricsLine, LyricsScreen)):
            return o.to_dict()
        return super().default(o)


def create_screens(logger, lyrics_segments, events_tuples):
    segments = iter(timing_data.LyricSegmentIterator(lyrics_segments=lyrics_segments))
    events = iter(events_tuples)
    screens: List[LyricsScreen] = []
    prev_segment: Optional[LyricSegment] = None
    line: Optional[LyricsLine] = None
    screen: Optional[LyricsScreen] = None

    try:
        for event in events:
            ts = event[0]
            marker = event[1]
            if marker == timing_data.LyricMarker.SEGMENT_START:
                segment_text: str = next(segments)
                segment = LyricSegment(segment_text, ts)
                if screen is None:
                    screen = LyricsScreen()
                if line is None:
                    line = LyricsLine()
                line.segments.append(segment)
                if segment_text.endswith("\n"):
                    screen.lines.append(line)
                    line = None
                if segment_text.endswith("\n\n"):
                    screens.append(screen)
                    screen = None
                prev_segment = segment
            elif marker == timing_data.LyricMarker.SEGMENT_END:
                if prev_segment is not None:
                    prev_segment.end_ts = ts
        if line is not None:
            screen.lines.append(line)  # type: ignore[union-attr]
        if screen is not None and len(screen.lines) > 0:
            screens.append(screen)  # type: ignore[arg-type]
    except StopIteration as si:
        logger.error(f"Reached end of segments before end of events. Events: {list(events)}, lyrics: {list(segments)}")

    return screens


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


def create_subtitles(lyric_screens: List[LyricsScreen], display_params: Dict) -> ass.ASS:
    a = ass.ASS()
    a.styles_format = [
        "Name",
        "Alignment",
        "Fontname",
        "Fontsize",
        "PrimaryColour",
        "SecondaryColour",
        "Bold",
        "ScaleX",
        "ScaleY",
        "Spacing",
        "MarginL",
        "MarginR",
        "Encoding",
    ]
    style = ass.ASS.Style()
    style.type = "Style"
    style.Name = "Default"
    style.Fontname = display_params["FontName"]
    style.Fontsize = display_params["FontSize"]
    style.Bold = True
    style.PrimaryColor = display_params["PrimaryColor"]
    style.SecondaryColor = display_params["SecondaryColor"]
    style.Alignment = ass.ASS.ALIGN_TOP_CENTER
    a.add_style(style)

    a.events_format = ["Layer", "Style", "Start", "End", "MarginV", "Text"]
    for screen in lyric_screens:
        [a.add(event) for event in screen.as_ass_events(style)]

    return a
