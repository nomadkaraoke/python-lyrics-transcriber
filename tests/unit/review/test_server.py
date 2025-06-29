import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import HTTPException

from lyrics_transcriber.review.server import ReviewServer
from lyrics_transcriber.types import CorrectionResult, LyricsSegment, Word, LyricsData, LyricsMetadata
from lyrics_transcriber.core.config import OutputConfig


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_segments():
    """Sample segments for testing."""
    return [
        LyricsSegment(
            id="seg1",
            text="Hello world",
            words=[
                Word(id="w1", text="Hello", start_time=0.0, end_time=1.0),
                Word(id="w2", text="world", start_time=1.0, end_time=2.0),
            ],
            start_time=0.0,
            end_time=2.0,
        )
    ]


@pytest.fixture
def sample_correction_result(sample_segments):
    """Sample correction result for testing."""
    return CorrectionResult(
        original_segments=sample_segments,
        corrected_segments=sample_segments,
        corrections=[],
        corrections_made=0,
        confidence=0.95,
        reference_lyrics={},
        anchor_sequences=[],
        gap_sequences=[],
        resized_segments=sample_segments,
        metadata={"title": "Test Song", "artist": "Test Artist", "audio_hash": "test_hash"},
        correction_steps=[],
        word_id_map={},
        segment_id_map={},
    )


@pytest.fixture
def output_config():
    """Sample output config for testing."""
    return OutputConfig(
        output_dir="/tmp/test",
        cache_dir="/tmp/cache",
        output_styles_json="{}",
        styles={}
    )


@pytest.fixture
def review_server(sample_correction_result, output_config, mock_logger, tmp_path):
    """Create a ReviewServer instance for testing."""
    # Create a temporary audio file
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake audio data")
    
    # Mock the frontend directory to exist
    with patch('os.path.exists', return_value=True):
        server = ReviewServer(
            correction_result=sample_correction_result,
            output_config=output_config,
            audio_filepath=str(audio_file),
            logger=mock_logger,
        )
    return server


class TestReviewServer:
    """Test cases for ReviewServer class."""

    def test_init(self, sample_correction_result, output_config, mock_logger, tmp_path):
        """Test ReviewServer initialization."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        with patch('os.path.exists', return_value=True):
            server = ReviewServer(
                correction_result=sample_correction_result,
                output_config=output_config,
                audio_filepath=str(audio_file),
                logger=mock_logger,
            )
        
        assert server.correction_result == sample_correction_result
        assert server.output_config == output_config
        assert server.audio_filepath == str(audio_file)
        assert server.logger == mock_logger
        assert not server.review_completed

    def test_init_without_frontend_dir(self, sample_correction_result, output_config, mock_logger, tmp_path):
        """Test ReviewServer initialization when frontend directory doesn't exist."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Frontend assets not found"):
                ReviewServer(
                    correction_result=sample_correction_result,
                    output_config=output_config,
                    audio_filepath=str(audio_file),
                    logger=mock_logger,
                )

    @pytest.mark.asyncio
    async def test_get_correction_data(self, review_server):
        """Test getting correction data."""
        with patch.object(review_server.correction_result, 'to_dict', return_value={"test": "data"}):
            result = await review_server.get_correction_data()
            assert result == {"test": "data"}

    def test_update_correction_result(self, review_server, sample_segments):
        """Test updating correction result."""
        updated_data = {
            "corrections": [{
                "original_word": "test",
                "corrected_word": "fixed",
                "original_position": 0,
                "source": "manual",
                "reason": "test",
                "segment_index": 0,
            }],
            "corrected_segments": [{
                "id": "seg1",
                "text": "Hello fixed",
                "words": [
                    {"id": "w1", "text": "Hello", "start_time": 0.0, "end_time": 1.0},
                    {"id": "w2", "text": "fixed", "start_time": 1.0, "end_time": 2.0},
                ],
                "start_time": 0.0,
                "end_time": 2.0,
            }]
        }
        
        result = review_server._update_correction_result(review_server.correction_result, updated_data)
        
        assert len(result.corrections) == 1
        assert result.corrections[0].original_word == "test"
        assert result.corrections[0].corrected_word == "fixed"
        assert len(result.corrected_segments) == 1

    @pytest.mark.asyncio
    async def test_complete_review_success(self, review_server):
        """Test successful review completion."""
        updated_data = {
            "corrections": [],
            "corrected_segments": [{
                "id": "seg1",
                "text": "Hello world",
                "words": [
                    {"id": "w1", "text": "Hello", "start_time": 0.0, "end_time": 1.0},
                    {"id": "w2", "text": "world", "start_time": 1.0, "end_time": 2.0},
                ],
                "start_time": 0.0,
                "end_time": 2.0,
            }]
        }
        
        result = await review_server.complete_review(updated_data)
        
        assert result == {"status": "success"}
        assert review_server.review_completed

    @pytest.mark.asyncio
    async def test_complete_review_error(self, review_server):
        """Test review completion with error."""
        # Invalid data to cause an error
        invalid_data = {"invalid": "data"}
        
        result = await review_server.complete_review(invalid_data)
        
        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_ping(self, review_server):
        """Test ping endpoint."""
        result = await review_server.ping()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_get_audio_success(self, review_server, tmp_path):
        """Test successful audio file retrieval."""
        # Create a test audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        review_server.audio_filepath = str(audio_file)
        
        # Mock the metadata to have the correct hash
        review_server.correction_result.metadata = {"audio_hash": "test_hash"}
        
        with patch('os.path.exists', return_value=True):
            result = await review_server.get_audio("test_hash")
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_audio_not_found(self, review_server):
        """Test audio file retrieval when file not found."""
        with pytest.raises(HTTPException) as exc_info:
            await review_server.get_audio("nonexistent_hash")
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_preview_video_success(self, review_server):
        """Test successful preview video generation."""
        updated_data = {
            "corrections": [],
            "corrected_segments": [{
                "id": "seg1",
                "text": "Hello world",
                "words": [
                    {"id": "w1", "text": "Hello", "start_time": 0.0, "end_time": 1.0},
                    {"id": "w2", "text": "world", "start_time": 1.0, "end_time": 2.0},
                ],
                "start_time": 0.0,
                "end_time": 2.0,
            }]
        }
        
        mock_output_generator = Mock()
        mock_outputs = Mock()
        mock_outputs.video = "/path/to/preview.mp4"
        mock_output_generator.generate_outputs.return_value = mock_outputs
        
        with patch('lyrics_transcriber.review.server.OutputGenerator', return_value=mock_output_generator):
            result = await review_server.generate_preview_video(updated_data)
            
            assert result["status"] == "success"
            assert "preview_hash" in result

    @pytest.mark.asyncio
    async def test_generate_preview_video_error(self, review_server):
        """Test preview video generation with error."""
        updated_data = {"invalid": "data"}
        
        with pytest.raises(HTTPException) as exc_info:
            await review_server.generate_preview_video(updated_data)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_preview_video_success(self, review_server, tmp_path):
        """Test successful preview video retrieval."""
        # Set up preview video
        preview_hash = "test_hash"
        video_file = tmp_path / "preview.mp4"
        video_file.write_bytes(b"fake video data")
        
        review_server.preview_videos = {preview_hash: str(video_file)}
        
        with patch('os.path.exists', return_value=True):
            result = await review_server.get_preview_video(preview_hash)
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_preview_video_not_found(self, review_server):
        """Test preview video retrieval when not found."""
        with pytest.raises(HTTPException) as exc_info:
            await review_server.get_preview_video("nonexistent_hash")
        
        assert exc_info.value.status_code == 404

    def test_create_lyrics_data_from_text(self, review_server):
        """Test creating LyricsData from text."""
        text = "Line one\nLine two\nLine three"
        source = "manual"
        
        result = review_server._create_lyrics_data_from_text(text, source)
        
        assert isinstance(result, LyricsData)
        assert len(result.segments) == 3
        assert result.source == source
        assert result.metadata.source == source

    def test_fastapi_app_creation(self, review_server):
        """Test that FastAPI app is created with correct routes."""
        app = review_server.app
        
        # Check that routes are registered
        route_paths = [route.path for route in app.routes]
        
        expected_paths = [
            "/api/correction-data",
            "/api/complete",
            "/api/preview-video",
            "/api/audio",
            "/api/ping",
            "/api/handlers",
            "/api/add-lyrics"
        ]
        
        for path in expected_paths:
            found = any(path in route_path for route_path in route_paths)
            assert found, f"Route {path} not found in {route_paths}"


class TestReviewServerIntegration:
    """Integration tests for ReviewServer."""

    def test_cors_configuration(self, review_server):
        """Test CORS middleware configuration."""
        # Check that CORS middleware is added
        middleware_types = [type(middleware) for middleware in review_server.app.user_middleware]
        
        # The exact check depends on how FastAPI structures middleware
        # This is a basic check that middleware exists
        assert len(review_server.app.user_middleware) > 0 