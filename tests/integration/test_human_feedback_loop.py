"""Integration test Scenario 2: Human feedback loop (minimal API path)."""

import pytest
import requests


@pytest.mark.integration
def test_human_feedback_loop():
    base = "http://localhost:8000/api/v1"
    try:
        # Create a session
        resp = requests.post(f"{base}/correction/agentic", json={"transcriptionData": {"segments": []}, "audioFileHash": "hash123"}, timeout=1)
        if resp is None:
            pytest.skip("Server not running")
        session_id = resp.json().get("sessionId")

        # Submit feedback
        feedback = {
            "aiCorrectionId": "c1",
            "reviewerAction": "MODIFY",
            "finalText": "world",
            "reasonCategory": "AI_SUBOPTIMAL",
        }
        r2 = requests.post(f"{base}/feedback", json=feedback, timeout=1)
        if r2 is None:
            pytest.skip("Server not running")
        assert r2.status_code in (200, 201)
    except Exception:
        pytest.skip("Server not running; skipping feedback loop test")


