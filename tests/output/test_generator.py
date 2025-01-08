import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch
import os

from lyrics_transcriber.output.generator import OutputGenerator, OutputGeneratorConfig, OutputPaths
from lyrics_transcriber.types import LyricsSegment, Word, CorrectionResult, LyricsData, LyricsMetadata


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    return OutputGeneratorConfig(
        output_dir=str(tmp_path / "output"), cache_dir=str(tmp_path / "cache"), video_resolution="360p", max_line_length=36
    )


@pytest.fixture
def output_generator(test_config):
    """Create an OutputGenerator instance with test configuration."""
    return OutputGenerator(config=test_config)


@pytest.fixture
def sample_word():
    """Create a sample Word instance."""
    return Word(text="test", start_time=0.0, end_time=1.0, confidence=0.9)


@pytest.fixture
def sample_segment(sample_word):
    """Create a sample LyricsSegment instance."""
    return LyricsSegment(text="test word", words=[sample_word], start_time=0.0, end_time=1.0)


@pytest.fixture
def sample_correction_result(sample_segment):
    """Create a sample CorrectionResult instance."""
    return CorrectionResult(
        original_segments=[sample_segment],
        corrected_segments=[sample_segment],
        corrected_text="test word",
        corrections=[],
        corrections_made=0,
        confidence=0.9,
        transcribed_text="test word",
        reference_texts={"source": "test word"},
        anchor_sequences=[],
        gap_sequences=[],
        resized_segments=[sample_segment],
        metadata={},
    )


@pytest.fixture
def sample_lyrics_data():
    """Create a sample LyricsData instance."""
    metadata = LyricsMetadata(source="test", track_name="Test Track", artist_names="Test Artist")
    return LyricsData(lyrics="test lyrics", segments=[], metadata=metadata, source="test")


def test_output_generator_initialization(test_config):
    """Test OutputGenerator initialization with valid config."""
    generator = OutputGenerator(config=test_config)
    assert generator.config == test_config
    assert generator.video_resolution_num == (640, 360)
    assert generator.font_size == 50
    assert generator.line_height == 50


def test_invalid_video_resolution(test_config):
    """Test OutputGenerator initialization with invalid video resolution."""
    test_config.video_resolution = "invalid"
    with pytest.raises(ValueError, match="Invalid video_resolution value"):
        OutputGenerator(config=test_config)


@pytest.mark.parametrize(
    "resolution,expected",
    [
        ("4k", ((3840, 2160), 250, 250)),
        ("1080p", ((1920, 1080), 120, 120)),
        ("720p", ((1280, 720), 100, 100)),
        ("360p", ((640, 360), 50, 50)),
    ],
)
def test_video_params(resolution, expected):
    """Test _get_video_params with different resolutions."""
    config = OutputGeneratorConfig(output_dir="test", cache_dir="test", video_resolution=resolution)
    generator = OutputGenerator(config=config)
    assert (generator.video_resolution_num, generator.font_size, generator.line_height) == expected


def test_generate_outputs(output_generator, sample_correction_result, sample_lyrics_data, tmp_path):
    """Test generate_outputs creates expected files."""
    # Create output directory
    os.makedirs(output_generator.config.output_dir, exist_ok=True)
    
    with patch.object(output_generator.plain_text, 'write_lyrics'), \
         patch.object(output_generator.plain_text, 'write_original_transcription'), \
         patch.object(output_generator.plain_text, 'write_corrected_lyrics'), \
         patch.object(output_generator.lyrics_file, 'generate_lrc'), \
         patch.object(output_generator.subtitle, 'generate_ass'), \
         patch.object(output_generator.video, 'generate_video'):
        
        outputs = output_generator.generate_outputs(
            transcription_corrected=sample_correction_result,
            lyrics_results=[sample_lyrics_data],
            output_prefix="test",
            audio_filepath="test.mp3",
            render_video=True
        )
        
        assert isinstance(outputs, OutputPaths)
        # Verify corrections JSON was written
        assert outputs.corrections_json is not None


def test_write_corrections_data(output_generator, sample_correction_result):
    """Test writing corrections data to JSON file."""
    # Create output directory
    os.makedirs(output_generator.config.output_dir, exist_ok=True)
    
    output_path = output_generator.write_corrections_data(
        sample_correction_result,
        "test"
    )
    
    assert output_path.endswith(".json")
    assert Path(output_path).exists()
    
    # Verify JSON content
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert "corrected_text" in data
        assert "corrections_made" in data
        assert "confidence" in data


def test_output_generator_with_background_image(tmp_path):
    """Test OutputGenerator with background image configuration."""
    # Create a dummy background image
    bg_image = tmp_path / "background.jpg"
    bg_image.touch()

    config = OutputGeneratorConfig(
        output_dir=str(tmp_path / "output"), cache_dir=str(tmp_path / "cache"), video_background_image=str(bg_image)
    )

    generator = OutputGenerator(config=config)
    assert generator.config.video_background_image == str(bg_image)


def test_output_generator_invalid_background_image(tmp_path):
    """Test OutputGenerator with non-existent background image."""
    with pytest.raises(FileNotFoundError):
        OutputGeneratorConfig(
            output_dir=str(tmp_path / "output"), cache_dir=str(tmp_path / "cache"), video_background_image="nonexistent.jpg"
        )
