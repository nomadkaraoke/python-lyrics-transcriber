"""Tests for gap classification and category handlers."""

import pytest
from lyrics_transcriber.correction.agentic.models.schemas import GapCategory, GapClassification
from lyrics_transcriber.correction.agentic.handlers.registry import HandlerRegistry
from lyrics_transcriber.correction.agentic.handlers import (
    PunctuationHandler,
    SoundAlikeHandler,
    BackgroundVocalsHandler,
    ExtraWordsHandler,
    NoErrorHandler,
    RepeatedSectionHandler,
    ComplexMultiErrorHandler,
    AmbiguousHandler
)
from lyrics_transcriber.correction.agentic.prompts.classifier import build_classification_prompt


class TestGapClassificationSchema:
    """Test gap classification schema validation."""
    
    def test_gap_classification_creation(self):
        """Test creating a valid GapClassification."""
        classification = GapClassification(
            gap_id="gap_1",
            category=GapCategory.SOUND_ALIKE,
            confidence=0.95,
            reasoning="Test reasoning",
            suggested_handler="sound_alike"
        )
        
        assert classification.gap_id == "gap_1"
        assert classification.category == GapCategory.SOUND_ALIKE
        assert classification.confidence == 0.95
    
    def test_gap_classification_validation(self):
        """Test that validation rejects invalid data."""
        with pytest.raises(Exception):
            # Invalid category
            GapClassification(
                gap_id="gap_1",
                category="INVALID_CATEGORY",
                confidence=0.95,
                reasoning="Test"
            )
        
        with pytest.raises(Exception):
            # Invalid confidence (> 1.0)
            GapClassification(
                gap_id="gap_1",
                category=GapCategory.SOUND_ALIKE,
                confidence=1.5,
                reasoning="Test"
            )


class TestHandlerRegistry:
    """Test handler registry functionality."""
    
    def test_get_all_handlers(self):
        """Test that all categories have registered handlers."""
        for category in GapCategory:
            handler = HandlerRegistry.get_handler(category)
            assert handler is not None
            assert handler.category == category
    
    def test_handler_initialization_with_metadata(self):
        """Test handlers can be initialized with song metadata."""
        handler = HandlerRegistry.get_handler(
            GapCategory.SOUND_ALIKE,
            artist="Test Artist",
            title="Test Song"
        )
        
        assert handler.artist == "Test Artist"
        assert handler.title == "Test Song"


class TestPunctuationHandler:
    """Test punctuation-only handler."""
    
    def test_returns_no_action(self):
        """Test that punctuation differences return NO_ACTION."""
        handler = PunctuationHandler()
        
        gap_words = [
            {"id": "w1", "text": "Tick-", "start_time": 10.0, "end_time": 10.5},
            {"id": "w2", "text": "tock", "start_time": 10.5, "end_time": 11.0}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="test before",
            following_words="test after",
            reference_contexts={"genius": "Tick tock"},
            classification_reasoning="Only hyphen difference"
        )
        
        assert len(proposals) == 1
        assert proposals[0].action == "NoAction"
        assert proposals[0].confidence >= 0.9


class TestBackgroundVocalsHandler:
    """Test background vocals handler."""
    
    def test_detects_parentheses(self):
        """Test that parenthesized content is marked for deletion."""
        handler = BackgroundVocalsHandler()
        
        gap_words = [
            {"id": "w1", "text": "(Big", "start_time": 10.0, "end_time": 10.3},
            {"id": "w2", "text": "business)", "start_time": 10.3, "end_time": 10.8}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="was it worth it?",
            following_words="Was it worth",
            reference_contexts={"genius": "was it worth what you did to big business?"},
            classification_reasoning="Background vocals"
        )
        
        assert len(proposals) == 1
        assert proposals[0].action == "DeleteWord"
        assert len(proposals[0].word_ids) == 2
    
    def test_flags_if_no_parentheses(self):
        """Test that handler flags for review if no parentheses found."""
        handler = BackgroundVocalsHandler()
        
        gap_words = [
            {"id": "w1", "text": "test", "start_time": 10.0, "end_time": 10.5}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="before",
            following_words="after",
            reference_contexts={},
            classification_reasoning="Classified as background but no parens"
        )
        
        assert len(proposals) == 1
        assert proposals[0].action == "Flag"
        assert proposals[0].requires_human_review


class TestExtraWordsHandler:
    """Test extra filler words handler."""
    
    def test_detects_filler_words(self):
        """Test detection of common filler words."""
        handler = ExtraWordsHandler()
        
        gap_words = [
            {"id": "w1", "text": "But", "start_time": 10.0, "end_time": 10.3},
            {"id": "w2", "text": "to", "start_time": 10.3, "end_time": 10.5},
            {"id": "w3", "text": "wreck", "start_time": 10.5, "end_time": 10.8}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="just in time.",
            following_words="my life",
            reference_contexts={"genius": "just in time To wreck my life"},
            classification_reasoning="Extra word at start"
        )
        
        # Should propose deleting "But"
        assert len(proposals) >= 1
        delete_proposals = [p for p in proposals if p.action == "DeleteWord"]
        assert len(delete_proposals) > 0


class TestNoErrorHandler:
    """Test no-error handler."""
    
    def test_returns_no_action(self):
        """Test that matching transcription returns NO_ACTION."""
        handler = NoErrorHandler()
        
        gap_words = [
            {"id": "w1", "text": "you're", "start_time": 10.0, "end_time": 10.3},
            {"id": "w2", "text": "telling", "start_time": 10.3, "end_time": 10.6},
            {"id": "w3", "text": "lies", "start_time": 10.6, "end_time": 11.0}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="Now",
            following_words="Tell me",
            reference_contexts={"genius": "Now you're telling lies"},
            classification_reasoning="Matches genius source"
        )
        
        assert len(proposals) == 1
        assert proposals[0].action == "NoAction"
        assert proposals[0].confidence >= 0.95


class TestSoundAlikeHandler:
    """Test sound-alike error handler."""
    
    def test_extracts_replacement_from_context(self):
        """Test extraction of replacement text from reference."""
        handler = SoundAlikeHandler()
        
        gap_words = [
            {"id": "w1", "text": "out", "start_time": 17.5, "end_time": 18.0}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="Oh no, was it worth it? Starting",
            following_words="I'm starting over",
            reference_contexts={
                "genius": "Starting now I'm starting over",
                "spotify": "Starting now I'm starting over"
            },
            classification_reasoning="Sound-alike: out vs now"
        )
        
        assert len(proposals) == 1
        # Should find "now" as replacement
        if proposals[0].action == "ReplaceWord":
            assert proposals[0].replacement_text is not None
            assert "now" in proposals[0].replacement_text.lower()
    
    def test_flags_if_cannot_extract(self):
        """Test that handler flags for review if replacement not found."""
        handler = SoundAlikeHandler()
        
        gap_words = [
            {"id": "w1", "text": "unknown", "start_time": 10.0, "end_time": 10.5}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="some random",
            following_words="context here",
            reference_contexts={},
            classification_reasoning="Sound-alike but no reference"
        )
        
        assert len(proposals) == 1
        assert proposals[0].requires_human_review


class TestRepeatedSectionHandler:
    """Test repeated section handler."""
    
    def test_always_flags_for_review(self):
        """Test that repeated sections are always flagged."""
        handler = RepeatedSectionHandler()
        
        gap_words = [
            {"id": "w1", "text": "You're", "start_time": 50.0, "end_time": 50.3},
            {"id": "w2", "text": "a", "start_time": 50.3, "end_time": 50.4},
            {"id": "w3", "text": "time", "start_time": 50.4, "end_time": 50.7},
            {"id": "w4", "text": "bomb", "start_time": 50.7, "end_time": 51.0}
        ]
        
        proposals = handler.handle(
            gap_id="test_gap",
            gap_words=gap_words,
            preceding_words="Tick tock you're not a clock",
            following_words="You're a time bomb baby",
            reference_contexts={"genius": "You're a time bomb baby"},
            classification_reasoning="Possible chorus repetition"
        )
        
        assert len(proposals) == 1
        assert proposals[0].action == "Flag"
        assert proposals[0].requires_human_review


class TestClassificationPrompt:
    """Test classification prompt generation."""
    
    def test_prompt_includes_all_context(self):
        """Test that prompt includes all required context."""
        prompt = build_classification_prompt(
            gap_text="out I'm starting over",
            preceding_words="Oh no, was it worth it? Starting",
            following_words="I'm gonna sleep With the next person",
            reference_contexts={
                "genius": "Starting now I'm starting over",
                "spotify": "Starting now I'm starting over"
            },
            artist="Rancid",
            title="Time Bomb",
            gap_id="gap_1"
        )
        
        # Check all components are present
        assert "out I'm starting over" in prompt
        assert "Starting" in prompt  # preceding
        assert "I'm gonna sleep" in prompt  # following
        assert "genius" in prompt.lower()
        assert "spotify" in prompt.lower()
        assert "Rancid" in prompt
        assert "Time Bomb" in prompt
        assert "gap_1" in prompt
        
        # Check categories are listed
        assert "SOUND_ALIKE" in prompt
        assert "BACKGROUND_VOCALS" in prompt
        assert "NO_ERROR" in prompt
        
        # Check it requests JSON
        assert "JSON" in prompt or "json" in prompt

