import pytest
import os
from pathlib import Path

from lyrics_transcriber.output.plain_text import PlainTextGenerator
from lyrics_transcriber.types import (
    LyricsData, LyricsMetadata, LyricsSegment, Word, CorrectionResult
)
from tests.test_helpers import create_test_word, create_test_segment, create_test_lyrics_data


@pytest.fixture
def plain_text_generator(tmp_path):
    """Create a PlainTextGenerator instance with a temporary output directory."""
    return PlainTextGenerator(output_dir=str(tmp_path))


@pytest.fixture
def sample_lyrics_data():
    """Create a sample LyricsData instance."""
    segment = create_test_segment(
        text="Test lyrics",
        words=[
            create_test_word(text="Test", start_time=0.0, end_time=0.5),
            create_test_word(text="lyrics", start_time=0.6, end_time=1.0)
        ],
        start_time=0.0,
        end_time=1.0
    )
    return create_test_lyrics_data(
        segments=[segment],
        source="test_source",
        track_name="Test Track",
        artist_names="Test Artist"
    )


@pytest.fixture
def sample_correction_result():
    """Create a sample CorrectionResult instance."""
    segment = create_test_segment(
        text="Test lyrics",
        words=[
            create_test_word(text="Test", start_time=0.0, end_time=0.5),
            create_test_word(text="lyrics", start_time=0.6, end_time=1.0)
        ],
        start_time=0.0,
        end_time=1.0
    )
    return CorrectionResult(
        original_segments=[segment],
        corrected_segments=[segment],
        corrections=[],
        corrections_made=0,
        confidence=0.9,
        reference_lyrics={},
        anchor_sequences=[],
        gap_sequences=[],
        resized_segments=[segment],
        metadata={},
        correction_steps=[],
        word_id_map={},
        segment_id_map={}
    )


def test_get_output_path(plain_text_generator, tmp_path):
    """Test _get_output_path method generates correct paths."""
    output_path = plain_text_generator._get_output_path("test_prefix", "txt")
    expected_path = os.path.join(str(tmp_path), "test_prefix.txt")
    assert output_path == expected_path


def test_write_lyrics(plain_text_generator, sample_lyrics_data):
    """Test write_lyrics method creates correct file."""
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_lyrics(
        sample_lyrics_data,
        "test_output"
    )
    
    # Verify file was created
    assert Path(output_path).exists()
    assert output_path.endswith(f" (Lyrics {sample_lyrics_data.metadata.source.title()}).txt")
    
    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        expected_content = "\n".join(segment.text for segment in sample_lyrics_data.segments)
        assert content == expected_content


def test_write_corrected_lyrics(plain_text_generator, sample_correction_result):
    """Test write_corrected_lyrics method creates correct file."""
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_corrected_lyrics(
        sample_correction_result.corrected_segments,
        "test_output"
    )
    
    # Verify file was created
    assert Path(output_path).exists()
    assert output_path.endswith(" (Lyrics Corrected).txt")
    
    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        assert content == sample_correction_result.corrected_segments[0].text


def test_write_original_transcription(plain_text_generator, sample_correction_result):
    """Test write_original_transcription method creates correct file."""
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_original_transcription(
        sample_correction_result,
        "test_output"
    )
    
    # Verify file was created
    assert Path(output_path).exists()
    assert output_path.endswith(" (Lyrics Uncorrected).txt")
    
    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        expected_content = " ".join(" ".join(w.text for w in segment.words) for segment in sample_correction_result.original_segments)
        assert content == expected_content


def test_error_handling(plain_text_generator, sample_lyrics_data):
    """Test error handling when writing files."""
    # Use an invalid directory to trigger an error
    plain_text_generator.output_dir = "/nonexistent/directory"
    
    with pytest.raises(Exception):
        plain_text_generator.write_lyrics(sample_lyrics_data, "test_output")


def test_write_lyrics_with_special_characters(plain_text_generator):
    """Test handling of special characters in lyrics."""
    special_segment = create_test_segment(
        text="Special & chars © ñ",
        words=[
            create_test_word(text="Special", start_time=0.0, end_time=0.5),
            create_test_word(text="&", start_time=0.6, end_time=0.7),
            create_test_word(text="chars", start_time=0.8, end_time=1.0),
            create_test_word(text="©", start_time=1.1, end_time=1.2),
            create_test_word(text="ñ", start_time=1.3, end_time=1.5),
        ],
        start_time=0.0,
        end_time=1.5,
    )
    lyrics_data = create_test_lyrics_data(
        segments=[special_segment],
        source="test",
        track_name="Test Track", 
        artist_names="Test Artist"
    )
    
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_lyrics(lyrics_data, "test_output")
    
    # Verify file was created and can be read
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Special & chars © ñ" in content


def test_empty_content(plain_text_generator):
    """Test handling of empty content."""
    lyrics_data = create_test_lyrics_data(
        segments=[],
        source="test",
        track_name="Test Track",
        artist_names="Test Artist"
    )
    
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_lyrics(lyrics_data, "test_output")
    
    # Verify file was created
    assert Path(output_path).exists()
    
    # Verify content is empty (no segments = no content)
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert content == ""


def test_multiple_writes(plain_text_generator, sample_lyrics_data):
    """Test writing multiple files with the same prefix."""
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    # Write same content multiple times
    path1 = plain_text_generator.write_lyrics(sample_lyrics_data, "test_output")
    path2 = plain_text_generator.write_lyrics(sample_lyrics_data, "test_output")
    
    # Verify both files exist and have correct content
    assert Path(path1).exists()
    assert Path(path2).exists()
    assert path1 == path2  # Should overwrite rather than create new file
    
    with open(path1, 'r', encoding='utf-8') as f:
        content = f.read()
        expected_content = "\n".join(segment.text for segment in sample_lyrics_data.segments)
        assert content == expected_content 