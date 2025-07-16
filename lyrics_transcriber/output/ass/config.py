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
        lead_in_color: str = "112, 112, 247",  # Default blue color in RGB format
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
        # Lead-in configuration
        self.lead_in_color = lead_in_color

    def get_lead_in_color_ass_format(self) -> str:
        """Convert RGB lead-in color to ASS format.
        
        Accepts either:
        - RGB format: "112, 112, 247" 
        - ASS format: "&HF77070&" (for backward compatibility)
        
        Returns ASS format color string.
        """
        color_str = self.lead_in_color.strip()
        
        # If already in ASS format, return as-is
        if color_str.startswith("&H") and color_str.endswith("&"):
            return color_str
            
        # Parse RGB format "R, G, B" or "R, G, B, A"
        try:
            parts = [int(x.strip()) for x in color_str.split(",")]
            if len(parts) == 3:
                r, g, b = parts
                a = 255  # Default full opacity
            elif len(parts) == 4:
                r, g, b, a = parts
            else:
                raise ValueError(f"Invalid color format: {color_str}")
                
            # Convert to ASS format: &H{alpha}{blue}{green}{red}&
            # Note: alpha is inverted in ASS (255-a)
            return f"&H{255-a:02X}{b:02X}{g:02X}{r:02X}&"
            
        except (ValueError, TypeError) as e:
            # Fallback to default blue if parsing fails
            return "&HF77070&"


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
