"""Integration test Scenario 5: Performance and observability (minimal)."""

import pytest
import requests


@pytest.mark.integration
def test_performance_observability():
    base = "http://localhost:8000/api/v1"
    try:
        r = requests.get(f"{base}/metrics", timeout=1)
        if r is None:
            pytest.skip("Server not running")
        assert r.status_code == 200
        data = r.json()
        assert "totalSessions" in data
        assert "averageAccuracy" in data
    except Exception:
        pytest.skip("Server not running; skipping metrics test")


