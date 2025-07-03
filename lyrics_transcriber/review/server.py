import logging
import socket
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from lyrics_transcriber.types import CorrectionResult, WordCorrection, LyricsSegment, LyricsData, LyricsMetadata, Word
import time
import os
import urllib.parse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import hashlib
from lyrics_transcriber.core.config import OutputConfig
import uvicorn
import webbrowser
from threading import Thread
from lyrics_transcriber.output.generator import OutputGenerator
import json
from lyrics_transcriber.correction.corrector import LyricsCorrector
from lyrics_transcriber.types import TranscriptionResult, TranscriptionData
from lyrics_transcriber.lyrics.user_input_provider import UserInputProvider
from lyrics_transcriber.correction.operations import CorrectionOperations


class ReviewServer:
    """Handles the review process through a web interface."""

    def __init__(
        self,
        correction_result: CorrectionResult,
        output_config: OutputConfig,
        audio_filepath: str,
        logger: logging.Logger,
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
        from lyrics_transcriber.frontend import get_frontend_assets_dir
        frontend_dir = get_frontend_assets_dir()

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
        self.app.add_api_route("/api/handlers", self.update_handlers, methods=["POST"])
        self.app.add_api_route("/api/add-lyrics", self.add_lyrics, methods=["POST"])

    async def get_correction_data(self):
        """Get the correction data."""
        return self.correction_result.to_dict()

    def _update_correction_result(self, base_result: CorrectionResult, updated_data: Dict[str, Any]) -> CorrectionResult:
        """Update a CorrectionResult with new correction data."""
        return CorrectionOperations.update_correction_result_with_data(base_result, updated_data)

    async def complete_review(self, updated_data: Dict[str, Any] = Body(...)):
        """Complete the review process."""
        try:
            self.correction_result = self._update_correction_result(self.correction_result, updated_data)
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
            # Use shared operation for preview generation
            result = CorrectionOperations.generate_preview_video(
                correction_result=self.correction_result,
                updated_data=updated_data,
                output_config=self.output_config,
                audio_filepath=self.audio_filepath,
                logger=self.logger
            )
            
            # Store the path for later retrieval
            if not hasattr(self, "preview_videos"):
                self.preview_videos = {}
            self.preview_videos[result["preview_hash"]] = result["video_path"]

            return {"status": "success", "preview_hash": result["preview_hash"]}

        except Exception as e:
            self.logger.error(f"Failed to generate preview video: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_preview_video(self, preview_hash: str):
        """Stream the preview video."""
        try:
            if not hasattr(self, "preview_videos") or preview_hash not in self.preview_videos:
                raise FileNotFoundError("Preview video not found")

            video_path = self.preview_videos[preview_hash]
            if not os.path.exists(video_path):
                raise FileNotFoundError("Preview video file not found")

            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=os.path.basename(video_path),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except Exception as e:
            self.logger.error(f"Failed to stream preview video: {str(e)}")
            raise HTTPException(status_code=404, detail="Preview video not found")

    async def update_handlers(self, enabled_handlers: List[str] = Body(...)):
        """Update enabled correction handlers and rerun correction."""
        try:
            # Use shared operation for handler updates
            self.correction_result = CorrectionOperations.update_correction_handlers(
                correction_result=self.correction_result,
                enabled_handlers=enabled_handlers,
                cache_dir=self.output_config.cache_dir,
                logger=self.logger
            )

            return {"status": "success", "data": self.correction_result.to_dict()}
        except Exception as e:
            self.logger.error(f"Failed to update handlers: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def _create_lyrics_data_from_text(self, text: str, source: str) -> LyricsData:
        """Create LyricsData object from plain text lyrics."""
        self.logger.info(f"Creating LyricsData for source '{source}'")

        # Split text into lines and create segments
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        self.logger.info(f"Found {len(lines)} non-empty lines in input text")

        segments = []
        for i, line in enumerate(lines):
            # Split line into words
            word_texts = line.strip().split()
            words = []

            for j, word_text in enumerate(word_texts):
                word = Word(
                    id=f"manual_{source}_word_{i}_{j}",  # Create unique ID for each word
                    text=word_text,
                    start_time=0.0,  # Placeholder timing
                    end_time=0.0,
                    confidence=1.0,  # Reference lyrics are considered ground truth
                    created_during_correction=False,
                )
                words.append(word)

            segments.append(
                LyricsSegment(
                    id=f"manual_{source}_{i}",
                    text=line,
                    words=words,  # Now including the word objects
                    start_time=0.0,  # Placeholder timing
                    end_time=0.0,
                )
            )

        # Create metadata
        self.logger.info("Creating metadata for LyricsData")
        metadata = LyricsMetadata(
            source=source,
            track_name=self.correction_result.metadata.get("title", "") or "",
            artist_names=self.correction_result.metadata.get("artist", "") or "",
            is_synced=False,
            lyrics_provider="manual",
            lyrics_provider_id="",
            album_name=None,
            duration_ms=None,
            explicit=None,
            language=None,
            provider_metadata={},
        )
        self.logger.info(f"Created metadata: {metadata}")

        lyrics_data = LyricsData(segments=segments, metadata=metadata, source=source)
        self.logger.info(f"Created LyricsData with {len(segments)} segments and {sum(len(s.words) for s in segments)} total words")

        return lyrics_data

    async def add_lyrics(self, data: Dict[str, str] = Body(...)):
        """Add new lyrics source and rerun correction."""
        try:
            source = data.get("source", "").strip()
            lyrics_text = data.get("lyrics", "").strip()

            self.logger.info(f"Received request to add lyrics source '{source}' with {len(lyrics_text)} characters")

            # Use shared operation for adding lyrics source
            self.correction_result = CorrectionOperations.add_lyrics_source(
                correction_result=self.correction_result,
                source=source,
                lyrics_text=lyrics_text,
                cache_dir=self.output_config.cache_dir,
                logger=self.logger
            )

            return {"status": "success", "data": self.correction_result.to_dict()}

        except ValueError as e:
            # Convert ValueError to HTTPException for API consistency
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to add lyrics: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    def start(self) -> CorrectionResult:
        """Start the review server and wait for completion."""
        # Generate audio hash if audio file exists
        if self.audio_filepath and os.path.exists(self.audio_filepath):
            with open(self.audio_filepath, "rb") as f:
                audio_hash = hashlib.md5(f.read()).hexdigest()
            if not self.correction_result.metadata:
                self.correction_result.metadata = {}
            self.correction_result.metadata["audio_hash"] = audio_hash

        server = None
        server_thread = None
        sock = None

        try:
            # Check port availability
            while True:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", 8000)) == 0:
                    # Port is in use, get process info
                    process_info = ""
                    if os.name != "nt":  # Unix-like systems
                        try:
                            process_info = os.popen("lsof -i:8000").read().strip()
                        except:
                            pass

                    self.logger.warning(
                        f"Port 8000 is in use. Waiting for it to become available...\n"
                        f"Process using port 8000:\n{process_info}\n"
                        f"To manually free the port, you can run: lsof -ti:8000 | xargs kill -9"
                    )
                    sock.close()
                    time.sleep(30)
                else:
                    sock.close()
                    break

            # Start server
            config = uvicorn.Config(self.app, host="127.0.0.1", port=8000, log_level="error")
            server = uvicorn.Server(config)
            server_thread = Thread(target=server.run, daemon=True)
            server_thread.start()
            time.sleep(0.5)  # Reduced wait time

            # Open browser and wait for completion
            base_api_url = "http://localhost:8000/api"
            encoded_api_url = urllib.parse.quote(base_api_url, safe="")
            audio_hash_param = (
                f"&audioHash={self.correction_result.metadata.get('audio_hash', '')}"
                if self.correction_result.metadata and "audio_hash" in self.correction_result.metadata
                else ""
            )
            webbrowser.open(f"http://localhost:8000?baseApiUrl={encoded_api_url}{audio_hash_param}")

            while not self.review_completed:
                time.sleep(0.1)

            return self.correction_result

        except KeyboardInterrupt:
            self.logger.info("Received interrupt, shutting down server...")
            raise
        except Exception as e:
            self.logger.error(f"Error during review server operation: {e}")
            raise
        finally:
            # Comprehensive cleanup
            if sock:
                try:
                    sock.close()
                except:
                    pass

            if server:
                server.should_exit = True

            if server_thread and server_thread.is_alive():
                server_thread.join(timeout=1)

            # Force cleanup any remaining server resources
            try:
                import multiprocessing.resource_tracker

                multiprocessing.resource_tracker._resource_tracker = None
            except:
                pass
