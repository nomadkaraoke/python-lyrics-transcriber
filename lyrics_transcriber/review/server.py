import logging
import socket
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from lyrics_transcriber.types import CorrectionResult, WordCorrection, LyricsSegment
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
        self.app.add_api_route("/api/handlers", self.update_handlers, methods=["POST"])

    async def get_correction_data(self):
        """Get the correction data."""
        return self.correction_result.to_dict()

    def _update_correction_result(self, base_result: CorrectionResult, updated_data: Dict[str, Any]) -> CorrectionResult:
        """Update a CorrectionResult with new correction data."""
        return CorrectionResult(
            corrections=[
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
            ],
            corrected_segments=[LyricsSegment.from_dict(s) for s in updated_data["corrected_segments"]],
            # Copy existing fields from the base result
            original_segments=base_result.original_segments,
            corrections_made=len(updated_data["corrections"]),
            confidence=base_result.confidence,
            reference_lyrics=base_result.reference_lyrics,
            anchor_sequences=base_result.anchor_sequences,
            gap_sequences=base_result.gap_sequences,
            resized_segments=None,  # Will be generated if needed
            metadata=base_result.metadata,
            correction_steps=base_result.correction_steps,
            word_id_map=base_result.word_id_map,
            segment_id_map=base_result.segment_id_map,
        )

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
            # Create temporary correction result with updated data
            temp_correction = self._update_correction_result(self.correction_result, updated_data)

            # Generate a unique hash for this preview
            preview_data = json.dumps(updated_data, sort_keys=True).encode("utf-8")
            preview_hash = hashlib.md5(preview_data).hexdigest()[:12]  # Use first 12 chars for shorter filename

            # Initialize output generator with preview settings
            preview_config = OutputConfig(
                output_dir=self.output_config.output_dir,
                cache_dir=self.output_config.cache_dir,
                output_styles_json=self.output_config.output_styles_json,
                video_resolution="360p",  # Force 360p for preview
                styles=self.output_config.styles,
                max_line_length=self.output_config.max_line_length,
            )
            output_generator = OutputGenerator(config=preview_config, logger=self.logger, preview_mode=True)

            # Generate preview outputs with unique prefix
            preview_outputs = output_generator.generate_outputs(
                transcription_corrected=temp_correction,
                lyrics_results={},  # Empty dict since we don't need lyrics results for preview
                output_prefix=f"preview_{preview_hash}",  # Include hash in filename
                audio_filepath=self.audio_filepath,
            )

            if not preview_outputs.video:
                raise ValueError("Preview video generation failed")

            # Store the path for later retrieval
            if not hasattr(self, "preview_videos"):
                self.preview_videos = {}
            self.preview_videos[preview_hash] = preview_outputs.video

            return {"status": "success", "preview_hash": preview_hash}

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
            # Store existing audio hash
            audio_hash = self.correction_result.metadata.get("audio_hash") if self.correction_result.metadata else None

            # Update metadata with new handler configuration
            if not self.correction_result.metadata:
                self.correction_result.metadata = {}
            self.correction_result.metadata["enabled_handlers"] = enabled_handlers

            # Rerun correction with updated handlers
            corrector = LyricsCorrector(cache_dir=self.output_config.cache_dir, enabled_handlers=enabled_handlers, logger=self.logger)

            # Create proper TranscriptionData from original segments
            transcription_data = TranscriptionData(
                segments=self.correction_result.original_segments,
                words=[word for segment in self.correction_result.original_segments for word in segment.words],
                text="\n".join(segment.text for segment in self.correction_result.original_segments),
                source="original",
            )

            # Run correction
            self.correction_result = corrector.run(
                transcription_results=[TranscriptionResult(name="original", priority=1, result=transcription_data)],
                lyrics_results=self.correction_result.reference_lyrics,
                metadata=self.correction_result.metadata,
            )

            # Restore audio hash
            if audio_hash:
                if not self.correction_result.metadata:
                    self.correction_result.metadata = {}
                self.correction_result.metadata["audio_hash"] = audio_hash

            return {"status": "success", "data": self.correction_result.to_dict()}
        except Exception as e:
            self.logger.error(f"Failed to update handlers: {str(e)}")
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
