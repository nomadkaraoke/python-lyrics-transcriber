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
from fastapi.responses import FileResponse, JSONResponse
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
import uuid

try:
    # Optional: used to introspect local models for /api/v1/models
    from lyrics_transcriber.correction.agentic.providers.health import (
        is_ollama_available,
        get_ollama_models,
    )
except Exception:
    def is_ollama_available() -> bool:  # type: ignore
        return False

    def get_ollama_models():  # type: ignore
        return []

try:
    from lyrics_transcriber.correction.agentic.observability.metrics import MetricsAggregator
except Exception:
    MetricsAggregator = None  # type: ignore

try:
    from lyrics_transcriber.correction.agentic.observability.langfuse_integration import (
        setup_langfuse,
        record_metrics as lf_record,
    )
except Exception:
    setup_langfuse = lambda *args, **kwargs: None  # type: ignore
    lf_record = lambda *args, **kwargs: None  # type: ignore

try:
    from lyrics_transcriber.correction.agentic.feedback.store import FeedbackStore
except Exception:
    FeedbackStore = None  # type: ignore

try:
    from lyrics_transcriber.correction.feedback.store import FeedbackStore as NewFeedbackStore
    from lyrics_transcriber.correction.feedback.schemas import CorrectionAnnotation
except Exception:
    NewFeedbackStore = None  # type: ignore
    CorrectionAnnotation = None  # type: ignore


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
        # Initialize optional SQLite store for sessions/feedback (legacy)
        try:
            default_db = os.path.join(self.output_config.cache_dir, "agentic_feedback.sqlite3")
            self._store = FeedbackStore(default_db) if FeedbackStore else None
        except Exception:
            self._store = None
        
        # Initialize new annotation store
        try:
            self._annotation_store = NewFeedbackStore(storage_dir=self.output_config.cache_dir) if NewFeedbackStore else None
        except Exception:
            self._annotation_store = None
        # Metrics aggregator
        self._metrics = MetricsAggregator() if MetricsAggregator else None
        # LangFuse (optional)
        try:
            self._langfuse = setup_langfuse("agentic-corrector")
        except Exception:
            self._langfuse = None

    def _configure_cors(self) -> None:
        """Configure CORS middleware."""
        # Allow localhost development ports and the hosted review UI
        allowed_origins = (
            [f"http://localhost:{port}" for port in range(3000, 5174)]
            + [f"http://127.0.0.1:{port}" for port in range(3000, 5174)]
            + ["https://lyrics.nomadkaraoke.com"]
        )
        
        # Also allow custom review UI URL if set
        custom_ui = os.environ.get("LYRICS_REVIEW_UI_URL", "")
        if custom_ui and custom_ui.lower() != "local" and custom_ui not in allowed_origins:
            allowed_origins.append(custom_ui)
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.exception_handler(HTTPException)
        async def _http_exception_handler(request, exc: HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"error": "HTTPException", "message": exc.detail, "details": {}})

        @self.app.exception_handler(Exception)
        async def _unhandled_exception_handler(request, exc: Exception):
            return JSONResponse(status_code=500, content={"error": "InternalServerError", "message": str(exc), "details": {}})

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

        # Agentic AI v1 endpoints (contract-compliant scaffolds)
        self.app.add_api_route("/api/v1/correction/agentic", self.post_correction_agentic, methods=["POST"])
        self.app.add_api_route("/api/v1/correction/session/{session_id}", self.get_correction_session_v1, methods=["GET"])
        self.app.add_api_route("/api/v1/feedback", self.post_feedback_v1, methods=["POST"])
        self.app.add_api_route("/api/v1/models", self.get_models_v1, methods=["GET"])
        self.app.add_api_route("/api/v1/models", self.put_models_v1, methods=["PUT"])
        self.app.add_api_route("/api/v1/metrics", self.get_metrics_v1, methods=["GET"])
        
        # Annotation endpoints
        self.app.add_api_route("/api/v1/annotations", self.post_annotation, methods=["POST"])
        self.app.add_api_route("/api/v1/annotations/{audio_hash}", self.get_annotations_by_song, methods=["GET"])
        self.app.add_api_route("/api/v1/annotations/stats", self.get_annotation_stats, methods=["GET"])

    async def get_correction_data(self):
        """Get the correction data."""
        return self.correction_result.to_dict()

    # ------------------------------
    # API v1: Agentic AI scaffolds
    # ------------------------------

    @property
    def _session_store(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self, "__session_store"):
            self.__session_store = {}
        return self.__session_store  # type: ignore[attr-defined]

    @property
    def _feedback_store(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self, "__feedback_store"):
            self.__feedback_store = {}
        return self.__feedback_store  # type: ignore[attr-defined]

    @property
    def _model_registry(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self, "__model_registry"):
            # Seed with a few placeholders
            models: Dict[str, Dict[str, Any]] = {}
            # Local models via Ollama
            if is_ollama_available():
                for m in get_ollama_models():
                    mid = m.get("model") or m.get("name") or "ollama-unknown"
                    models[mid] = {
                        "id": mid,
                        "name": mid,
                        "type": "local",
                        "available": True,
                        "responseTimeMs": 0,
                        "costPerToken": 0.0,
                        "accuracy": 0.0,
                    }
            # Cloud placeholders
            for mid in ["anthropic/claude-4-sonnet", "gpt-5", "gemini-2.5-pro"]:
                if mid not in models:
                    models[mid] = {
                        "id": mid,
                        "name": mid,
                        "type": "cloud",
                        "available": False,
                        "responseTimeMs": 0,
                        "costPerToken": 0.0,
                        "accuracy": 0.0,
                    }
            self.__model_registry = models
        return self.__model_registry  # type: ignore[attr-defined]

    async def post_correction_agentic(self, request: Dict[str, Any] = Body(...)):
        """POST /api/v1/correction/agentic
        Minimal scaffold: validates required fields and returns a stub response.
        """
        start_time = time.time()
        if not isinstance(request, dict):
            raise HTTPException(status_code=400, detail="Invalid request body")

        if "transcriptionData" not in request or "audioFileHash" not in request:
            raise HTTPException(status_code=400, detail="Missing required fields: transcriptionData, audioFileHash")

        session_id = str(uuid.uuid4())
        session_record = {
            "id": session_id,
            "audioFileHash": request.get("audioFileHash"),
            "sessionType": "FULL_CORRECTION",
            "aiModelConfig": {"model": (request.get("modelPreferences") or [None])[0]},
            "totalCorrections": 0,
            "acceptedCorrections": 0,
            "humanModifications": 0,
            "sessionDurationMs": 0,
            "accuracyImprovement": 0.0,
            "startedAt": None,
            "completedAt": None,
            "status": "IN_PROGRESS",
        }
        self._session_store[session_id] = session_record
        if self._store:
            try:
                self._store.put_session(session_id, json.dumps(session_record))
            except Exception:
                pass

        # Simulate provider availability based on model preferences
        preferred = (request.get("modelPreferences") or ["unknown"])[0]
        model_entry = self._model_registry.get(preferred)
        if model_entry and not model_entry.get("available", False):
            # Service unavailable → return 503 with fallback details
            from fastapi.responses import JSONResponse
            if self._metrics:
                self._metrics.record_session(preferred, int((time.time() - start_time) * 1000), fallback_used=True)
            content = {
                "corrections": [],
                "fallbackReason": f"Model {preferred} unavailable",
                "originalSystemUsed": "rule-based",
                "processingTimeMs": int((time.time() - start_time) * 1000),
            }
            lf_record(self._langfuse, "post_correction_agentic_fallback", {"model": preferred, **content})
            return JSONResponse(status_code=503, content=content)

        response = {
            "sessionId": session_id,
            "corrections": [],
            "processingTimeMs": int((time.time() - start_time) * 1000),
            "modelUsed": preferred,
            "fallbackUsed": False,
            "accuracyEstimate": 0.0,
        }
        if self._metrics:
            self._metrics.record_session(preferred, response["processingTimeMs"], fallback_used=False)
        lf_record(self._langfuse, "post_correction_agentic", {"model": preferred, **response})
        return response

    async def get_correction_session_v1(self, session_id: str):
        data = self._session_store.get(session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Session not found")
        return data

    async def post_feedback_v1(self, request: Dict[str, Any] = Body(...)):
        if not isinstance(request, dict):
            raise HTTPException(status_code=400, detail="Invalid request body")
        required = ["aiCorrectionId", "reviewerAction", "reasonCategory"]
        if any(k not in request for k in required):
            raise HTTPException(status_code=400, detail="Missing required feedback fields")

        feedback_id = str(uuid.uuid4())
        record = {**request, "id": feedback_id}
        self._feedback_store[feedback_id] = record
        if self._store:
            try:
                self._store.put_feedback(feedback_id, request.get("sessionId"), json.dumps(record))
            except Exception:
                pass
        if self._metrics:
            self._metrics.record_feedback()
        return {"feedbackId": feedback_id, "recorded": True, "learningDataUpdated": False}

    async def get_models_v1(self):
        return {"models": list(self._model_registry.values())}

    async def put_models_v1(self, config: Dict[str, Any] = Body(...)):
        if not isinstance(config, dict) or "modelId" not in config:
            raise HTTPException(status_code=400, detail="Invalid model configuration")
        mid = config["modelId"]
        entry = self._model_registry.get(mid, {
            "id": mid,
            "name": mid,
            "type": "cloud",
            "available": False,
            "responseTimeMs": 0,
            "costPerToken": 0.0,
            "accuracy": 0.0,
        })
        if "enabled" in config:
            entry["available"] = bool(config["enabled"]) or entry.get("available", False)
        if "priority" in config:
            entry["priority"] = config["priority"]
        if "configuration" in config and isinstance(config["configuration"], dict):
            entry["configuration"] = config["configuration"]
        self._model_registry[mid] = entry
        return {"status": "ok"}

    async def get_metrics_v1(self, timeRange: str = "day", sessionId: Optional[str] = None):
        if self._metrics:
            return self._metrics.snapshot(time_range=timeRange, session_id=sessionId)
        # Fallback if metrics unavailable
        return {"timeRange": timeRange, "totalSessions": len(self._session_store), "averageAccuracy": 0.0, "errorReduction": 0.0, "averageProcessingTime": 0, "modelPerformance": {}, "costSummary": {}, "userSatisfaction": 0.0}
    
    # ------------------------------
    # Annotation endpoints
    # ------------------------------
    
    async def post_annotation(self, annotation_data: Dict[str, Any] = Body(...)):
        """Save a correction annotation."""
        if not self._annotation_store or not CorrectionAnnotation:
            raise HTTPException(status_code=501, detail="Annotation system not available")
        
        try:
            # Validate and create annotation
            annotation = CorrectionAnnotation.model_validate(annotation_data)
            
            # Save to store
            success = self._annotation_store.save_annotation(annotation)
            
            if success:
                return {"status": "success", "annotation_id": annotation.annotation_id}
            else:
                raise HTTPException(status_code=500, detail="Failed to save annotation")
                
        except Exception as e:
            self.logger.error(f"Failed to save annotation: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_annotations_by_song(self, audio_hash: str):
        """Get all annotations for a specific song."""
        if not self._annotation_store:
            raise HTTPException(status_code=501, detail="Annotation system not available")
        
        try:
            annotations = self._annotation_store.get_annotations_by_song(audio_hash)
            return {
                "audio_hash": audio_hash,
                "count": len(annotations),
                "annotations": [a.model_dump() for a in annotations]
            }
        except Exception as e:
            self.logger.error(f"Failed to get annotations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_annotation_stats(self):
        """Get aggregated statistics from all annotations."""
        if not self._annotation_store:
            raise HTTPException(status_code=501, detail="Annotation system not available")
        
        try:
            stats = self._annotation_store.get_statistics()
            return stats.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to get annotation statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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
            
            # Use hosted review UI by default, can be overridden with LYRICS_REVIEW_UI_URL env var
            # Set to "local" to use the bundled local frontend instead
            review_ui_url = os.environ.get("LYRICS_REVIEW_UI_URL", "https://lyrics.nomadkaraoke.com")
            if review_ui_url.lower() == "local":
                # Use the bundled local frontend
                browser_url = f"http://localhost:8000?baseApiUrl={encoded_api_url}{audio_hash_param}"
            else:
                # Use the hosted/external review UI
                browser_url = f"{review_ui_url}?baseApiUrl={encoded_api_url}{audio_hash_param}"
            
            self.logger.info(f"Opening review UI: {browser_url}")
            webbrowser.open(browser_url)

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
