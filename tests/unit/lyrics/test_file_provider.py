import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import logging

from lyrics_transcriber.lyrics.file_provider import FileProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData, LyricsMetadata


class TestFileProvider:
    """Test cases for FileProvider class."""

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        logger = Mock(spec=logging.Logger)
        logger.getEffectiveLevel.return_value = logging.INFO
        mock_handler = Mock()
        mock_handler.formatter = Mock()
        logger.handlers = [mock_handler]
        return logger

    @pytest.fixture
    def temp_lyrics_file(self, tmp_path):
        """Create a temporary lyrics file for testing."""
        lyrics_content = """[Verse 1]
Hello world
This is a test

[Chorus]
Test lyrics here
Another line
"""
        lyrics_file = tmp_path / "test_lyrics.txt"
        lyrics_file.write_text(lyrics_content)
        return str(lyrics_file)

    @pytest.fixture
    def config_with_file(self, temp_lyrics_file):
        """Config with a valid lyrics file."""
        return LyricsProviderConfig(lyrics_file=temp_lyrics_file)

    @pytest.fixture
    def config_without_file(self):
        """Config without a lyrics file."""
        return LyricsProviderConfig()

    @pytest.fixture
    def file_provider(self, config_with_file, mock_logger):
        """FileProvider instance for testing."""
        return FileProvider(config_with_file, mock_logger)

    def test_init(self, config_with_file, mock_logger):
        """Test FileProvider initialization."""
        provider = FileProvider(config_with_file, mock_logger)
        
        assert provider.config == config_with_file
        assert provider.logger == mock_logger
        assert provider.title is None
        assert provider.artist is None

    def test_init_without_logger(self, config_with_file):
        """Test FileProvider initialization without logger."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            provider = FileProvider(config_with_file)
            assert provider.logger == mock_logger

    def test_get_lyrics_stores_metadata(self, file_provider):
        """Test that get_lyrics stores artist and title."""
        artist = "Test Artist"
        title = "Test Song"
        
        # Mock the lower-level methods to avoid complex call chain
        with patch.object(file_provider, '_fetch_data_from_source', return_value={"text": "test", "source": "file", "filepath": "test.txt"}):
            with patch.object(file_provider, '_convert_result_format', return_value=Mock()):
                result = file_provider.get_lyrics(artist, title)
                
                # Check that metadata was stored
                assert file_provider.artist == artist
                assert file_provider.title == title

    def test_fetch_data_from_source_success(self, file_provider, temp_lyrics_file):
        """Test successful lyrics fetching from file."""
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            processed_content = "[Verse 1]\nHello world\nThis is a test\n\n[Chorus]\nTest lyrics here\nAnother line"
            mock_processor.process.return_value = processed_content
            mock_processor_class.return_value = mock_processor
            
            result = file_provider._fetch_data_from_source("Artist", "Title")
            
            assert result is not None
            assert result["text"] == processed_content
            assert result["source"] == "file"
            assert result["filepath"] == temp_lyrics_file
            
            # Verify processor was initialized correctly
            mock_processor_class.assert_called_once()
            call_args = mock_processor_class.call_args[1]
            assert call_args["input_filename"] == temp_lyrics_file
            assert call_args["max_line_length"] == file_provider.max_line_length

    def test_fetch_data_from_source_no_file_in_config(self, mock_logger):
        """Test fetching when no lyrics file is specified in config."""
        config = LyricsProviderConfig()
        provider = FileProvider(config, mock_logger)
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        mock_logger.warning.assert_called_with("No lyrics file specified in config")

    def test_fetch_data_from_source_file_not_found(self, mock_logger):
        """Test fetching when lyrics file doesn't exist."""
        config = LyricsProviderConfig(lyrics_file="/nonexistent/file.txt")
        provider = FileProvider(config, mock_logger)
        
        result = provider._fetch_data_from_source("Artist", "Title")
        
        assert result is None
        mock_logger.error.assert_called()

    def test_fetch_data_from_source_processor_error(self, file_provider):
        """Test handling processor errors."""
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor_class.side_effect = Exception("Processing failed")
            
            result = file_provider._fetch_data_from_source("Artist", "Title")
            
            assert result is None
            file_provider.logger.error.assert_called()

    def test_convert_result_format_success(self, file_provider):
        """Test successful result format conversion."""
        file_provider.title = "Test Song"
        file_provider.artist = "Test Artist"
        
        raw_data = {
            "text": "Test lyrics\nSecond line",
            "source": "file",
            "filepath": "/path/to/file.txt"
        }
        
        with patch.object(file_provider, '_create_segments_with_words') as mock_create_segments:
            mock_segments = [Mock(), Mock()]
            mock_create_segments.return_value = mock_segments
            
            result = file_provider._convert_result_format(raw_data)
            
            assert isinstance(result, LyricsData)
            assert result.source == "file"
            assert result.segments == mock_segments
            assert isinstance(result.metadata, LyricsMetadata)
            assert result.metadata.source == "file"
            assert result.metadata.track_name == "Test Song"
            assert result.metadata.artist_names == "Test Artist"
            assert result.metadata.lyrics_provider == "file"
            assert result.metadata.lyrics_provider_id == "/path/to/file.txt"
            assert not result.metadata.is_synced
            assert result.metadata.provider_metadata == {"filepath": "/path/to/file.txt"}
            
            # Verify segments were created correctly
            mock_create_segments.assert_called_once_with("Test lyrics\nSecond line", is_synced=False)

    def test_convert_result_format_error(self, file_provider):
        """Test error handling in result format conversion."""
        file_provider.title = "Test Song"
        file_provider.artist = "Test Artist"
        
        raw_data = {
            "text": "Test lyrics",
            "source": "file",
            "filepath": "/path/to/file.txt"
        }
        
        with patch.object(file_provider, '_create_segments_with_words', side_effect=Exception("Segment creation failed")):
            with pytest.raises(Exception, match="Segment creation failed"):
                file_provider._convert_result_format(raw_data)
            
            file_provider.logger.error.assert_called()

    def test_fetch_data_logs_file_info(self, file_provider, temp_lyrics_file):
        """Test that file information is logged correctly."""
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process.return_value = "Processed content"
            mock_processor_class.return_value = mock_processor
            
            file_provider._fetch_data_from_source("Artist", "Title")
            
            # Check that appropriate log messages were called
            file_provider.logger.info.assert_any_call(f"Found lyrics file: {Path(temp_lyrics_file)}")
            file_provider.logger.info.assert_any_call("Successfully processed lyrics file")

    def test_fetch_data_logs_debug_info(self, file_provider, temp_lyrics_file):
        """Test that debug information is logged correctly."""
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            processed_text = "Processed lyrics content"
            mock_processor.process.return_value = processed_text
            mock_processor_class.return_value = mock_processor
            
            file_provider._fetch_data_from_source("Artist", "Title")
            
            # Check debug log calls - need to match actual log message format
            file_provider.logger.debug.assert_any_call(f"Looking for lyrics file at: {Path(temp_lyrics_file)} (absolute: {Path(temp_lyrics_file).absolute()})")
            file_provider.logger.debug.assert_any_call("Created KaraokeLyricsProcessor instance")
            file_provider.logger.debug.assert_any_call(f"Processed text length: {len(processed_text)} characters")

    def test_convert_result_format_debug_logging(self, file_provider):
        """Test debug logging in convert_result_format."""
        file_provider.title = "Test Song"
        file_provider.artist = "Test Artist"
        
        raw_data = {
            "text": "Test lyrics",
            "source": "file", 
            "filepath": "/path/to/file.txt"
        }
        
        mock_segments = [Mock(), Mock()]
        with patch.object(file_provider, '_create_segments_with_words', return_value=mock_segments):
            file_provider._convert_result_format(raw_data)
            
            file_provider.logger.debug.assert_any_call(f"Converting raw data to LyricsData format: {raw_data}")
            file_provider.logger.debug.assert_any_call(f"Created LyricsData object with {len(mock_segments)} segments")

    def test_inheritance_from_base_provider(self, config_with_file, mock_logger):
        """Test that FileProvider correctly inherits from BaseLyricsProvider."""
        from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider
        
        provider = FileProvider(config_with_file, mock_logger)
        assert isinstance(provider, BaseLyricsProvider)

    def test_file_size_logging(self, file_provider, temp_lyrics_file):
        """Test that file size is logged correctly."""
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process.return_value = "Content"
            mock_processor_class.return_value = mock_processor
            
            file_provider._fetch_data_from_source("Artist", "Title")
            
            # Verify file size was logged
            expected_size = Path(temp_lyrics_file).stat().st_size
            file_provider.logger.debug.assert_any_call(f"File size: {expected_size} bytes")

    def test_processor_initialization_with_logger_handlers(self, temp_lyrics_file):
        """Test processor initialization when logger has handlers."""
        # Create a proper mock logger with handlers that has the formatter attribute
        mock_logger = Mock(spec=logging.Logger)
        mock_logger.getEffectiveLevel.return_value = logging.INFO
        mock_handler = Mock()
        mock_handler.formatter = "test_formatter"
        mock_logger.handlers = [mock_handler]
        
        config = LyricsProviderConfig(lyrics_file=temp_lyrics_file)
        provider = FileProvider(config, mock_logger)
        
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process.return_value = "Content"
            mock_processor_class.return_value = mock_processor
            
            provider._fetch_data_from_source("Artist", "Title")
            
            # Verify processor was initialized with logger formatter
            call_args = mock_processor_class.call_args[1]
            assert call_args["log_formatter"] == "test_formatter"

    def test_processor_initialization_without_logger_handlers(self, temp_lyrics_file):
        """Test processor initialization when logger has no handlers."""
        # Create a proper mock logger without handlers  
        mock_logger = Mock(spec=logging.Logger)
        mock_logger.getEffectiveLevel.return_value = logging.INFO
        mock_logger.handlers = []
        
        config = LyricsProviderConfig(lyrics_file=temp_lyrics_file)
        provider = FileProvider(config, mock_logger)
        
        with patch('lyrics_transcriber.lyrics.file_provider.KaraokeLyricsProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process.return_value = "Content"
            mock_processor_class.return_value = mock_processor
            
            provider._fetch_data_from_source("Artist", "Title")
            
            # Verify processor was initialized with None formatter
            call_args = mock_processor_class.call_args[1]
            assert call_args["log_formatter"] is None 