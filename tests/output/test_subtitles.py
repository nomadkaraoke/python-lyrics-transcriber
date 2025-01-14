import pytest
import os
from datetime import timedelta
import logging
from typing import List, Tuple

from lyrics_transcriber.output.subtitles import SubtitlesGenerator
from lyrics_transcriber.types import LyricsSegment, Word
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen


def create_word(text: str, start: float, end: float, confidence: float = 1.0) -> Word:
    """Helper to create a Word."""
    return Word(text=text, start_time=start, end_time=end, confidence=confidence)


def create_segment(start: float, end: float, text: str) -> LyricsSegment:
    """Helper to create a LyricsSegment with words."""
    words = [create_word(text=text, start=start, end=end)]
    return LyricsSegment(text=text, words=words, start_time=start, end_time=end)


@pytest.fixture
def mock_logger():
    """Create a logger that will show debug messages during testing."""
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    
    # Add a console handler to show the logs
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary directory for output files."""
    return str(tmp_path)


@pytest.fixture
def video_resolution() -> Tuple[int, int]:
    """Standard video resolution for testing."""
    return (1920, 1080)


@pytest.fixture
def generator(output_dir, video_resolution, mock_logger):
    """Create a SubtitlesGenerator instance."""
    return SubtitlesGenerator(output_dir=output_dir, video_resolution=video_resolution, font_size=48, line_height=60, logger=mock_logger)


@pytest.fixture
def sample_segments() -> List[LyricsSegment]:
    """Create sample lyrics segments for testing."""
    return [
        create_segment(17.98, 19.94, "I know I have good judgement"),
        create_segment(20.26, 22.10, "I know I have good taste"),
        create_segment(22.36, 24.40, "It's funny and it's ironic"),
        create_segment(24.62, 26.58, "That only I feel that way"),
        create_segment(26.62, 28.60, "I promise em that you're different"),
        create_segment(29.08, 30.96, "And everyone makes mistakes,"),
        create_segment(31.02, 32.84, "but just don't"),
        create_segment(35.98, 37.82, "I heard that you're an actor"),
    ]


def test_generate_ass_success(generator, sample_segments):
    """Test successful ASS file generation."""
    output_prefix = "test_lyrics"
    output_path = generator.generate_ass(sample_segments, output_prefix)

    # Verify output file exists
    assert os.path.exists(output_path)
    assert output_path.endswith(".ass")
    assert "Lyrics Corrected" in output_path

    # Read and verify file contents
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Check for required sections
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        # Check for style definition
        assert "Style: Nomad" in content
        # Check for some dialogue lines
        assert "Dialogue:" in content
        assert "I know I have good judgement" in content


def test_generate_ass_empty_segments(generator):
    """Test ASS generation with empty segments list."""
    output_path = generator.generate_ass([], "test_empty")
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0


def test_generate_ass_invalid_output_dir(video_resolution, mock_logger):
    """Test with invalid output directory."""
    invalid_generator = SubtitlesGenerator(
        output_dir="/nonexistent/directory", video_resolution=video_resolution, font_size=48, line_height=60, logger=mock_logger
    )

    with pytest.raises(Exception):
        invalid_generator.generate_ass([create_segment(1.0, 2.0, "Test")], "test")


def test_screen_creation(generator, sample_segments):
    """Test internal screen creation logic."""
    screens = generator._create_screens(sample_segments)

    # Verify screen creation
    assert len(screens) > 0
    for screen in screens:
        assert isinstance(screen, LyricsScreen)
        assert len(screen.lines) <= screen.MAX_VISIBLE_LINES


def test_styled_subtitles_creation(generator, sample_segments):
    """Test creation of styled ASS subtitles."""
    screens = generator._create_screens(sample_segments)
    ass = generator._create_styled_subtitles(screens, generator.video_resolution, generator.font_size)

    # Verify ASS object properties
    assert ass.styles_format is not None
    assert ass.events_format is not None
    assert len(ass.styles) > 0
    assert len(ass.events) > 0


def test_output_path_generation(generator):
    """Test output path generation."""
    prefix = "test_lyrics"
    path = generator._get_output_path(prefix, "ass")

    assert path.endswith(".ass")
    assert os.path.dirname(path) == generator.output_dir
    assert "test_lyrics" in path


def test_generate_ass_with_unicode(generator, mock_logger):
    """Test ASS generation with Unicode characters."""
    # Create segments with multiple words to ensure proper karaoke timing
    segments = [
        LyricsSegment(
            text="Hello こんにちは",
            start_time=5.0,
            end_time=6.0,
            words=[
                create_word("Hello", 5.0, 5.3),
                create_word("こんにちは", 5.4, 6.0)
            ]
        ),
        LyricsSegment(
            text="World 世界",
            start_time=6.5,
            end_time=7.5,
            words=[
                create_word("World", 6.5, 6.8),
                create_word("世界", 6.9, 7.5)
            ]
        )
    ]
    
    # Debug: Verify screen creation
    screens = generator._create_screens(segments)
    assert len(screens) > 0, "No screens were created"
    assert len(screens[0].lines) > 0, "No lines in first screen"
    
    mock_logger.debug(f"Created {len(screens)} screens")
    for i, screen in enumerate(screens):
        mock_logger.debug(f"Screen {i}: {len(screen.lines)} lines")
        for j, line in enumerate(screen.lines):
            mock_logger.debug(f"  Line {j}: {line.segment.text} ({line.segment.start_time}-{line.segment.end_time})")
    
    # Debug: Verify styled subtitles creation
    ass_obj = generator._create_styled_subtitles(screens, generator.video_resolution, generator.font_size)
    assert len(ass_obj.events) > 0, "No events created in ASS object"
    mock_logger.debug(f"Created {len(ass_obj.events)} events")
    for event in ass_obj.events:
        mock_logger.debug(f"Event: {event.Start}-{event.End}: {event.Text}")
        assert event.Start >= 0, f"Event has negative start time: {event.Start}"
        assert event.End >= 0, f"Event has negative end time: {event.End}"
        # Verify event format
        mock_logger.debug(f"Event type: {event.type}")
        mock_logger.debug(f"Event style: {event.Style}")
        # Style can be either a Style object or a string (style name)
        assert (isinstance(event.Style, str) or 
                event.Style is None or 
                hasattr(event.Style, 'Name')), f"Event style should be string, None, or Style object, got {type(event.Style)}"
        if hasattr(event.Style, 'Name'):
            assert isinstance(event.Style.Name, str), "Style object should have a string Name"
    
    output_path = generator.generate_ass(segments, "unicode_test")
    
    # Verify file exists and contains Unicode in the Events section
    assert os.path.exists(output_path)
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        mock_logger.debug("File content:")
        mock_logger.debug(content)
        
        # Verify style section exists
        assert "[V4+ Styles]" in content
        assert "Style: Nomad" in content
        
        # Verify events section exists and contains our Unicode text
        assert "[Events]" in content
        events_section = content.split('[Events]')[1]
        
        # Look for Dialogue lines containing our text
        assert "Dialogue:" in events_section, "No dialogue events found"
        
        # Check for both Japanese and English text
        dialogue_lines = [line for line in events_section.split('\n') if line.startswith('Dialogue:')]
        full_dialogue = '\n'.join(dialogue_lines)
        mock_logger.debug("Dialogue lines:")
        mock_logger.debug(full_dialogue)
        
        assert "こんにちは" in full_dialogue, "Japanese text not found in dialogue"
        assert "世界" in full_dialogue, "Japanese text not found in dialogue"
        assert "Hello" in full_dialogue, "English text not found in dialogue"
        assert "World" in full_dialogue, "English text not found in dialogue"


def test_generate_ass_style_customization(output_dir, video_resolution, mock_logger):
    """Test ASS generation with custom style parameters."""
    generator = SubtitlesGenerator(
        output_dir=output_dir,
        video_resolution=video_resolution,
        font_size=72,  # Larger font
        line_height=90,  # Larger line height
        logger=mock_logger
    )
    
    segments = [create_segment(1.0, 2.0, "Test")]
    output_path = generator.generate_ass(segments, "style_test")
    
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        styles_section = content.split('[V4+ Styles]')[1].split('[')[0]
        assert "Style: Nomad,Avenir Next Bold,72," in styles_section
