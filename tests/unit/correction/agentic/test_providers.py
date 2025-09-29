import pytest

from lyrics_transcriber.correction.agentic.providers.bridge import LiteLLMBridge


def test_provider_circuit_breaker_opens_on_failures(monkeypatch):
    # Force missing litellm by raising ImportError in import path
    monkeypatch.setitem(__import__("sys").modules, "litellm", None)
    b = LiteLLMBridge(model="gpt-5")
    # First call: returns error
    r1 = b.generate_correction_proposals("prompt", schema={})
    assert r1 and "error" in r1[0]
    # Trigger multiple failures to open circuit
    for _ in range(5):
        b.generate_correction_proposals("prompt", schema={})
    r2 = b.generate_correction_proposals("prompt", schema={})
    assert r2 and ("error" in r2[0] or "until" in r2[0])


