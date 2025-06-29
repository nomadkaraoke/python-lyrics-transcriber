import pytest
from lyrics_transcriber.output.ass.formatters import Formatters


def test_same():
    assert Formatters.same("test") == "test"
    assert Formatters.same(123) == 123
    assert Formatters.same(None) is None


def test_color_conversions():
    # Test color_to_str
    assert Formatters.color_to_str((255, 255, 255, 255)) == "&H00FFFFFF"  # White
    assert Formatters.color_to_str((255, 0, 0, 255)) == "&H000000FF"  # Red
    assert Formatters.color_to_str((0, 255, 0, 255)) == "&H0000FF00"  # Green
    assert Formatters.color_to_str((0, 0, 255, 255)) == "&H00FF0000"  # Blue

    # Test str_to_color
    assert Formatters.str_to_color("&H00FFFFFF") == (255, 255, 255, 255)  # White
    assert Formatters.str_to_color("&H000000FF") == (255, 0, 0, 255)  # Red
    assert Formatters.str_to_color("&H0000FF00") == (0, 255, 0, 255)  # Green
    assert Formatters.str_to_color("&H00FF0000") == (0, 0, 255, 255)  # Blue

    # Test invalid input - should return white
    assert Formatters.str_to_color("") == (255, 255, 255, 255)
    assert Formatters.str_to_color("invalid") == (255, 255, 255, 255)


def test_boolean_conversions():
    # Test n1bool_to_str
    assert Formatters.n1bool_to_str(True) == "-1"
    assert Formatters.n1bool_to_str(False) == "0"

    # Test str_to_n1bool
    assert Formatters.str_to_n1bool("-1") is True
    assert Formatters.str_to_n1bool("0") is False
    assert Formatters.str_to_n1bool("invalid") is False


def test_integer_conversions():
    # Test integer_to_str
    assert Formatters.integer_to_str(42) == "42"
    assert Formatters.integer_to_str(-42) == "-42"
    assert Formatters.integer_to_str(0) == "0"

    # Test str_to_integer
    assert Formatters.str_to_integer("42") == 42
    assert Formatters.str_to_integer("-42") == -42
    assert Formatters.str_to_integer("0") == 0
    assert Formatters.str_to_integer("invalid") == 0


def test_number_conversions():
    # Test number_to_str
    assert Formatters.number_to_str(42) == "42"
    assert Formatters.number_to_str(42.0) == "42"
    assert Formatters.number_to_str(42.5) == "42.5"

    # Test str_to_number
    assert Formatters.str_to_number("42") == 42.0
    assert Formatters.str_to_number("42.5") == 42.5
    assert Formatters.str_to_number("-42.5") == -42.5
    assert Formatters.str_to_number("invalid") == 0.0


def test_timecode_conversions():
    # Test timecode_to_str
    assert Formatters.timecode_to_str(3661.5) == "1:01:01.50"  # 1h 1m 1.5s
    assert Formatters.timecode_to_str(61.5) == "0:01:01.50"  # 1m 1.5s
    assert Formatters.timecode_to_str(1.5) == "0:00:01.50"  # 1.5s

    # Test str_to_timecode
    assert Formatters.str_to_timecode("1:01:01.50") == 3661.5  # 1h 1m 1.5s
    assert Formatters.str_to_timecode("0:01:01.50") == 61.5  # 1m 1.5s
    assert Formatters.str_to_timecode("0:00:01.50") == 1.5  # 1.5s


def test_tag_argument_to_number():
    assert Formatters.tag_argument_to_number("42") == 42.0
    assert Formatters.tag_argument_to_number("42.5") == 42.5
    assert Formatters.tag_argument_to_number("-42.5") == -42.5
    # Test invalid input with default value
    assert Formatters.tag_argument_to_number("invalid", 0) == 0
    assert Formatters.tag_argument_to_number("invalid") is None


def test_style_conversions():
    # Mock style class for testing
    class MockStyle:
        def __init__(self):
            self.Name = ""
            self.fake = False

    style = MockStyle()
    style.Name = "TestStyle"

    # Test style_to_str
    assert Formatters.style_to_str(style) == "TestStyle"
    assert Formatters.style_to_str(None) == ""

    # Test str_to_style
    style_map = {}
    existing_style = MockStyle()
    existing_style.Name = "ExistingStyle"
    style_map["ExistingStyle"] = existing_style

    # Test getting existing style
    result = Formatters.str_to_style("ExistingStyle", style_map, MockStyle)
    assert result is existing_style

    # Test creating new fake style
    result = Formatters.str_to_style("NewStyle", style_map, MockStyle)
    assert result.Name == "NewStyle"
    assert result.fake is True
    assert "NewStyle" in style_map


def test_timecode_to_str_generic():
    # Test with default parameters (with decimals)
    assert Formatters.timecode_to_str_generic(3661.5) == "1:01:01.50"

    # Test with no decimals (covers the decimal_length=0 branch)
    # 3661.5 rounds to 3662 seconds when no decimals, so it's 1:01:02
    assert Formatters.timecode_to_str_generic(3661.5, decimal_length=0) == "1:01:02"

    # Test with exact integer to avoid rounding issues
    assert Formatters.timecode_to_str_generic(3661.0, decimal_length=0) == "1:01:01"

    # Test with custom lengths
    assert (
        Formatters.timecode_to_str_generic(3661.5, decimal_length=3, seconds_length=3, minutes_length=3, hours_length=2) == "01:001:001.500"
    )
