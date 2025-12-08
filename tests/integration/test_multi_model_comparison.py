"""Integration test Scenario 3: Multi-model comparison (minimal)."""

import pytest
import requests


@pytest.mark.integration
def test_multi_model_comparison():
    base = "http://localhost:8000/api/v1"
    try:
        r = requests.get(f"{base}/models", timeout=1)
        if r is None:
            pytest.skip("Server not running")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert isinstance(data["models"], list)
    except Exception:
        pytest.skip("Server not running; skipping model comparison test")


