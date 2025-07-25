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
    
    # New lead-in indicator defaults
    assert config.lead_in_enabled == True
    assert config.lead_in_width_percent == 3.5
    assert config.lead_in_height_percent == 4.0
    assert config.lead_in_opacity_percent == 70.0
    assert config.lead_in_outline_thickness == 0
    assert config.lead_in_outline_color == "0, 0, 0"
    assert config.lead_in_gap_threshold == 5.0
    assert config.lead_in_horiz_offset_percent == 0.0
    assert config.lead_in_vert_offset_percent == 0.0


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


def test_lead_in_enabled_configuration():
    """Test lead-in enabled/disabled configuration."""
    # Test enabled (default)
    config = ScreenConfig()
    assert config.lead_in_enabled == True
    
    # Test disabled
    config = ScreenConfig(lead_in_enabled=False)
    assert config.lead_in_enabled == False


def test_lead_in_size_configuration():
    """Test lead-in size configuration as percentages."""
    config = ScreenConfig(
        lead_in_width_percent=5.0,
        lead_in_height_percent=6.0
    )
    
    assert config.lead_in_width_percent == 5.0
    assert config.lead_in_height_percent == 6.0


def test_lead_in_opacity_configuration():
    """Test lead-in opacity configuration and ASS conversion."""
    # Test default opacity
    config = ScreenConfig()
    assert config.lead_in_opacity_percent == 70.0
    assert config.get_lead_in_opacity_ass_format() == "&H4C&"  # 70% opacity
    
    # Test custom opacity
    config = ScreenConfig(lead_in_opacity_percent=50.0)
    assert config.lead_in_opacity_percent == 50.0
    assert config.get_lead_in_opacity_ass_format() == "&H7F&"  # 50% opacity
    
    # Test full opacity
    config = ScreenConfig(lead_in_opacity_percent=100.0)
    assert config.get_lead_in_opacity_ass_format() == "&H00&"  # 100% opacity
    
    # Test transparent
    config = ScreenConfig(lead_in_opacity_percent=0.0)
    assert config.get_lead_in_opacity_ass_format() == "&HFF&"  # 0% opacity


def test_lead_in_outline_configuration():
    """Test lead-in outline configuration."""
    # Test no outline (default)
    config = ScreenConfig()
    assert config.lead_in_outline_thickness == 0
    assert config.lead_in_outline_color == "0, 0, 0"
    
    # Test custom outline
    config = ScreenConfig(
        lead_in_outline_thickness=3,
        lead_in_outline_color="255, 255, 255"
    )
    assert config.lead_in_outline_thickness == 3
    assert config.lead_in_outline_color == "255, 255, 255"
    assert config.get_lead_in_outline_color_ass_format() == "&H00FFFFFF&"


def test_lead_in_outline_color_conversion():
    """Test lead-in outline color RGB to ASS conversion."""
    config = ScreenConfig()
    
    # Test white outline
    config.lead_in_outline_color = "255, 255, 255"
    assert config.get_lead_in_outline_color_ass_format() == "&H00FFFFFF&"
    
    # Test black outline (default)
    config.lead_in_outline_color = "0, 0, 0"
    assert config.get_lead_in_outline_color_ass_format() == "&H00000000&"
    
    # Test red outline
    config.lead_in_outline_color = "255, 0, 0"
    assert config.get_lead_in_outline_color_ass_format() == "&H000000FF&"
    
    # Test with alpha
    config.lead_in_outline_color = "255, 255, 255, 128"
    assert config.get_lead_in_outline_color_ass_format() == "&H7FFFFFFF&"
    
    # Test ASS format compatibility
    config.lead_in_outline_color = "&H00FFFFFF&"
    assert config.get_lead_in_outline_color_ass_format() == "&H00FFFFFF&"
    
    # Test invalid format fallback
    config.lead_in_outline_color = "invalid"
    assert config.get_lead_in_outline_color_ass_format() == "&H000000&"  # Fallback to black


def test_lead_in_gap_threshold_configuration():
    """Test lead-in gap threshold configuration."""
    # Test default
    config = ScreenConfig()
    assert config.lead_in_gap_threshold == 5.0
    
    # Test custom value
    config = ScreenConfig(lead_in_gap_threshold=3.0)
    assert config.lead_in_gap_threshold == 3.0


def test_lead_in_horizontal_offset_configuration():
    """Test lead-in horizontal offset configuration."""
    # Test default (no offset)
    config = ScreenConfig()
    assert config.lead_in_horiz_offset_percent == 0.0
    
    # Test negative offset (move left)
    config = ScreenConfig(lead_in_horiz_offset_percent=-2.5)
    assert config.lead_in_horiz_offset_percent == -2.5
    
    # Test positive offset (move right)
    config = ScreenConfig(lead_in_horiz_offset_percent=1.5)
    assert config.lead_in_horiz_offset_percent == 1.5


def test_lead_in_vertical_offset_configuration():
    """Test lead-in vertical offset configuration."""
    # Test default (no offset)
    config = ScreenConfig()
    assert config.lead_in_vert_offset_percent == 0.0
    
    # Test negative offset (move up)
    config = ScreenConfig(lead_in_vert_offset_percent=-1.0)
    assert config.lead_in_vert_offset_percent == -1.0
    
    # Test positive offset (move down)
    config = ScreenConfig(lead_in_vert_offset_percent=2.0)
    assert config.lead_in_vert_offset_percent == 2.0


def test_lead_in_all_options_together():
    """Test all lead-in options configured together."""
    config = ScreenConfig(
        lead_in_enabled=True,
        lead_in_width_percent=4.5,
        lead_in_height_percent=5.5,
        lead_in_opacity_percent=80.0,
        lead_in_outline_thickness=2,
        lead_in_outline_color="128, 128, 128",
        lead_in_gap_threshold=3.0,
        lead_in_color="255, 140, 0",
        lead_in_horiz_offset_percent=-1.5,
        lead_in_vert_offset_percent=1.0
    )
    
    assert config.lead_in_enabled == True
    assert config.lead_in_width_percent == 4.5
    assert config.lead_in_height_percent == 5.5
    assert config.lead_in_opacity_percent == 80.0
    assert config.lead_in_outline_thickness == 2
    assert config.lead_in_outline_color == "128, 128, 128"
    assert config.lead_in_gap_threshold == 3.0
    assert config.lead_in_color == "255, 140, 0"
    assert config.lead_in_horiz_offset_percent == -1.5
    assert config.lead_in_vert_offset_percent == 1.0
    
    # Test color conversions work properly
    assert config.get_lead_in_color_ass_format() == "&H00008CFF&"  # Orange
    assert config.get_lead_in_outline_color_ass_format() == "&H00808080&"  # Gray
    assert config.get_lead_in_opacity_ass_format() == "&H33&"  # 80% opacity
