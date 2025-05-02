import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch
import os

from lyrics_transcriber.output.generator import OutputGenerator, OutputPaths
from lyrics_transcriber.core.config import OutputConfig
from lyrics_transcriber.types import LyricsSegment, Word, CorrectionResult, LyricsData, LyricsMetadata


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    return OutputConfig(
        output_dir=str(tmp_path / "output"), 
        cache_dir=str(tmp_path / "cache"), 
        video_resolution="360p", 
        max_line_length=36,
        output_styles_json=str(tmp_path / "styles.json")
    )


@pytest.fixture
def output_generator(test_config, tmp_path):
    """Create an OutputGenerator instance with test configuration."""
    # Create a styles.json file for testing
    styles_path = tmp_path / "styles.json"
    with open(styles_path, 'w') as f:
        json.dump({"karaoke": {}, "cdg": {}}, f)
    
    test_config.output_styles_json = str(styles_path)
    test_config.styles = {"karaoke": {}, "cdg": {}}
    test_config.render_video = True
    
    # Initialize the generator with the updated config
    generator = OutputGenerator(config=test_config)
    return generator


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
    return LyricsData(segments=[], metadata=metadata, source="test")


def test_output_generator_initialization(test_config):
    """Test OutputGenerator initialization with valid config."""
    generator = OutputGenerator(config=test_config)
    assert generator.config == test_config
    assert generator.video_resolution_num == (640, 360)
    assert generator.font_size == 40
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
        ("360p", ((640, 360), 40, 50)),
    ],
)
def test_video_params(resolution, expected, tmp_path):
    """Test _get_video_params with different resolutions."""
    styles_path = str(tmp_path / "styles.json")
    Path(styles_path).touch()
    config = OutputConfig(output_dir="test", cache_dir="test", video_resolution=resolution, output_styles_json=styles_path)
    generator = OutputGenerator(config=config)
    assert (generator.video_resolution_num, generator.font_size, generator.line_height) == expected


def test_generate_outputs(output_generator, sample_correction_result, sample_lyrics_data, tmp_path):
    """Test generate_outputs creates expected files."""
    # Create output directory
    os.makedirs(output_generator.config.output_dir, exist_ok=True)
    
    # Create mock styles file
    styles_path = os.path.join(tmp_path, "styles.json")
    with open(styles_path, 'w') as f:
        json.dump({"karaoke": {}}, f)
    output_generator.config.output_styles_json = styles_path
    output_generator.config.styles = {"karaoke": {}}
    
    # Enable video rendering for test
    output_generator.config.render_video = True

    # Set up required patched methods including any needed for the test
    with patch.object(output_generator.plain_text, "write_lyrics"), patch.object(
        output_generator.plain_text, "write_original_transcription"
    ), patch.object(output_generator.plain_text, "write_corrected_lyrics"), patch.object(
        output_generator.lyrics_file, "generate_lrc"
    ), patch.object(
        output_generator, "write_corrections_data", return_value="test_corrections.json"
    ), patch.object(
        output_generator.subtitle, "generate_ass", return_value="test.ass"
    ), patch.object(
        output_generator.video, "generate_video", return_value="test.mp4"
    ):

        outputs = output_generator.generate_outputs(
            transcription_corrected=sample_correction_result,
            lyrics_results={"test": sample_lyrics_data},
            output_prefix="test",
            audio_filepath="test.mp3"
        )

        assert isinstance(outputs, OutputPaths)
        assert outputs.corrections_json == "test_corrections.json"
        assert outputs.ass == "test.ass"
        assert outputs.video == "test.mp4"


def test_write_corrections_data(output_generator, sample_correction_result):
    """Test writing corrections data to JSON file."""
    # Create output directory
    os.makedirs(output_generator.config.output_dir, exist_ok=True)

    output_path = output_generator.write_corrections_data(sample_correction_result, "test")

    assert output_path.endswith(".json")
    assert Path(output_path).exists()

    # Verify JSON content
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "corrected_text" in data
        assert "corrections_made" in data
        assert "confidence" in data


def test_output_generator_with_background_image(tmp_path):
    """Test OutputGenerator with background image configuration."""
    # Create a dummy background image
    bg_image = tmp_path / "background.jpg"
    bg_image.touch()
    
    # Create a dummy styles file
    styles_path = tmp_path / "styles.json"
    styles_path.touch()

    config = OutputConfig(
        output_dir=str(tmp_path / "output"), 
        cache_dir=str(tmp_path / "cache"), 
        video_background_image=str(bg_image),
        output_styles_json=str(styles_path)
    )

    generator = OutputGenerator(config=config)
    assert generator.config.video_background_image == str(bg_image)


def test_output_generator_invalid_background_image(tmp_path):
    """Test OutputGenerator with non-existent background image."""
    # Create a dummy styles file
    styles_path = tmp_path / "styles.json"
    styles_path.touch()
    
    with pytest.raises(FileNotFoundError):
        OutputConfig(
            output_dir=str(tmp_path / "output"), 
            cache_dir=str(tmp_path / "cache"), 
            video_background_image="nonexistent.jpg",
            output_styles_json=str(styles_path)
        )
