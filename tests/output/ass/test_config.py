from lyrics_transcriber.output.ass.config import ScreenConfig, LineTimingInfo, LineState


def test_screen_config_defaults():
    """Test default values of ScreenConfig."""
    config = ScreenConfig()

    # Screen layout defaults
    assert config.max_visible_lines == 4
    assert config.line_height == 50
    assert config.top_padding == 50
    assert config.video_height == 720

    # Timing defaults
    assert config.screen_gap_threshold == 5.0
    assert config.post_roll_time == 1.0
    assert config.fade_in_ms == 200
    assert config.fade_out_ms == 400
    assert config.cascade_delay_ms == 200
    assert config.target_preshow_time == 5.0
    assert config.position_clear_buffer_ms == 300


def test_screen_config_custom_values():
    """Test custom values can be set in ScreenConfig."""
    config = ScreenConfig(line_height=60, max_visible_lines=3, video_height=1080)

    assert config.max_visible_lines == 3
    assert config.line_height == 60
    assert config.video_height == 1080
    # Other values should remain at defaults
    assert config.fade_in_ms == 200
    assert config.fade_out_ms == 400
    assert config.cascade_delay_ms == 200


def test_screen_config_custom_padding():
    """Test custom top padding in ScreenConfig."""
    config = ScreenConfig(line_height=60, top_padding=100)
    assert config.top_padding == 100

    # Test default padding equals line height
    config = ScreenConfig(line_height=80)
    assert config.top_padding == 80


def test_line_timing_info():
    """Test LineTimingInfo creation and values."""
    # fmt: off
    timing = LineTimingInfo(
        fade_in_time=10.0,
        end_time=15.0,
        fade_out_time=15.4,
        clear_time=15.7
    )
    # fmt: on

    assert timing.fade_in_time == 10.0
    assert timing.end_time == 15.0
    assert timing.fade_out_time == 15.4
    assert timing.clear_time == 15.7


def test_line_state():
    """Test LineState creation and values."""
    # fmt: off
    timing = LineTimingInfo(
        fade_in_time=10.0,
        end_time=15.0,
        fade_out_time=15.4,
        clear_time=15.7
    )
    
    state = LineState(
        text="Test line",
        timing=timing,
        y_position=100
    )
    # fmt: on

    assert state.text == "Test line"
    assert state.timing == timing
    assert state.y_position == 100
