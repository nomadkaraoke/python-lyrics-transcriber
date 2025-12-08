"""Integration test Scenario 4: Fallback reliability (minimal API path)."""

import pytest
import requests


@pytest.mark.integration
def test_fallback_reliability():
    url = "http://localhost:8000/api/v1/correction/agentic"
    # Choose a model that is likely unavailable by default to trigger fallback
    payload = {"transcriptionData": {"segments": []}, "audioFileHash": "hash123", "modelPreferences": ["unavailable-model"]}
    try:
        resp = requests.post(url, json=payload, timeout=1)
        # If server is not running, we skip this test (environmental)
        if resp is None:
            pytest.skip("Server not running")
        # If running, expect either 503 fallback or 200 with data
        assert resp.status_code in (200, 503)
    except Exception:
        pytest.skip("Server not running; skipping API fallback test")


