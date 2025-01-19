import pytest
import os
from pathlib import Path
from typing import List

from lyrics_transcriber.output.lyrics_file import LyricsFileGenerator
from lyrics_transcriber.types import LyricsSegment, Word


@pytest.fixture
def lyrics_file_generator(tmp_path):
    """Create a LyricsFileGenerator instance with a temporary output directory."""
    return LyricsFileGenerator(output_dir=str(tmp_path))


@pytest.fixture
def sample_words() -> List[Word]:
    """Create a list of sample Word objects."""
    return [
        Word(text="Hello", start_time=0.0, end_time=0.5),
        Word(text="world", start_time=0.6, end_time=1.0),
    ]


@pytest.fixture
def sample_segments(sample_words) -> List[LyricsSegment]:
    """Create a list of sample LyricsSegment objects."""
    return [
        LyricsSegment(text="Hello world", words=sample_words, start_time=0.0, end_time=1.0),
        LyricsSegment(
            text="Second line",
            words=[
                Word(text="Second", start_time=1.5, end_time=2.0),
                Word(text="line", start_time=2.1, end_time=2.5),
            ],
            start_time=1.5,
            end_time=2.5,
        ),
    ]


def test_get_output_path(lyrics_file_generator, tmp_path):
    """Test _get_output_path method generates correct paths."""
    output_path = lyrics_file_generator._get_output_path("test_prefix", "lrc")
    expected_path = os.path.join(str(tmp_path), "test_prefix.lrc")
    assert output_path == expected_path


def test_format_lrc_timestamp(lyrics_file_generator):
    """Test _format_lrc_timestamp method formats timestamps correctly."""
    test_cases = [
        # Basic cases
        (0.0, "00:00.000"),
        (1.5, "00:01.500"),
        (61.123, "01:01.123"),
        (3600.001, "60:00.001"),
        
        # Rounding cases
        (1.1234, "00:01.123"),    # Round down
        (1.1235, "00:01.124"),    # Round up (Python rounds .5 up)
        (1.1236, "00:01.124"),    # Round up
        
        # Boundary cases
        (59.9999, "01:00.000"),   # Round to next minute
        (1.999999, "00:02.000"),  # Round up to next second
    ]
    
    for seconds, expected in test_cases:
        result = lyrics_file_generator._format_lrc_timestamp(seconds)
        assert result == expected, f"Failed for {seconds} seconds"


def test_write_lrc_file(lyrics_file_generator, sample_segments, tmp_path):
    """Test _write_lrc_file method creates correct LRC content."""
    output_path = os.path.join(str(tmp_path), "test.lrc")

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write the LRC file
    lyrics_file_generator._write_lrc_file(output_path, sample_segments)

    # Verify file exists
    assert Path(output_path).exists()

    # Read and verify content
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.readlines()

        # Check header
        assert content[0].strip() == "[re:MidiCo]"

        # Check first segment
        assert "[00:00.000]1:/Hello" in content[1]
        assert "[00:00.600]1:world" in content[2]

        # Check second segment
        assert "[00:01.500]1:/Second" in content[3]
        assert "[00:02.100]1:line" in content[4]


def test_generate_lrc(lyrics_file_generator, sample_segments):
    """Test generate_lrc method end-to-end."""
    # Create output directory
    os.makedirs(lyrics_file_generator.output_dir, exist_ok=True)

    output_path = lyrics_file_generator.generate_lrc(sample_segments, "test_output")

    # Verify file was created
    assert Path(output_path).exists()
    assert output_path.endswith(" (Karaoke).lrc")

    # Verify file content
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "[re:MidiCo]" in content
        assert "Hello" in content
        assert "world" in content
        assert "Second" in content
        assert "line" in content


def test_generate_lrc_error_handling(lyrics_file_generator, sample_segments):
    """Test error handling in generate_lrc method."""
    # Use an invalid directory to trigger an error
    lyrics_file_generator.output_dir = "/nonexistent/directory"

    with pytest.raises(Exception):
        lyrics_file_generator.generate_lrc(sample_segments, "test_output")


def test_empty_segments(lyrics_file_generator):
    """Test handling of empty segments list."""
    os.makedirs(lyrics_file_generator.output_dir, exist_ok=True)

    output_path = lyrics_file_generator.generate_lrc([], "test_output")

    # Verify file was created with just the header
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.readlines()
        assert len(content) == 1
        assert content[0].strip() == "[re:MidiCo]"


def test_special_characters(lyrics_file_generator, tmp_path):
    """Test handling of special characters in lyrics."""
    segments = [
        LyricsSegment(
            text="Special & chars © ñ",
            words=[
                Word(text="Special", start_time=0.0, end_time=0.5),
                Word(text="&", start_time=0.6, end_time=0.7),
                Word(text="chars", start_time=0.8, end_time=1.0),
                Word(text="©", start_time=1.1, end_time=1.2),
                Word(text="ñ", start_time=1.3, end_time=1.5),
            ],
            start_time=0.0,
            end_time=1.5,
        )
    ]

    os.makedirs(lyrics_file_generator.output_dir, exist_ok=True)
    output_path = lyrics_file_generator.generate_lrc(segments, "test_output")

    # Verify file was created and can be read
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Special" in content
        assert "&" in content
        assert "©" in content
        assert "ñ" in content
