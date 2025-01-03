import pytest
from lyrics_transcriber.correction.text_utils import clean_text


def test_basic_cleaning():
    """Test basic text cleaning functionality."""
    assert clean_text("Hello, World!") == "hello world"
    assert clean_text("  spaces  here  ") == "spaces here"
    assert clean_text("UPPERCASE") == "uppercase"


def test_punctuation_removal():
    """Test that punctuation is properly removed."""
    test_cases = [
        ("Hello, world!", "hello world"),
        ("What's up?", "whats up"),
        ("This; that: other.", "this that other"),
        ('He said "quote" here', "he said quote here"),
    ]
    for input_text, expected in test_cases:
        assert clean_text(input_text) == expected


def test_hyphenated_words():
    """Test that hyphens are handled correctly."""
    test_cases = [
        ("fifty-thousand", "fifty thousand"),
        ("up-to-date", "up to date"),
        ("rock-and-roll", "rock and roll"),
        ("twenty-twenty-twenty", "twenty twenty twenty"),
    ]
    for input_text, expected in test_cases:
        assert clean_text(input_text) == expected


def test_whitespace_normalization():
    """Test that whitespace is properly normalized."""
    test_cases = [
        ("too    many    spaces", "too many spaces"),
        ("\ttabs\there\t", "tabs here"),
        ("\nnewlines\n\nhere\n", "newlines here"),
        ("   leading/trailing   ", "leading trailing"),
    ]
    for input_text, expected in test_cases:
        assert clean_text(input_text) == expected


def test_mixed_cases():
    """Test combinations of different cleaning needs."""
    test_cases = [
        ("  The Quick-Brown Fox's Jump!  ", "the quick brown foxs jump"),
        ("Rock-and-Roll, Baby!!!\nLet's Dance!", "rock and roll baby lets dance"),
        ("Up-To-Date    Information;\nCheck-It-Out!", "up to date information check it out"),
    ]
    for input_text, expected in test_cases:
        assert clean_text(input_text) == expected


def test_empty_and_special_cases():
    """Test edge cases and special inputs."""
    assert clean_text("") == ""
    assert clean_text(" ") == ""
    assert clean_text("-") == ""
    assert clean_text("---") == ""
    assert clean_text("-a-b-c-") == "a b c"
