import pytest
from pathlib import Path
import json
import os
import tempfile

from lyrics_transcriber.output.generator import OutputGenerator, OutputPaths
from lyrics_transcriber.core.config import OutputConfig
from lyrics_transcriber.types import LyricsSegment, Word, CorrectionResult, LyricsData, LyricsMetadata

# Import test helpers
from tests.test_helpers import create_test_word, create_test_segment


@pytest.fixture
def basic_styles_content():
    """Basic styles content for testing."""
    return {
        "karaoke": {
            "font_size": 40,
            "top_padding": 100
        },
        "cdg": {}
    }


@pytest.fixture
def test_config_no_video(tmp_path, basic_styles_content):
    """Create a test configuration without video rendering."""
    styles_path = tmp_path / "styles.json"
    with open(styles_path, 'w') as f:
        json.dump(basic_styles_content, f)
    
    return OutputConfig(
        output_styles_json=str(styles_path),
        output_dir=str(tmp_path / "output"),
        cache_dir=str(tmp_path / "cache"),
        video_resolution="360p",
        max_line_length=36,
        render_video=False,  # Disable video to avoid complexity
        generate_cdg=False   # Disable CDG to avoid complexity
    )


@pytest.fixture
def test_config_with_video(tmp_path, basic_styles_content):
    """Create a test configuration with video rendering enabled."""
    styles_path = tmp_path / "styles.json"
    with open(styles_path, 'w') as f:
        json.dump(basic_styles_content, f)
    
    return OutputConfig(
        output_styles_json=str(styles_path),
        output_dir=str(tmp_path / "output"),
        cache_dir=str(tmp_path / "cache"),
        video_resolution="360p",
        max_line_length=36,
        render_video=True,
        generate_cdg=False
    )


class TestOutputGenerator:
    
    def test_initialization_no_video(self, test_config_no_video):
        """Test OutputGenerator initialization without video rendering."""
        generator = OutputGenerator(config=test_config_no_video)
        
        assert generator.config == test_config_no_video
        assert hasattr(generator, 'plain_text')
        assert hasattr(generator, 'lyrics_file')
        assert hasattr(generator, 'segment_resizer')
        
    def test_initialization_with_video(self, test_config_with_video):
        """Test OutputGenerator initialization with video rendering."""
        generator = OutputGenerator(config=test_config_with_video)
        
        assert generator.config == test_config_with_video
        assert hasattr(generator, 'subtitle')
        assert hasattr(generator, 'video')
        assert generator.video_resolution_num == (640, 360)
        assert generator.font_size == 40
        assert generator.line_height == 50

    def test_initialization_missing_styles_file(self, tmp_path):
        """Test OutputGenerator initialization with missing styles file."""
        config = OutputConfig(
            output_styles_json=str(tmp_path / "nonexistent.json"),
            output_dir=str(tmp_path / "output"),
            cache_dir=str(tmp_path / "cache"),
            render_video=True
        )
        
        with pytest.raises(ValueError, match="Failed to load output styles file"):
            OutputGenerator(config=config)

    def test_initialization_invalid_styles_file(self, tmp_path):
        """Test OutputGenerator initialization with invalid JSON in styles file."""
        styles_path = tmp_path / "invalid.json"
        with open(styles_path, 'w') as f:
            f.write("invalid json content")
        
        config = OutputConfig(
            output_styles_json=str(styles_path),
            output_dir=str(tmp_path / "output"),
            cache_dir=str(tmp_path / "cache"),
            render_video=True
        )
        
        with pytest.raises(ValueError, match="Failed to load output styles file"):
            OutputGenerator(config=config)

    def test_initialization_preview_mode(self, test_config_with_video):
        """Test OutputGenerator initialization in preview mode."""
        generator = OutputGenerator(config=test_config_with_video, preview_mode=True)
        
        assert generator.preview_mode is True
        assert generator.config == test_config_with_video

    @pytest.mark.parametrize(
        "resolution,expected_dims,expected_font,expected_line",
        [
            ("4k", (3840, 2160), 250, 250),
            ("1080p", (1920, 1080), 120, 120),
            ("720p", (1280, 720), 100, 100),
            ("360p", (640, 360), 40, 50),
        ],
    )
    def test_video_params(self, resolution, expected_dims, expected_font, expected_line, tmp_path, basic_styles_content):
        """Test _get_video_params with different resolutions."""
        # Use basic styles without font_size override to test defaults
        basic_styles = {"karaoke": {}, "cdg": {}}
        styles_path = tmp_path / "styles.json"
        with open(styles_path, 'w') as f:
            json.dump(basic_styles, f)
        
        config = OutputConfig(
            output_styles_json=str(styles_path),
            output_dir=str(tmp_path / "output"),
            cache_dir=str(tmp_path / "cache"),
            video_resolution=resolution,
            render_video=True
        )
        
        generator = OutputGenerator(config=config)
        assert generator.video_resolution_num == expected_dims
        assert generator.font_size == expected_font
        assert generator.line_height == expected_line

    def test_invalid_video_resolution(self, tmp_path, basic_styles_content):
        """Test OutputGenerator initialization with invalid video resolution."""
        styles_path = tmp_path / "styles.json"
        with open(styles_path, 'w') as f:
            json.dump(basic_styles_content, f)
        
        config = OutputConfig(
            output_styles_json=str(styles_path),
            output_dir=str(tmp_path / "output"),
            cache_dir=str(tmp_path / "cache"),
            video_resolution="invalid",
            render_video=True
        )
        
        with pytest.raises(ValueError, match="Invalid video_resolution value"):
            OutputGenerator(config=config)

    def test_output_paths_structure(self):
        """Test OutputPaths dataclass structure."""
        paths = OutputPaths()
        
        # Test default values
        assert paths.lrc is None
        assert paths.ass is None
        assert paths.video is None
        assert paths.original_txt is None
        assert paths.corrected_txt is None
        assert paths.corrections_json is None
        assert paths.cdg is None
        assert paths.mp3 is None
        assert paths.cdg_zip is None
        
        # Test setting values
        paths.lrc = "test.lrc"
        paths.video = "test.mp4"
        assert paths.lrc == "test.lrc"
        assert paths.video == "test.mp4"

    def test_get_output_path(self, test_config_no_video):
        """Test _get_output_path method."""
        generator = OutputGenerator(config=test_config_no_video)
        
        path = generator._get_output_path("test_prefix", "txt")
        expected = os.path.join(test_config_no_video.output_dir, "test_prefix.txt")
        assert path == expected

    def test_write_corrections_data(self, test_config_no_video, tmp_path):
        """Test write_corrections_data method."""
        # Create output directory
        os.makedirs(test_config_no_video.output_dir, exist_ok=True)
        
        generator = OutputGenerator(config=test_config_no_video)
        
        # Create a minimal CorrectionResult
        segment = create_test_segment(text="test", words=[create_test_word(text="test")], start_time=0.0, end_time=1.0)
        correction_result = CorrectionResult(
            original_segments=[segment],
            corrected_segments=[segment],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={}
        )
        
        output_path = generator.write_corrections_data(correction_result, "test")
        
        # Verify file was created
        assert os.path.exists(output_path)
        assert output_path.endswith(".json")
        
        # Verify content is valid JSON
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "corrections_made" in data
            assert "confidence" in data
