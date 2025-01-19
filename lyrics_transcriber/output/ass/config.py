from dataclasses import dataclass


@dataclass
class ScreenConfig:
    """Configuration for screen timing and layout."""

    # Screen layout
    max_visible_lines: int = 4
    line_height: int = 50
    top_padding: int = 50  # One line height of padding
    video_height: int = 720  # 720p default

    # Timing configuration
    screen_gap_threshold: float = 5.0
    post_roll_time: float = 1.0
    fade_in_ms: int = 100
    fade_out_ms: int = 400
    cascade_delay_ms: int = 200
    target_preshow_time: float = 5.0
    position_clear_buffer_ms: int = 300


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
