import logging
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from lyrics_transcriber.types import CorrectionResult, WordCorrection, LyricsSegment
import time
import os
import urllib.parse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socket
import hashlib
from lyrics_transcriber.core.config import OutputConfig
import uvicorn
import webbrowser
from threading import Thread

logger = logging.getLogger(__name__)


class ReviewServer:
    """Handles the review process through a web interface."""

    def __init__(
        self,
        correction_result: CorrectionResult,
        output_config: OutputConfig,
        audio_filepath: str,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the review server."""
        self.correction_result = correction_result
        self.output_config = output_config
        self.audio_filepath = audio_filepath
        self.logger = logger or logging.getLogger(__name__)
        self.review_completed = False

        # Create FastAPI instance and configure
        self.app = FastAPI()
        self._configure_cors()
        self._register_routes()
        self._mount_frontend()

    def _configure_cors(self) -> None:
        """Configure CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[f"http://localhost:{port}" for port in range(3000, 5174)]
            + [f"http://127.0.0.1:{port}" for port in range(3000, 5174)],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _mount_frontend(self) -> None:
        """Mount the frontend static files."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.abspath(os.path.join(current_dir, "../frontend/dist"))

        if not os.path.exists(frontend_dir):
            raise FileNotFoundError(f"Frontend assets not found at {frontend_dir}")

        self.app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    def _register_routes(self) -> None:
        """Register API routes."""
        self.app.add_api_route("/api/correction-data", self.get_correction_data, methods=["GET"])
        self.app.add_api_route("/api/complete", self.complete_review, methods=["POST"])
        self.app.add_api_route("/api/preview-video", self.generate_preview_video, methods=["POST"])
        self.app.add_api_route("/api/preview-video/{preview_hash}", self.get_preview_video, methods=["GET"])
        self.app.add_api_route("/api/audio/{audio_hash}", self.get_audio, methods=["GET"])
        self.app.add_api_route("/api/ping", self.ping, methods=["GET"])

    async def get_correction_data(self):
        """Get the correction data."""
        return self.correction_result.to_dict()

    async def complete_review(self, updated_data: Dict[str, Any] = Body(...)):
        """Complete the review process."""
        try:
            self.correction_result.corrections = [
                WordCorrection(
                    original_word=c.get("original_word", ""),
                    corrected_word=c.get("corrected_word", ""),
                    original_position=c.get("original_position", 0),
                    source=c.get("source", "review"),
                    reason=c.get("reason", "manual_review"),
                    segment_index=c.get("segment_index", 0),
                    confidence=c.get("confidence"),
                    alternatives=c.get("alternatives", {}),
                    is_deletion=c.get("is_deletion", False),
                    split_index=c.get("split_index"),
                    split_total=c.get("split_total"),
                    corrected_position=c.get("corrected_position"),
                    reference_positions=c.get("reference_positions"),
                    length=c.get("length", 1),
                    handler=c.get("handler"),
                    word_id=c.get("word_id"),
                    corrected_word_id=c.get("corrected_word_id"),
                )
                for c in updated_data["corrections"]
            ]
            self.correction_result.corrected_segments = [LyricsSegment.from_dict(s) for s in updated_data["corrected_segments"]]
            self.correction_result.corrections_made = len(self.correction_result.corrections)

            self.review_completed = True
            return {"status": "success"}

        except Exception as e:
            self.logger.error(f"Failed to update correction data: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def ping(self):
        """Simple ping endpoint for testing."""
        return {"status": "ok"}

    async def get_audio(self, audio_hash: str):
        """Stream the audio file."""
        try:
            if (
                not self.audio_filepath
                or not os.path.exists(self.audio_filepath)
                or not self.correction_result.metadata
                or self.correction_result.metadata.get("audio_hash") != audio_hash
            ):
                raise FileNotFoundError("Audio file not found")

            return FileResponse(self.audio_filepath, media_type="audio/mpeg", filename=os.path.basename(self.audio_filepath))
        except Exception as e:
            raise HTTPException(status_code=404, detail="Audio file not found")

    async def generate_preview_video(self, updated_data: Dict[str, Any] = Body(...)):
        """Generate a preview video with the current corrections."""
        try:
            # Preview video generation is not implemented yet
            self.logger.info("Preview video generation requested but not implemented")
            return {"status": "error", "message": "Preview video generation not implemented"}
        except Exception as e:
            self.logger.error(f"Failed to generate preview video: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_preview_video(self, preview_hash: str):
        """Stream the preview video."""
        raise HTTPException(status_code=404, detail="Preview video not found")

    def start(self) -> CorrectionResult:
        """Start the review server and wait for completion."""
        # Generate audio hash if audio file exists
        if self.audio_filepath and os.path.exists(self.audio_filepath):
            with open(self.audio_filepath, "rb") as f:
                audio_hash = hashlib.md5(f.read()).hexdigest()
            if not self.correction_result.metadata:
                self.correction_result.metadata = {}
            self.correction_result.metadata["audio_hash"] = audio_hash

        # Wait for port 8000 to become available
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", 8000))
                break
            except OSError:
                time.sleep(10)

        # Start server
        config = uvicorn.Config(self.app, host="127.0.0.1", port=8000)
        server = uvicorn.Server(config)
        server_thread = Thread(target=server.run, daemon=True)
        server_thread.start()
        time.sleep(1)

        # Open browser
        base_api_url = "http://localhost:8000/api"
        encoded_api_url = urllib.parse.quote(base_api_url, safe="")
        audio_hash_param = (
            f"&audioHash={self.correction_result.metadata.get('audio_hash', '')}"
            if self.correction_result.metadata and "audio_hash" in self.correction_result.metadata
            else ""
        )
        webbrowser.open(f"http://localhost:8000?baseApiUrl={encoded_api_url}{audio_hash_param}")

        # Wait for review to complete
        while not self.review_completed:
            time.sleep(0.1)

        server.should_exit = True
        server_thread.join(timeout=5)

        return self.correction_result
