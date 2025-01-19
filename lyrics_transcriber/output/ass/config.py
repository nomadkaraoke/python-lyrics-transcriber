from dataclasses import dataclass


class ScreenConfig:
    """Configuration for screen timing and layout."""

    def __init__(self, line_height: int = 50, max_visible_lines: int = 4, top_padding: int = None, video_height: int = 720):
        # Screen layout
        self.max_visible_lines = max_visible_lines
        self.line_height = line_height
        self.top_padding = top_padding if top_padding is not None else line_height
        self.video_height = video_height

        # Timing configuration
        self.screen_gap_threshold = 5.0
        self.post_roll_time = 1.0
        self.fade_in_ms = 200
        self.fade_out_ms = 400
        self.cascade_delay_ms = 200
        self.target_preshow_time = 5.0
        self.position_clear_buffer_ms = 300


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