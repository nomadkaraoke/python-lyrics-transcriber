"""Integration test Scenario 1: Basic AI correction workflow (minimal path)."""

import pytest

from lyrics_transcriber.correction.agentic.agent import AgenticCorrector
from lyrics_transcriber.correction.agentic.providers.base import BaseAIProvider


class MockProvider(BaseAIProvider):
    """Mock provider for testing."""
    
    def name(self) -> str:
        return "mock_provider"
    
    def generate_correction_proposals(self, prompt, schema, session_id=None):
        return [{
            "word_id": "w1",
            "action": "ReplaceWord",
            "replacement_text": "world",
            "confidence": 0.9,
            "reason": "spelling correction"
        }]


@pytest.mark.integration
def test_basic_ai_correction_workflow():
    """Test basic AI correction workflow with mocked provider using dependency injection."""
    # Create mock provider
    mock_provider = MockProvider()
    
    # Inject mock provider (much cleaner than monkeypatching!)
    agent = AgenticCorrector(provider=mock_provider)
    proposals = agent.propose("Fix spelling errors in 'wurld'.")

    assert proposals, "Expected at least one correction proposal"
    assert proposals[0].replacement_text == "world"


