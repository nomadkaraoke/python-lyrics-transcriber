import pytest
import os
from pathlib import Path

from lyrics_transcriber.output.plain_text import PlainTextGenerator
from lyrics_transcriber.types import (
    LyricsData, LyricsMetadata, LyricsSegment, Word, CorrectionResult
)


@pytest.fixture
def plain_text_generator(tmp_path):
    """Create a PlainTextGenerator instance with a temporary output directory."""
    return PlainTextGenerator(output_dir=str(tmp_path))


@pytest.fixture
def sample_lyrics_data():
    """Create a sample LyricsData instance."""
    metadata = LyricsMetadata(
        source="test_source",
        track_name="Test Track",
        artist_names="Test Artist"
    )
    return LyricsData(
        lyrics="Test lyrics\nSecond line",
        segments=[
            LyricsSegment(
                text="Test lyrics",
                words=[
                    Word(text="Test", start_time=0.0, end_time=0.5),
                    Word(text="lyrics", start_time=0.6, end_time=1.0)
                ],
                start_time=0.0,
                end_time=1.0
            )
        ],
        metadata=metadata,
        source="test_source"
    )


@pytest.fixture
def sample_correction_result():
    """Create a sample CorrectionResult instance."""
    segment = LyricsSegment(
        text="Test lyrics",
        words=[
            Word(text="Test", start_time=0.0, end_time=0.5),
            Word(text="lyrics", start_time=0.6, end_time=1.0)
        ],
        start_time=0.0,
        end_time=1.0
    )
    return CorrectionResult(
        original_segments=[segment],
        corrected_segments=[segment],
        corrected_text="Test lyrics",
        corrections=[],
        corrections_made=0,
        confidence=0.9,
        transcribed_text="Test lyrics",
        reference_texts={"source": "Test lyrics"},
        anchor_sequences=[],
        gap_sequences=[],
        resized_segments=[segment],
        metadata={}
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
        assert content == sample_lyrics_data.lyrics


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
        assert content == sample_correction_result.transcribed_text


def test_error_handling(plain_text_generator, sample_lyrics_data):
    """Test error handling when writing files."""
    # Use an invalid directory to trigger an error
    plain_text_generator.output_dir = "/nonexistent/directory"
    
    with pytest.raises(Exception):
        plain_text_generator.write_lyrics(sample_lyrics_data, "test_output")


def test_write_lyrics_with_special_characters(plain_text_generator):
    """Test handling of special characters in lyrics."""
    lyrics_data = LyricsData(
        lyrics="Special & chars © ñ\nMore £ § ¥",
        segments=[],
        metadata=LyricsMetadata(
            source="test",
            track_name="Test Track",
            artist_names="Test Artist"
        ),
        source="test"
    )
    
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_lyrics(lyrics_data, "test_output")
    
    # Verify file was created and can be read
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Special & chars © ñ" in content
        assert "More £ § ¥" in content


def test_empty_content(plain_text_generator):
    """Test handling of empty content."""
    lyrics_data = LyricsData(
        lyrics="",
        segments=[],
        metadata=LyricsMetadata(
            source="test",
            track_name="Test Track",
            artist_names="Test Artist"
        ),
        source="test"
    )
    
    # Create output directory
    os.makedirs(plain_text_generator.output_dir, exist_ok=True)
    
    output_path = plain_text_generator.write_lyrics(lyrics_data, "test_output")
    
    # Verify file was created
    assert Path(output_path).exists()
    
    # Verify content is empty
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
        assert content == sample_lyrics_data.lyrics 