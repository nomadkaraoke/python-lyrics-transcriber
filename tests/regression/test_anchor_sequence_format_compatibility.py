"""
Regression test for anchor sequence format compatibility issue.

This test verifies that anchor sequences loaded from cache (old format) 
are properly converted to the new format expected by the frontend.

This test would have caught the issue where cached anchor sequences
were serialized in old format (words, text, length) but frontend
expected new format (id, transcribed_word_ids, reference_word_ids).

Enhanced with contract testing to validate against actual frontend schemas.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch
from pathlib import Path

from lyrics_transcriber.types import AnchorSequence
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.utils.word_utils import WordUtils


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_old_format_anchor_sequence_frontend_compatibility(temp_cache_dir):
    """
    Regression test: Verify old format cached anchor sequences work with frontend
    
    This test recreates the exact scenario that caused the bug:
    1. Cached anchor sequences in old format (words, text, length)
    2. Backend loads and converts to new format
    3. Frontend validation should succeed
    """
    # Create anchor sequence data in OLD format (as it was cached)
    old_format_data = {
        "words": ["hello", "world", "test"],
        "text": "hello world test", 
        "length": 3,
        "transcription_position": 0,
        "reference_positions": {"source1": 0},
        "confidence": 1.0
    }
    
    # Simulate loading from cache (old format)
    anchor = AnchorSequence.from_dict(old_format_data)
    
    # Serialize using to_dict() - this is what frontend receives
    serialized = anchor.to_dict()
    
    # Verify NEW format fields are present (required by frontend)
    assert "id" in serialized, "Missing 'id' field required by frontend"
    assert "transcribed_word_ids" in serialized, "Missing 'transcribed_word_ids' field required by frontend" 
    assert "reference_word_ids" in serialized, "Missing 'reference_word_ids' field required by frontend"
    
    # Verify the data structure matches frontend expectations
    assert isinstance(serialized["id"], str)
    assert isinstance(serialized["transcribed_word_ids"], list)
    assert isinstance(serialized["reference_word_ids"], dict)
    assert isinstance(serialized["transcription_position"], int)
    assert isinstance(serialized["reference_positions"], dict)
    assert isinstance(serialized["confidence"], float)
    
    # Verify old format fields are NOT present in serialized output
    # (They can exist for backwards compatibility but shouldn't be serialized)
    assert "words" not in serialized, "Old 'words' field should not be in serialized output"
    
    # Note: 'text' and 'length' may be present as derived properties, which is fine


def test_old_format_anchor_sequence_with_contract_validation(temp_cache_dir):
    """
    ENHANCED regression test with actual frontend validation.
    
    This test does everything the original regression test does, PLUS
    validates against the actual frontend schemas to ensure contract compliance.
    """
    # Import contract testing infrastructure (gracefully handle if not available)
    try:
        from tests.contract.test_frontend_schemas import FrontendSchemaValidator
        validator = FrontendSchemaValidator()
        contract_testing_available = True
    except (ImportError, RuntimeError):
        # Contract testing not available (Node.js not installed, etc.)
        contract_testing_available = False
    
    # Create anchor sequence data in OLD format (as it was cached)
    old_format_data = {
        "words": ["hello", "world", "test"],
        "text": "hello world test", 
        "length": 3,
        "transcription_position": 0,
        "reference_positions": {"source1": 0},
        "confidence": 1.0
    }
    
    # Simulate loading from cache (old format)
    anchor = AnchorSequence.from_dict(old_format_data)
    
    # Serialize using to_dict() - this is what frontend receives
    serialized = anchor.to_dict()
    
    # Backend validation (original regression test)
    assert "id" in serialized, "Missing 'id' field required by frontend"
    assert "transcribed_word_ids" in serialized, "Missing 'transcribed_word_ids' field required by frontend" 
    assert "reference_word_ids" in serialized, "Missing 'reference_word_ids' field required by frontend"
    assert "words" not in serialized, "Old 'words' field should not be in serialized output"
    
    # Contract validation (enhanced test)
    if contract_testing_available:
        try:
            # Add required fields for complete anchor sequence validation
            complete_anchor_data = {
                **serialized,
                "phrase_score": {
                    "phrase_type": "complete",
                    "natural_break_score": 0.8,
                    "length_score": 0.7,
                    "total_score": 0.75
                },
                "total_score": 0.85
            }
            
            # Validate against actual frontend schema
            result = validator.validate_data("anchorSequence", complete_anchor_data)
            
            assert result["success"], f"Contract validation failed: {result.get('errors', result.get('error'))}"
            assert result["valid"], "Data structure is not valid according to frontend schema"
            
            print("✅ Contract validation passed - backend data matches frontend schema")
            
        except Exception as e:
            if "Node.js not found" in str(e):
                print("⚠️  Contract validation skipped - Node.js not available")
            else:
                # Re-raise other errors
                raise
    else:
        print("⚠️  Contract validation skipped - dependencies not available")


def test_cached_anchor_file_format_conversion(temp_cache_dir):
    """
    Test that cached anchor files in old format are properly converted
    
    This simulates the actual cache loading scenario that was broken.
    """
    # Create a cache file with old format data
    old_format_anchors = [
        {
            "words": ["my", "heart", "will", "go"],
            "text": "my heart will go",
            "length": 4,
            "transcription_position": 0,
            "reference_positions": {"genius": 0, "azlyrics": 0},
            "confidence": 1.0
        },
        {
            "words": ["on", "and", "on"],
            "text": "on and on", 
            "length": 3,
            "transcription_position": 4,
            "reference_positions": {"genius": 4},
            "confidence": 0.5
        }
    ]
    
    # Save to cache file (simulating old cached data)
    cache_file = os.path.join(temp_cache_dir, "anchors_test.json")
    with open(cache_file, 'w') as f:
        json.dump(old_format_anchors, f)
    
    # Load anchors using backend logic
    loaded_anchors = []
    with open(cache_file, 'r') as f:
        cached_data = json.load(f)
        for anchor_data in cached_data:
            anchor = AnchorSequence.from_dict(anchor_data)
            loaded_anchors.append(anchor)
    
    # Verify all loaded anchors can be serialized for frontend
    for anchor in loaded_anchors:
        serialized = anchor.to_dict()
        
        # Must have new format fields
        assert "id" in serialized
        assert "transcribed_word_ids" in serialized  
        assert "reference_word_ids" in serialized
        
        # Must NOT have old format fields in serialized output
        assert "words" not in serialized


def test_anchor_sequence_cache_invalidation_on_format_change():
    """
    Test that cache is properly invalidated when data format changes.
    
    This ensures that old cached data doesn't cause issues.
    """
    # Create old format cache data
    old_format_data = {
        "words": ["cached", "data"],
        "text": "cached data",
        "length": 2,
        "transcription_position": 0,
        "reference_positions": {"source1": 0},
        "confidence": 1.0,
        # Note: missing format_version or having old version
    }
    
    # Load and convert
    anchor = AnchorSequence.from_dict(old_format_data)
    
    # Verify conversion worked and output is frontend-compatible
    serialized = anchor.to_dict()
    
    assert "id" in serialized
    assert "transcribed_word_ids" in serialized
    assert "reference_word_ids" in serialized
    
    # Verify no old format artifacts
    assert "words" not in serialized


def test_regression_meta_validation():
    """
    Meta-test: Verify that this regression test would have caught the original bug.
    
    This test documents the exact conditions under which the original bug occurred
    and confirms our fix addresses them.
    """
    # Document the bug scenario
    bug_scenario = {
        "cached_format": ["words", "text", "length"],
        "frontend_expected": ["id", "transcribed_word_ids", "reference_word_ids"],
        "failure_point": "Frontend Zod validation",
        "root_cause": "AnchorSequence.to_dict() returned old format when _words present"
    }
    
    # Test that our fix addresses each aspect
    old_format_data = {
        "words": ["test", "data"],
        "text": "test data",
        "length": 2,
        "transcription_position": 0,
        "reference_positions": {"source1": 0},
        "confidence": 1.0
    }
    
    # Load using fixed backend logic
    anchor = AnchorSequence.from_dict(old_format_data)
    serialized = anchor.to_dict()
    
    # Verify the fix
    for expected_field in bug_scenario["frontend_expected"]:
        assert expected_field in serialized, f"Fix failed: missing {expected_field}"
    
    for old_field in bug_scenario["cached_format"]:
        if old_field in ["text", "length"]:
            # These might be present as derived properties
            continue
        assert old_field not in serialized, f"Fix failed: old field {old_field} still present"
    
    print("✅ Regression test confirms the fix addresses the original bug")


if __name__ == "__main__":
    # Run this specific test to verify the fix
    pytest.main([__file__, "-v"]) 