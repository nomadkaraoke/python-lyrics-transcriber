import logging
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from ..types import CorrectionResult
import time
import subprocess
import os
import signal
import atexit

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


def start_vite_server():
    """Start the Vite development server."""
    global vite_process

    # Get the path to the lyrics-analyzer directory relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vite_dir = os.path.abspath(os.path.join(current_dir, "../../lyrics-analyzer"))

    logger.info(f"Starting Vite dev server in {vite_dir}")

    # Start the Vite dev server
    vite_process = subprocess.Popen(["npm", "run", "dev"], cwd=vite_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Register cleanup function to kill Vite server on exit
    atexit.register(lambda: vite_process.terminate() if vite_process else None)

    # Wait a bit for the server to start
    time.sleep(2)  # Adjust this if needed

    return vite_process


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
        updated_data: The complete correction result data with any modifications
    """
    global review_completed, current_review

    logger.info("Received updated correction data")

    try:
        # Update the current review with modified data
        # We use from_dict to ensure the data is properly structured
        current_review = CorrectionResult.from_dict(updated_data)
        logger.info(f"Successfully updated correction data with {len(current_review.corrections)} corrections")

        review_completed = True
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update correction data: {str(e)}")
        return {"status": "error", "message": str(e)}


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

    global current_review, review_completed
    current_review = correction_result
    review_completed = False

    logger.info("Starting review server...")

    # Start Vite dev server
    vite_proc = start_vite_server()
    logger.info("Vite dev server started")

    # Start FastAPI server in a separate thread
    server_thread = Thread(target=uvicorn.run, args=(app,), kwargs={"host": "127.0.0.1", "port": 8000, "log_level": "info"}, daemon=True)
    server_thread.start()
    logger.info("Server thread started")

    # Open browser
    webbrowser.open("http://localhost:5173")
    logger.info("Opened browser for review")

    # Wait for review to complete
    start_time = time.time()
    while not review_completed:
        time.sleep(0.1)
        if time.time() - start_time > 300:  # 5 minute timeout
            logger.warning("Review timed out after 5 minutes")
            break

    # Clean up Vite server
    if vite_proc:
        vite_proc.terminate()
        try:
            vite_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite_proc.kill()

    logger.info("Review completed, returning results")
    return current_review
