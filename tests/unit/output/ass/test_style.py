import pytest
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.constants import ALIGN_BOTTOM_CENTER


@pytest.fixture
def style():
    return Style()


def test_style_initialization(style):
    assert style.type is None
    assert style.fake is False
    assert style.Name == ""
    assert style.Fontname == ""
    assert style.Fontsize == 1.0
    assert style.PrimaryColour == (255, 255, 255, 255)
    assert style.SecondaryColour == (255, 255, 255, 255)
    assert style.OutlineColour == (255, 255, 255, 255)
    assert style.BackColour == (255, 255, 255, 255)
    assert style.Bold is False
    assert style.Italic is False
    assert style.Underline is False
    assert style.StrikeOut is False
    assert style.ScaleX == 100
    assert style.ScaleY == 100
    assert style.Spacing == 0
    assert style.Angle == 0.0
    assert style.BorderStyle == 1
    assert style.Outline == 0
    assert style.Shadow == 0
    assert style.Alignment == ALIGN_BOTTOM_CENTER
    assert style.MarginL == 0
    assert style.MarginR == 0
    assert style.MarginV == 0
    assert style.Encoding == 0


def test_style_set_get(style):
    # Test string attributes
    style.set("Name", "TestStyle")
    assert style.get("Name") == "TestStyle"

    # Test number attributes
    style.set("Fontsize", "12.5")
    assert style.get("Fontsize") == "12.5"
    assert style.Fontsize == 12.5

    # Test color attributes
    style.set("PrimaryColour", "&H000000FF")  # Red
    assert style.get("PrimaryColour") == "&H000000FF"
    assert style.PrimaryColour == (255, 0, 0, 255)

    # Test boolean attributes
    style.set("Bold", "-1")
    assert style.get("Bold") == "-1"
    assert style.Bold is True

    # Test integer attributes
    style.set("ScaleX", "200")
    assert style.get("ScaleX") == "200"
    assert style.ScaleX == 200


def test_style_invalid_set_get(style):
    # Test setting invalid attribute
    style.set("InvalidAttr", "value")
    assert style.get("InvalidAttr") is None

    # Test setting lowercase attribute
    style.set("name", "value")
    assert style.get("name") is None

    # Test using aliases (empty by default)
    style.set("alias", "value")
    assert style.get("alias") is None


def test_style_copy(style):
    # Modify original style
    style.Name = "Original"
    style.Fontsize = 24.0
    style.Bold = True
    style.PrimaryColour = (255, 0, 0, 255)

    # Test copying to new style
    copied = style.copy()
    assert copied.Name == "Original"
    assert copied.Fontsize == 24.0
    assert copied.Bold is True
    assert copied.PrimaryColour == (255, 0, 0, 255)

    # Test copying to existing style
    target = Style()
    style.copy(target)
    assert target.Name == "Original"
    assert target.Fontsize == 24.0
    assert target.Bold is True
    assert target.PrimaryColour == (255, 0, 0, 255)


def test_style_equals(style):
    other = Style()
    assert style.equals(other)  # Should be equal when empty

    # Test with different attributes
    style.Name = "Style1"
    other.Name = "Style2"
    assert not style.equals(other)
    assert style.equals(other, names_can_differ=True)

    # Test with fake styles
    style.fake = True
    assert not style.equals(other)

    # Test with same attributes
    other.Name = "Style1"
    style.fake = False
    assert style.equals(other)

    # Test with different non-name attributes
    style.Fontsize = 24.0
    assert not style.equals(other)


def test_style_same_style_different_values():
    style1 = Style()
    style2 = Style()

    # These should still be equal even with different values
    style1.Name = "Style1"
    style2.Name = "Style1"
    style1.Fontsize = 24.0
    style2.Fontsize = 12.0

    assert style1.equals(style2) is False  # Different Fontsize
    assert style1.Name == style2.Name  # But same name


def test_style_aliases(style):
    # Set up an alias
    Style.aliases = {"color": "PrimaryColour"}

    # Test setting via alias
    style.set("color", "&H000000FF")  # Red
    assert style.PrimaryColour == (255, 0, 0, 255)

    # Test getting via alias
    assert style.get("color") == "&H000000FF"

    # Test invalid alias
    style.set("invalid_alias", "value")
    assert style.get("invalid_alias") is None

    # Clean up
    Style.aliases = {}


def test_style_lowercase_attributes(style):
    # Test setting lowercase attribute (should be ignored)
    style.set("name", "Test")
    assert style.Name == ""  # Should not change

    # Test getting lowercase attribute
    assert style.get("name") is None


def test_style_existing_lowercase_attributes(style):
    # Add a lowercase attribute directly
    setattr(style, "lowercase", "value")

    # Test setting existing lowercase attribute (should be ignored)
    style.set("lowercase", "new_value")
    assert getattr(style, "lowercase") == "value"  # Should not change

    # Test getting existing lowercase attribute
    assert style.get("lowercase") is None
