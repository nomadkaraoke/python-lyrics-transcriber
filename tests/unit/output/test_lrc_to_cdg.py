import pytest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call
from argparse import Namespace

from lyrics_transcriber.output.lrc_to_cdg import cli_main


class TestLrcToCdg:
    """Test cases for the lrc_to_cdg module."""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary test files."""
        lrc_file = tmp_path / "test.lrc"
        lrc_file.write_text("[00:10.00]Hello world\n[00:15.00]Test lyrics\n")
        
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        style_config = {
            "cdg": {
                "background_color": "#000000",
                "text_color": "#FFFFFF"
            }
        }
        style_file = tmp_path / "style.json"
        style_file.write_text(json.dumps(style_config))
        
        return {
            "lrc": str(lrc_file),
            "audio": str(audio_file),
            "style": str(style_file)
        }

    def test_cli_main_success(self, temp_files):
        """Test successful CLI execution."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", temp_files["style"]
        ]
        
        mock_generator = Mock()
        mock_generator.generate_cdg_from_lrc.return_value = ("test.cdg", "test.mp3", "test.zip")
        
        with patch('sys.argv', test_args):
            with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator', return_value=mock_generator):
                cli_main()
                
                mock_generator.generate_cdg_from_lrc.assert_called_once_with(
                    lrc_file=temp_files["lrc"],
                    audio_file=temp_files["audio"],
                    title="Test Song",
                    artist="Test Artist",
                    cdg_styles={"background_color": "#000000", "text_color": "#FFFFFF"}
                )

    def test_cli_main_missing_style_file(self, temp_files):
        """Test CLI with missing style configuration file."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", "/nonexistent/style.json"
        ]
        
        with patch('sys.argv', test_args):
            with patch('sys.exit') as mock_exit:
                cli_main()
                mock_exit.assert_called_with(1)

    def test_cli_main_invalid_json(self, temp_files, tmp_path):
        """Test CLI with invalid JSON in style file."""
        invalid_style_file = tmp_path / "invalid.json"
        invalid_style_file.write_text("invalid json content")
        
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", str(invalid_style_file)
        ]
        
        with patch('sys.argv', test_args):
            with patch('sys.exit') as mock_exit:
                cli_main()
                mock_exit.assert_called_with(1)

    def test_cli_main_invalid_style_config(self, temp_files):
        """Test CLI with invalid style configuration."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", temp_files["style"]
        ]
        
        mock_generator = Mock()
        mock_generator.generate_cdg_from_lrc.side_effect = ValueError("Invalid style config")
        
        with patch('sys.argv', test_args):
            with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator', return_value=mock_generator):
                with patch('sys.exit') as mock_exit:
                    cli_main()
                    mock_exit.assert_called_with(1)

    def test_cli_main_generation_error(self, temp_files):
        """Test CLI with CDG generation error."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", temp_files["style"]
        ]
        
        mock_generator = Mock()
        mock_generator.generate_cdg_from_lrc.side_effect = Exception("Generation failed")
        
        with patch('sys.argv', test_args):
            with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator', return_value=mock_generator):
                with patch('sys.exit') as mock_exit:
                    cli_main()
                    mock_exit.assert_called_with(1)

    def test_cli_argument_parsing(self, temp_files):
        """Test that CLI correctly parses all required arguments."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "My Song Title",
            "--artist", "My Artist Name",
            "--style_params_json", temp_files["style"]
        ]
        
        mock_generator = Mock()
        mock_generator.generate_cdg_from_lrc.return_value = ("test.cdg", "test.mp3", "test.zip")
        
        with patch('sys.argv', test_args):
            with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator', return_value=mock_generator):
                cli_main()
                
                # Verify the generator was called with correct parameters
                call_args = mock_generator.generate_cdg_from_lrc.call_args
                assert call_args[1]['lrc_file'] == temp_files["lrc"]
                assert call_args[1]['audio_file'] == temp_files["audio"]
                assert call_args[1]['title'] == "My Song Title"
                assert call_args[1]['artist'] == "My Artist Name"

    def test_logging_configuration(self, temp_files):
        """Test that logging is configured correctly."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", temp_files["style"]
        ]
        
        mock_generator = Mock()
        mock_generator.generate_cdg_from_lrc.return_value = ("test.cdg", "test.mp3", "test.zip")
        
        with patch('sys.argv', test_args):
            with patch('logging.basicConfig') as mock_logging:
                with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator', return_value=mock_generator):
                    cli_main()
                    
                    # Verify logging was configured
                    mock_logging.assert_called_once()
                    call_args = mock_logging.call_args
                    assert call_args[1]['level'] == 10  # DEBUG level
                    assert 'format' in call_args[1]

    def test_output_directory_creation(self, temp_files):
        """Test that output directory is set correctly."""
        test_args = [
            "lrc_to_cdg.py",
            temp_files["lrc"],
            temp_files["audio"],
            "--title", "Test Song",
            "--artist", "Test Artist",
            "--style_params_json", temp_files["style"]
        ]
        
        with patch('sys.argv', test_args):
            with patch('lyrics_transcriber.output.lrc_to_cdg.CDGGenerator') as mock_cdg_class:
                mock_generator = Mock()
                mock_generator.generate_cdg_from_lrc.return_value = ("test.cdg", "test.mp3", "test.zip")
                mock_cdg_class.return_value = mock_generator
                
                cli_main()
                
                # Verify CDGGenerator was initialized with correct output directory
                expected_output_dir = str(Path(temp_files["lrc"]).parent)
                mock_cdg_class.assert_called_once()
                call_args = mock_cdg_class.call_args
                assert call_args[1]['output_dir'] == expected_output_dir 