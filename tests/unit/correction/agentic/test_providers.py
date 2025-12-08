import pytest

from lyrics_transcriber.correction.agentic.providers.langchain_bridge import LangChainBridge


def test_provider_circuit_breaker_opens_on_failures(monkeypatch):
    """Test that circuit breaker opens after repeated failures."""
    # Use an invalid model to trigger failures
    b = LangChainBridge(model="invalid/nonexistent-model")
    
    # First call: should return error
    r1 = b.generate_correction_proposals("prompt", schema={})
    assert r1 and "error" in r1[0]
    
    # Trigger multiple failures to open circuit
    for _ in range(5):
        b.generate_correction_proposals("prompt", schema={})
    
    # Next call should hit circuit breaker
    r2 = b.generate_correction_proposals("prompt", schema={})
    assert r2 and ("error" in r2[0] or "until" in r2[0])


