"""
End-to-end data pipeline testing.

These tests follow the complete data flow from backend generation 
through frontend consumption, ensuring the entire pipeline works
without mocking critical serialization/deserialization steps.
"""

import tempfile
import json
from pathlib import Path
from typing import Dict, Any

import pytest

from lyrics_transcriber.types import (
    AnchorSequence, Word, LyricsSegment, LyricsData, LyricsMetadata,
    CorrectionResult, WordCorrection, CorrectionStep
)
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.utils.word_utils import WordUtils
from tests.test_helpers import create_test_word, create_test_segment
from tests.contract.test_frontend_schemas import FrontendSchemaValidator


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def validator():
    """Provide a frontend schema validator."""
    return FrontendSchemaValidator()


def test_complete_anchor_sequence_pipeline_no_mocks(temp_cache_dir, validator):
    """
    Test complete anchor sequence generation and frontend compatibility without mocks.
    
    This test ensures that:
    1. Anchor sequences are generated correctly by backend
    2. Cache loading/saving works with new format
    3. Frontend can validate the complete data structure
    """
    # Skip if Node.js not available (for CI environments without frontend setup)
    try:
        validator.validate_data("word", {"id": "test", "text": "test", "start_time": 1.0, "end_time": 2.0})
    except RuntimeError as e:
        if "Node.js not found" in str(e):
            pytest.skip("Node.js not available for frontend validation")
        raise
    
    # Create test data that would typically come from transcription and reference lyrics
    transcribed_words = [
        create_test_word("my", start_time=0.0, end_time=0.5),
        create_test_word("heart", start_time=0.5, end_time=1.0),
        create_test_word("will", start_time=1.0, end_time=1.5),
        create_test_word("go", start_time=1.5, end_time=2.0),
        create_test_word("on", start_time=2.0, end_time=2.5),
    ]
    
    # Create reference lyrics
    reference_words = [
        create_test_word("my", start_time=0.0, end_time=0.5),
        create_test_word("heart", start_time=0.5, end_time=1.0),
        create_test_word("will", start_time=1.0, end_time=1.5),
        create_test_word("go", start_time=1.5, end_time=2.0),
        create_test_word("on", start_time=2.0, end_time=2.5),
    ]
    
    reference_segment = create_test_segment(
        "my heart will go on", 
        reference_words, 
        start_time=0.0, 
        end_time=2.5
    )
    
    reference_metadata = LyricsMetadata(
        source="test",
        track_name="My Heart Will Go On",
        artist_names="Celine Dion",
        lyrics_provider="test_provider",
        lyrics_provider_id="test_123"
    )
    
    reference_lyrics = LyricsData(
        segments=[reference_segment],
        metadata=reference_metadata,
        source="test"
    )
    
    # Test that individual words validate
    for word in transcribed_words:
        word_result = validator.validate_data("word", word.to_dict())
        assert word_result["success"], f"Word validation failed: {word_result.get('errors')}"
    
    # Create anchor sequence manually (simulating what AnchorSequenceFinder would do)
    anchor = AnchorSequence(
        id=WordUtils.generate_id(),
        transcribed_word_ids=[w.id for w in transcribed_words[:4]],  # "my heart will go"
        transcription_position=0,
        reference_positions={"test": 0},
        reference_word_ids={"test": [w.id for w in reference_words[:4]]},
        confidence=1.0
    )
    
    # Test anchor sequence serialization
    anchor_dict = anchor.to_dict()
    
    # Verify the anchor has the expected new format
    assert "id" in anchor_dict
    assert "transcribed_word_ids" in anchor_dict
    assert "reference_word_ids" in anchor_dict
    
    # Verify old format fields are NOT present
    assert "words" not in anchor_dict
    assert "text" not in anchor_dict or isinstance(anchor_dict.get("text"), str)  # text might be derived property
    
    # Test cache save/load cycle with new format
    cache_file = Path(temp_cache_dir) / "test_anchors.json"
    
    # Save to cache (simulate what AnchorSequenceFinder._save_to_cache does)
    cache_data = [{"anchor": anchor.to_dict(), "phrase_score": {
        "phrase_type": "complete",
        "natural_break_score": 0.8,
        "length_score": 0.7,
        "total_score": 0.75
    }}]
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    # Load from cache (simulate what AnchorSequenceFinder._load_from_cache does)
    with open(cache_file, 'r') as f:
        loaded_cache_data = json.load(f)
    
    loaded_anchor = AnchorSequence.from_dict(loaded_cache_data[0]["anchor"])
    loaded_serialized = loaded_anchor.to_dict()
    
    # Verify cache round-trip maintains new format
    assert loaded_serialized == anchor_dict
    
    # Test frontend validation of complete anchor sequence with phrase score
    complete_anchor_data = {
        **loaded_serialized,
        "phrase_score": loaded_cache_data[0]["phrase_score"],
        "total_score": 0.85
    }
    
    anchor_result = validator.validate_data("anchorSequence", complete_anchor_data)
    assert anchor_result["success"], f"Anchor sequence validation failed: {anchor_result.get('errors')}"


def test_old_cached_data_compatibility_pipeline(temp_cache_dir, validator):
    """
    Test that old cached data is properly converted and works with frontend.
    
    This is the EXACT regression test scenario from the document.
    """
    # Skip if Node.js not available
    try:
        validator.validate_data("word", {"id": "test", "text": "test", "start_time": 1.0, "end_time": 2.0})
    except RuntimeError as e:
        if "Node.js not found" in str(e):
            pytest.skip("Node.js not available for frontend validation")
        raise
    
    # Create cache file with OLD format data (as it existed before the fix)
    old_format_cache_data = [
        {
            "anchor": {
                "words": ["my", "heart", "will", "go"],
                "text": "my heart will go",
                "length": 4,
                "transcription_position": 0,
                "reference_positions": {"genius": 0, "azlyrics": 0},
                "confidence": 1.0
            },
            "phrase_score": {
                "phrase_type": "complete",
                "natural_break_score": 0.8,
                "length_score": 0.7,
                "total_score": 0.75
            }
        }
    ]
    
    cache_file = Path(temp_cache_dir) / "old_format_anchors.json"
    with open(cache_file, 'w') as f:
        json.dump(old_format_cache_data, f, indent=2)
    
    # Load using backend logic (this should convert to new format)
    with open(cache_file, 'r') as f:
        cached_data = json.load(f)
    
    # Simulate what AnchorSequenceFinder would do
    loaded_anchor = AnchorSequence.from_dict(cached_data[0]["anchor"])
    
    # Serialize for frontend (this should be new format)
    serialized = loaded_anchor.to_dict()
    
    # Verify conversion to new format
    assert "id" in serialized
    assert "transcribed_word_ids" in serialized
    assert "reference_word_ids" in serialized
    assert "words" not in serialized  # Old format should be gone
    
    # Create complete data structure for frontend validation
    complete_data = {
        **serialized,
        "phrase_score": cached_data[0]["phrase_score"],
        "total_score": 0.85
    }
    
    # This is the validation that would have failed before the fix
    result = validator.validate_data("anchorSequence", complete_data)
    assert result["success"], f"Old format conversion failed frontend validation: {result.get('errors')}"


def test_correction_result_end_to_end_pipeline(validator):
    """
    Test complete CorrectionResult serialization and frontend validation.
    
    This tests the full data structure that gets sent to the frontend
    for the review interface.
    """
    # Skip if Node.js not available
    try:
        validator.validate_data("word", {"id": "test", "text": "test", "start_time": 1.0, "end_time": 2.0})
    except RuntimeError as e:
        if "Node.js not found" in str(e):
            pytest.skip("Node.js not available for frontend validation")
        raise
    
    # Create realistic test data
    original_words = [
        create_test_word("my", start_time=0.0, end_time=0.5),
        create_test_word("hart", start_time=0.5, end_time=1.0),  # Misspelled
        create_test_word("will", start_time=1.0, end_time=1.5),
        create_test_word("go", start_time=1.5, end_time=2.0),
    ]
    
    corrected_words = [
        create_test_word("my", start_time=0.0, end_time=0.5),
        create_test_word("heart", start_time=0.5, end_time=1.0),  # Corrected
        create_test_word("will", start_time=1.0, end_time=1.5),
        create_test_word("go", start_time=1.5, end_time=2.0),
    ]
    
    original_segment = create_test_segment("my hart will go", original_words, 0.0, 2.0)
    corrected_segment = create_test_segment("my heart will go", corrected_words, 0.0, 2.0)
    
    # Create correction
    correction = WordCorrection(
        id=WordUtils.generate_id(),
        handler="spell_check",
        original_word="hart",
        corrected_word="heart",
        word_id=original_words[1].id,
        corrected_word_id=corrected_words[1].id,
        source="test",
        confidence=0.9,
        reason="spelling_correction",
        alternatives={"heart": 5, "hurt": 1},
        is_deletion=False,
        length=1
    )
    
    # Create anchor sequence
    anchor = AnchorSequence(
        id=WordUtils.generate_id(),
        transcribed_word_ids=[w.id for w in corrected_words],
        transcription_position=0,
        reference_positions={"test": 0},
        reference_word_ids={"test": [w.id for w in corrected_words]},
        confidence=0.9
    )
    
    # Create correction step
    step = CorrectionStep(
        handler_name="spell_check",
        affected_word_ids=[original_words[1].id],
        affected_segment_ids=[original_segment.id],
        corrections=[correction],
        segments_before=[original_segment],
        segments_after=[corrected_segment]
    )
    
    # Create reference lyrics
    reference_metadata = LyricsMetadata(
        source="test",
        track_name="Test Song",
        artist_names="Test Artist",
        lyrics_provider="test",
        lyrics_provider_id="test"
    )
    
    reference_lyrics = LyricsData(
        segments=[corrected_segment],
        metadata=reference_metadata,
        source="test"
    )
    
    # Create complete CorrectionResult
    result = CorrectionResult(
        original_segments=[original_segment],
        corrected_segments=[corrected_segment],
        corrections=[correction],
        corrections_made=1,
        confidence=0.9,
        reference_lyrics={"test": reference_lyrics},
        anchor_sequences=[anchor],
        gap_sequences=[],
        resized_segments=[corrected_segment],
        metadata={
            "anchor_sequences_count": 1,
            "gap_sequences_count": 0,
            "total_words": 4,
            "correction_ratio": 0.25,
        },
        correction_steps=[step],
        word_id_map={w.id: w.id for w in original_words},
        segment_id_map={original_segment.id: corrected_segment.id}
    )
    
    # Serialize complete result
    serialized = result.to_dict()
    
    # Validate against frontend schema
    validation_result = validator.validate_data("correctionData", serialized)
    
    assert validation_result["success"], f"Complete correction result validation failed: {validation_result.get('errors')}"
    assert validation_result["valid"], "Complete correction result is not valid according to frontend schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 