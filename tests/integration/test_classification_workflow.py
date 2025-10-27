"""Integration tests for classification-first agentic correction workflow."""

import pytest
from typing import List, Dict, Any

from lyrics_transcriber.correction.agentic.agent import AgenticCorrector
from lyrics_transcriber.correction.agentic.providers.base import BaseAIProvider
from lyrics_transcriber.correction.agentic.models.schemas import GapCategory, GapClassification


class MockClassificationProvider(BaseAIProvider):
    """Mock provider that returns predefined classifications and proposals."""
    
    def __init__(self, classification_response: Dict[str, Any] = None):
        """Initialize with optional classification response."""
        self.classification_response = classification_response or {
            "gap_id": "gap_1",
            "category": "SOUND_ALIKE",
            "confidence": 0.95,
            "reasoning": "Mock classification",
            "suggested_handler": "sound_alike"
        }
        self.calls = []
    
    def name(self) -> str:
        return "mock_classification_provider"
    
    def generate_correction_proposals(self, prompt: str, schema: Dict[str, Any], session_id: str = None) -> List[Dict[str, Any]]:
        """Return mocked classification based on schema."""
        self.calls.append({"prompt": prompt, "schema": schema, "session_id": session_id})
        
        # Return classification response
        return [self.classification_response]


@pytest.mark.integration
class TestClassificationWorkflow:
    """Test the two-step classification workflow."""
    
    def test_sound_alike_classification_and_handling(self):
        """Test that sound-alike gaps are classified and handled correctly."""
        # Mock provider that classifies as SOUND_ALIKE
        mock = MockClassificationProvider({
            "gap_id": "gap_1",
            "category": "SOUND_ALIKE",
            "confidence": 0.90,
            "reasoning": "Transcription has 'out' but reference shows 'now'",
            "suggested_handler": "sound_alike"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        # Call with gap data
        proposals = agent.propose_for_gap(
            gap_id="gap_1",
            gap_words=[
                {"id": "w1", "text": "out", "start_time": 17.5, "end_time": 18.0}
            ],
            preceding_words="was it worth it? Starting",
            following_words="I'm starting over",
            reference_contexts={
                "genius": "Starting now I'm starting over"
            },
            artist="Test Artist",
            title="Test Song"
        )
        
        # Should get proposals from SoundAlikeHandler
        assert len(proposals) >= 1
        assert proposals[0].gap_category == GapCategory.SOUND_ALIKE
        
        # Handler should either propose replacement or flag for review
        assert proposals[0].action in ["ReplaceWord", "Flag"]
    
    def test_background_vocals_classification_and_handling(self):
        """Test that background vocals are classified and deleted."""
        mock = MockClassificationProvider({
            "gap_id": "gap_2",
            "category": "BACKGROUND_VOCALS",
            "confidence": 0.92,
            "reasoning": "Parenthesized content not in references",
            "suggested_handler": "background_vocals"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_2",
            gap_words=[
                {"id": "w1", "text": "(Big", "start_time": 70.0, "end_time": 70.3},
                {"id": "w2", "text": "business)", "start_time": 70.3, "end_time": 70.8}
            ],
            preceding_words="was it worth it?",
            following_words="Was it worth",
            reference_contexts={
                "genius": "was it worth what you did to big business?"
            }
        )
        
        # Should get delete proposal
        assert len(proposals) == 1
        assert proposals[0].gap_category == GapCategory.BACKGROUND_VOCALS
        assert proposals[0].action == "DeleteWord"
        assert len(proposals[0].word_ids) == 2
    
    def test_punctuation_only_classification(self):
        """Test that punctuation differences return NO_ACTION."""
        mock = MockClassificationProvider({
            "gap_id": "gap_3",
            "category": "PUNCTUATION_ONLY",
            "confidence": 0.88,
            "reasoning": "Only hyphen difference",
            "suggested_handler": "punctuation"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_3",
            gap_words=[
                {"id": "w1", "text": "Tick-", "start_time": 46.0, "end_time": 46.5},
                {"id": "w2", "text": "tock", "start_time": 46.5, "end_time": 47.0}
            ],
            preceding_words="concept of time",
            following_words="you're not a clock",
            reference_contexts={
                "genius": "Tick tock you're not a clock"
            }
        )
        
        assert len(proposals) == 1
        assert proposals[0].gap_category == GapCategory.PUNCTUATION_ONLY
        assert proposals[0].action == "NoAction"
    
    def test_no_error_classification(self):
        """Test that gaps matching a reference return NO_ERROR."""
        mock = MockClassificationProvider({
            "gap_id": "gap_4",
            "category": "NO_ERROR",
            "confidence": 0.99,
            "reasoning": "Matches genius reference exactly",
            "suggested_handler": "no_error"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_4",
            gap_words=[
                {"id": "w1", "text": "you're", "start_time": 38.0, "end_time": 38.3},
                {"id": "w2", "text": "telling", "start_time": 38.3, "end_time": 38.7},
                {"id": "w3", "text": "lies", "start_time": 38.7, "end_time": 39.1}
            ],
            preceding_words="Now",
            following_words="Tell me your words",
            reference_contexts={
                "genius": "Now you're telling lies",
                "lrclib": "Now you're telling me lies"
            }
        )
        
        assert len(proposals) == 1
        assert proposals[0].gap_category == GapCategory.NO_ERROR
        assert proposals[0].action == "NoAction"
    
    def test_repeated_section_flagged_for_review(self):
        """Test that repeated sections are flagged for human review."""
        mock = MockClassificationProvider({
            "gap_id": "gap_5",
            "category": "REPEATED_SECTION",
            "confidence": 0.65,
            "reasoning": "Chorus repetition not in condensed references",
            "suggested_handler": "repeated_section"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_5",
            gap_words=[
                {"id": "w1", "text": "You're", "start_time": 50.0, "end_time": 50.2},
                {"id": "w2", "text": "a", "start_time": 50.2, "end_time": 50.3},
                {"id": "w3", "text": "time", "start_time": 50.3, "end_time": 50.6},
                {"id": "w4", "text": "bomb", "start_time": 50.6, "end_time": 50.9}
            ],
            preceding_words="Tick tock you're not a clock",
            following_words="You're a time bomb baby",
            reference_contexts={
                "genius": "You're a time bomb baby"
            }
        )
        
        assert len(proposals) == 1
        assert proposals[0].gap_category == GapCategory.REPEATED_SECTION
        assert proposals[0].action == "Flag"
        assert proposals[0].requires_human_review == True
    
    def test_complex_multi_error_flagged(self):
        """Test that complex gaps with multiple errors are flagged."""
        mock = MockClassificationProvider({
            "gap_id": "gap_6",
            "category": "COMPLEX_MULTI_ERROR",
            "confidence": 0.70,
            "reasoning": "50 words with multiple different error types",
            "suggested_handler": "complex"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        # Large gap with many words
        gap_words = [
            {"id": f"w{i}", "text": f"word{i}", "start_time": i * 0.5, "end_time": (i + 1) * 0.5}
            for i in range(50)
        ]
        
        proposals = agent.propose_for_gap(
            gap_id="gap_6",
            gap_words=gap_words,
            preceding_words="some context",
            following_words="more context",
            reference_contexts={
                "genius": "different lyrics entirely"
            }
        )
        
        assert len(proposals) == 1
        assert proposals[0].gap_category == GapCategory.COMPLEX_MULTI_ERROR
        assert proposals[0].action == "Flag"
        assert proposals[0].requires_human_review == True
    
    def test_classification_failure_fallback(self):
        """Test that classification failure results in FLAG proposal."""
        # Mock provider that returns invalid data
        mock = MockClassificationProvider({
            "error": "Classification failed"
        })
        
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_error",
            gap_words=[{"id": "w1", "text": "test", "start_time": 10.0, "end_time": 10.5}],
            preceding_words="before",
            following_words="after",
            reference_contexts={}
        )
        
        # Should get a FLAG proposal as fallback
        assert len(proposals) == 1
        assert proposals[0].action == "Flag"
        assert proposals[0].requires_human_review == True
        assert "failed" in proposals[0].reason.lower() or "unable" in proposals[0].reason.lower()
    
    def test_metadata_propagation(self):
        """Test that artist/title metadata is included in proposals."""
        mock = MockClassificationProvider()
        agent = AgenticCorrector(provider=mock)
        
        proposals = agent.propose_for_gap(
            gap_id="gap_meta",
            gap_words=[{"id": "w1", "text": "test", "start_time": 10.0, "end_time": 10.5}],
            preceding_words="before",
            following_words="after",
            reference_contexts={},
            artist="Rancid",
            title="Time Bomb"
        )
        
        assert len(proposals) >= 1
        assert proposals[0].artist == "Rancid"
        assert proposals[0].title == "Time Bomb"
    
    def test_session_id_tracking(self):
        """Test that session_id is tracked through the workflow."""
        mock = MockClassificationProvider()
        agent = AgenticCorrector(provider=mock, session_id="test_session_123")
        
        # Make a classification call
        agent.propose_for_gap(
            gap_id="gap_session",
            gap_words=[{"id": "w1", "text": "test", "start_time": 10.0, "end_time": 10.5}],
            preceding_words="before",
            following_words="after",
            reference_contexts={}
        )
        
        # Verify session_id was passed to provider
        assert len(mock.calls) >= 1
        assert mock.calls[0]["session_id"] == "test_session_123"

