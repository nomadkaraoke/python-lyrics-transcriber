import logging
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from ..types import CorrectionResult, WordCorrection, LyricsSegment
import time
import subprocess
import os
import atexit
import urllib.parse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for the review process
current_review: Optional[CorrectionResult] = None
review_completed = False
vite_process: Optional[subprocess.Popen] = None
audio_filepath: Optional[str] = None  # Add this new global variable


def start_vite_server():
    """Get path to the built frontend assets."""
    global vite_process  # We'll keep this for backwards compatibility

    # Get the path to the built frontend assets
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.abspath(os.path.join(current_dir, "../frontend/dist"))

    if not os.path.exists(frontend_dir):
        raise FileNotFoundError(f"Frontend assets not found at {frontend_dir}. Ensure the package was built correctly.")

    # Mount the static files
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    logger.info(f"Mounted frontend assets from {frontend_dir}")
    return None  # No process to return since we're serving static files


@app.get("/api/correction-data")
async def get_correction_data():
    """Get the current correction data for review."""
    if current_review is None:
        return {"error": "No review in progress"}
    return current_review.to_dict()


@app.post("/api/complete")
async def complete_review(updated_data: Dict[str, Any] = Body(...)):
    """
    Mark the review as complete and update the correction data.

    Args:
        updated_data: Dictionary containing corrections and corrected_segments
    """
    global review_completed, current_review

    logger.info("Received updated correction data")

    try:
        # Only update the specific fields that were modified
        if current_review is None:
            raise ValueError("No review in progress")

        # Update only the corrections and corrected_segments
        current_review.corrections = [WordCorrection.from_dict(c) for c in updated_data["corrections"]]
        current_review.corrected_segments = [LyricsSegment.from_dict(s) for s in updated_data["corrected_segments"]]
        current_review.corrections_made = len(current_review.corrections)

        logger.info(f"Successfully updated correction data with {len(current_review.corrections)} corrections")

        review_completed = True
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update correction data: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/api/audio")
async def get_audio():
    """Stream the audio file for playback in the browser."""
    if not audio_filepath or not os.path.exists(audio_filepath):
        logger.error(f"Audio file not found at {audio_filepath}")
        return {"error": "Audio file not found"}

    return FileResponse(
        audio_filepath,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes", "Content-Disposition": f"attachment; filename={Path(audio_filepath).name}"},
    )


def start_review_server(correction_result: CorrectionResult) -> CorrectionResult:
    """
    Start the review server and wait for completion.

    Args:
        correction_result: The correction result to review

    Returns:
        The potentially modified correction result after review
    """
    import uvicorn
    import webbrowser
    from threading import Thread
    import signal
    import sys

    global current_review, review_completed, audio_filepath  # Add audio_filepath to globals
    current_review = correction_result
    review_completed = False

    # Get the audio filepath from the correction result's metadata if available
    audio_filepath = correction_result.metadata.get("audio_filepath") if correction_result.metadata else None

    logger.info("Starting review server...")

    # Start Vite dev server (now just mounts static files)
    start_vite_server()
    logger.info("Frontend assets mounted")

    # Create a custom server config
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)

    # Start FastAPI server in a separate thread
    server_thread = Thread(target=server.run, daemon=True)
    server_thread.start()
    logger.info("Server thread started")

    # Open browser - Updated to use port 8000 instead of 5173
    base_api_url = "http://localhost:8000/api"
    encoded_api_url = urllib.parse.quote(base_api_url, safe="")
    webbrowser.open(f"http://localhost:8000?baseApiUrl={encoded_api_url}")
    logger.info("Opened browser for review")

    # Wait for review to complete
    start_time = time.time()
    while not review_completed:
        time.sleep(0.1)

    logger.info("Review completed, shutting down server...")
    server.should_exit = True
    server_thread.join(timeout=5)  # Wait up to 5 seconds for server to shut down

    return current_review
