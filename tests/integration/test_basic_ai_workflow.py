"""Integration test Scenario 1: Basic AI correction workflow (minimal path)."""

import pytest

from lyrics_transcriber.correction.agentic.agent import AgenticCorrector
from lyrics_transcriber.correction.agentic.providers.bridge import LiteLLMBridge


@pytest.mark.integration
def test_basic_ai_correction_workflow(monkeypatch):
    # Stub provider to avoid network calls; return a valid proposal list
    def fake_generate(prompt, schema):
        return [{
            "word_id": "w1",
            "action": "ReplaceWord",
            "replacement_text": "world",
            "confidence": 0.9,
            "reason": "spelling correction"
        }]

    monkeypatch.setattr(LiteLLMBridge, "generate_correction_proposals", lambda self, prompt, schema: fake_generate(prompt, schema))

    agent = AgenticCorrector(model="dummy")
    proposals = agent.propose("Fix spelling errors in 'wurld'.")

    assert proposals, "Expected at least one correction proposal"
    assert proposals[0].replacement_text == "world"


