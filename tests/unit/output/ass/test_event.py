import pytest
from lyrics_transcriber.output.ass.event import Event
from lyrics_transcriber.output.ass.formatters import Formatters


@pytest.fixture
def event():
    # Store original formatters
    original_formatters = Event.formatters
    
    # Set test formatters
    Event.formatters = {
        "Layer": (Formatters.str_to_integer, Formatters.integer_to_str),
        "Start": (Formatters.str_to_number, Formatters.number_to_str),
        "End": (Formatters.str_to_number, Formatters.number_to_str),
        "Style": (Formatters.same, Formatters.same),
        "Name": (Formatters.same, Formatters.same),
        "MarginL": (Formatters.str_to_integer, Formatters.integer_to_str),
        "MarginR": (Formatters.str_to_integer, Formatters.integer_to_str),
        "MarginV": (Formatters.str_to_integer, Formatters.integer_to_str),
        "Effect": (Formatters.same, Formatters.same),
        "Text": (Formatters.same, Formatters.same),
    }
    
    yield Event()
    
    # Restore original formatters after test
    Event.formatters = original_formatters


def test_event_initialization(event):
    assert event.type is None
    assert event.Layer == 0
    assert event.Start == 0.0
    assert event.End == 0.0
    assert event.Style is None
    assert event.Name == ""
    assert event.MarginL == 0
    assert event.MarginR == 0
    assert event.MarginV == 0
    assert event.Effect == ""
    assert event.Text == ""


def test_set_and_get(event):
    # Test setting and getting various attributes
    event.set("Layer", "5")
    assert event.get("Layer") == "5"
    assert event.Layer == 5

    event.set("Start", "1.5")
    assert event.get("Start") == "1.5"
    assert event.Start == 1.5

    event.set("Text", "Hello")
    assert event.get("Text") == "Hello"
    assert event.Text == "Hello"


def test_invalid_set_get(event):
    # Test setting/getting invalid or non-capitalized attributes
    event.set("invalid", "value")
    assert event.get("invalid") is None

    event.set("type", "value")  # lowercase attribute
    assert event.get("type") is None


def test_copy(event):
    # Test copying to new event
    event.set("Layer", "5")
    event.set("Start", "1.5")
    event.set("Text", "Test")

    copied = event.copy()
    assert copied.Layer == 5
    assert copied.Start == 1.5
    assert copied.Text == "Test"

    # Test copying to existing event
    target = Event()
    event.copy(target)
    assert target.Layer == 5
    assert target.Start == 1.5
    assert target.Text == "Test"


def test_equals(event):
    other = Event()
    assert event.equals(other)  # Should be equal when empty

    event.Layer = 5
    assert not event.equals(other)  # Should not be equal after change

    other.Layer = 5
    assert event.equals(other)  # Should be equal again


def test_same_style(event):
    other = Event()
    assert event.same_style(other)  # Should have same style when empty

    event.Layer = 5
    assert not event.same_style(other)  # Different Layer

    other.Layer = 5
    assert event.same_style(other)  # Same Layer

    # Text and timing differences shouldn't affect style comparison
    event.Text = "Different"
    event.Start = 1.5
    assert event.same_style(other)
