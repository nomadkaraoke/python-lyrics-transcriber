from dataclasses import dataclass


class ScreenConfig:
    """Configuration for screen timing and layout."""

    def __init__(
        self,
        line_height: int = 50,
        max_visible_lines: int = 4,
        top_padding: int = None,
        video_width: int = 640,
        video_height: int = 360,
        screen_gap_threshold: float = 5.0,
        post_roll_time: float = 1.0,
        fade_in_ms: int = 200,
        fade_out_ms: int = 300,
    ):
        # Screen layout
        self.max_visible_lines = max_visible_lines
        self.line_height = line_height
        self.top_padding = top_padding if top_padding is not None else line_height
        self.video_height = video_height
        self.video_width = video_width
        # Timing configuration
        self.screen_gap_threshold = screen_gap_threshold
        self.post_roll_time = post_roll_time
        self.fade_in_ms = fade_in_ms
        self.fade_out_ms = fade_out_ms


@dataclass
class LineTimingInfo:
    """Timing information for a single line."""

    fade_in_time: float
    end_time: float
    fade_out_time: float
    clear_time: float


@dataclass
class LineState:
    """Complete state for a single line."""

    text: str
    timing: LineTimingInfo
    y_position: int
