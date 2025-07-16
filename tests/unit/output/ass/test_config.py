from lyrics_transcriber.output.ass.config import ScreenConfig, LineTimingInfo, LineState


def test_screen_config_defaults():
    """Test default values of ScreenConfig."""
    config = ScreenConfig()

    # Screen layout defaults
    assert config.max_visible_lines == 4
    assert config.line_height == 50
    assert config.top_padding == 50
    assert config.video_height == 360

    # Timing defaults
    assert config.screen_gap_threshold == 5.0
    assert config.post_roll_time == 1.0
    assert config.fade_in_ms == 200
    assert config.fade_out_ms == 300
    
    # Lead-in defaults
    assert config.lead_in_color == "112, 112, 247"
    assert config.get_lead_in_color_ass_format() == "&H00F77070&"


def test_screen_config_custom_values():
    """Test custom values can be set in ScreenConfig."""
    config = ScreenConfig(line_height=60, max_visible_lines=3, video_height=1080)

    assert config.max_visible_lines == 3
    assert config.line_height == 60
    assert config.video_height == 1080
    # Other values should remain at defaults
    assert config.fade_in_ms == 200
    assert config.fade_out_ms == 300


def test_screen_config_custom_padding():
    """Test custom padding configuration."""
    config = ScreenConfig(line_height=60, top_padding=120)

    assert config.line_height == 60
    assert config.top_padding == 120  # Custom value, not based on line_height

    # Test default padding behavior
    config_default = ScreenConfig(line_height=60)
    assert config_default.top_padding == 60  # Should equal line_height when not specified


def test_lead_in_color_rgb_conversion():
    """Test RGB to ASS color conversion for lead-in indicator."""
    config = ScreenConfig()
    
    # Test default blue RGB format
    config.lead_in_color = "112, 112, 247"
    assert config.get_lead_in_color_ass_format() == "&H00F77070&"
    
    # Test red color
    config.lead_in_color = "255, 0, 0"
    assert config.get_lead_in_color_ass_format() == "&H000000FF&"
    
    # Test green color
    config.lead_in_color = "0, 255, 0"
    assert config.get_lead_in_color_ass_format() == "&H0000FF00&"
    
    # Test with alpha
    config.lead_in_color = "255, 0, 0, 128"  # Red with 50% opacity
    assert config.get_lead_in_color_ass_format() == "&H7F0000FF&"
    
    # Test backward compatibility with ASS format
    config.lead_in_color = "&HF77070&"
    assert config.get_lead_in_color_ass_format() == "&HF77070&"
    
    # Test invalid format fallback
    config.lead_in_color = "invalid color"
    assert config.get_lead_in_color_ass_format() == "&HF77070&"
    
    # Test edge cases
    config.lead_in_color = "255,255,255"  # No spaces
    assert config.get_lead_in_color_ass_format() == "&H00FFFFFF&"
    
    config.lead_in_color = " 0 , 128 , 255 "  # Extra spaces
    assert config.get_lead_in_color_ass_format() == "&H00FF8000&"


def test_custom_lead_in_color():
    """Test custom lead-in color configuration."""
    config = ScreenConfig(lead_in_color="255, 128, 64")
    
    assert config.lead_in_color == "255, 128, 64"
    assert config.get_lead_in_color_ass_format() == "&H004080FF&"


def test_line_timing_info():
    """Test LineTimingInfo dataclass."""
    timing = LineTimingInfo(
        fade_in_time=1.0,
        end_time=5.0,
        fade_out_time=4.5,
        clear_time=5.5
    )
    
    assert timing.fade_in_time == 1.0
    assert timing.end_time == 5.0
    assert timing.fade_out_time == 4.5
    assert timing.clear_time == 5.5


def test_line_state():
    """Test LineState dataclass."""
    timing = LineTimingInfo(
        fade_in_time=1.0,
        end_time=5.0,
        fade_out_time=4.5,
        clear_time=5.5
    )
    
    state = LineState(
        text="Hello world",
        timing=timing,
        y_position=100
    )
    
    assert state.text == "Hello world"
    assert state.timing == timing
    assert state.y_position == 100
