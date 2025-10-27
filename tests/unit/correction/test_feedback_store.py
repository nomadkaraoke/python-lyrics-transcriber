"""Tests for the feedback store and annotation system."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from lyrics_transcriber.correction.feedback.store import FeedbackStore
from lyrics_transcriber.correction.feedback.schemas import (
    CorrectionAnnotation,
    CorrectionAnnotationType,
    CorrectionAction,
    AnnotationStatistics
)


@pytest.fixture
def temp_store():
    """Create a temporary feedback store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = FeedbackStore(storage_dir=tmpdir)
        yield store


@pytest.fixture
def sample_annotation():
    """Create a sample annotation for testing."""
    return CorrectionAnnotation(
        audio_hash="test_hash_123",
        gap_id="gap_1",
        annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
        action_taken=CorrectionAction.REPLACE,
        original_text="out I'm starting over",
        corrected_text="now I'm starting over",
        confidence=5.0,
        reasoning="The word 'out' sounds like 'now' but reference confirms 'now'",
        word_ids_affected=["w1"],
        agentic_proposal={
            "action": "ReplaceWord",
            "replacement_text": "now",
            "confidence": 0.8,
            "reason": "Sound-alike error"
        },
        agentic_category="SOUND_ALIKE",
        agentic_agreed=True,
        reference_sources_consulted=["genius", "spotify"],
        artist="Rancid",
        title="Time Bomb",
        session_id="session_123"
    )


class TestFeedbackStore:
    """Test the FeedbackStore class."""
    
    def test_store_initialization(self, temp_store):
        """Test store initialization creates file."""
        assert temp_store.annotations_file.exists()
    
    def test_save_single_annotation(self, temp_store, sample_annotation):
        """Test saving a single annotation."""
        success = temp_store.save_annotation(sample_annotation)
        
        assert success
        assert temp_store.annotations_file.exists()
        
        # Verify file content
        content = temp_store.annotations_file.read_text()
        assert sample_annotation.annotation_id in content
        assert "SOUND_ALIKE" in content
    
    def test_save_multiple_annotations(self, temp_store):
        """Test saving multiple annotations."""
        annotations = [
            CorrectionAnnotation(
                audio_hash=f"hash_{i}",
                annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
                action_taken=CorrectionAction.REPLACE,
                original_text=f"original_{i}",
                corrected_text=f"corrected_{i}",
                confidence=4.0,
                reasoning=f"Test reasoning {i}",
                artist="Test Artist",
                title="Test Song",
                session_id="session_test"
            )
            for i in range(5)
        ]
        
        count = temp_store.save_annotations(annotations)
        
        assert count == 5
        
        # Verify we can load them back
        loaded = temp_store.get_all_annotations()
        assert len(loaded) == 5
    
    def test_load_annotations(self, temp_store, sample_annotation):
        """Test loading annotations from file."""
        # Save then load
        temp_store.save_annotation(sample_annotation)
        
        loaded = temp_store.get_all_annotations()
        
        assert len(loaded) == 1
        assert loaded[0].annotation_id == sample_annotation.annotation_id
        assert loaded[0].audio_hash == sample_annotation.audio_hash
        assert loaded[0].annotation_type == sample_annotation.annotation_type
    
    def test_get_annotations_by_song(self, temp_store):
        """Test filtering annotations by audio hash."""
        # Save annotations for different songs
        ann1 = CorrectionAnnotation(
            audio_hash="song_a",
            annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
            action_taken=CorrectionAction.REPLACE,
            original_text="test1",
            corrected_text="test1_fixed",
            confidence=5.0,
            reasoning="Test reasoning 1",
            artist="Artist A",
            title="Song A",
            session_id="session_a"
        )
        
        ann2 = CorrectionAnnotation(
            audio_hash="song_b",
            annotation_type=CorrectionAnnotationType.BACKGROUND_VOCALS,
            action_taken=CorrectionAction.DELETE,
            original_text="test2",
            corrected_text="",
            confidence=4.0,
            reasoning="Test reasoning 2",
            artist="Artist B",
            title="Song B",
            session_id="session_b"
        )
        
        temp_store.save_annotation(ann1)
        temp_store.save_annotation(ann2)
        
        # Get annotations for song_a
        song_a_anns = temp_store.get_annotations_by_song("song_a")
        
        assert len(song_a_anns) == 1
        assert song_a_anns[0].audio_hash == "song_a"
    
    def test_get_annotations_by_category(self, temp_store):
        """Test filtering annotations by category."""
        # Save different types
        for category in [CorrectionAnnotationType.SOUND_ALIKE, CorrectionAnnotationType.BACKGROUND_VOCALS]:
            ann = CorrectionAnnotation(
                audio_hash="test_hash",
                annotation_type=category,
                action_taken=CorrectionAction.REPLACE,
                original_text="test",
                corrected_text="test_fixed",
                confidence=4.0,
                reasoning="Test reasoning",
                artist="Test Artist",
                title="Test Song",
                session_id="session_test"
            )
            temp_store.save_annotation(ann)
        
        # Filter by category
        sound_alike = temp_store.get_annotations_by_category("SOUND_ALIKE")
        
        assert len(sound_alike) == 1
        assert sound_alike[0].annotation_type == CorrectionAnnotationType.SOUND_ALIKE
    
    def test_get_statistics(self, temp_store):
        """Test statistics generation."""
        # Save diverse annotations
        annotations = [
            CorrectionAnnotation(
                audio_hash="hash_1",
                annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
                action_taken=CorrectionAction.REPLACE,
                original_text="out",
                corrected_text="now",
                confidence=5.0,
                reasoning="Sound-alike",
                agentic_proposal={"action": "ReplaceWord"},
                agentic_agreed=True,
                artist="Artist 1",
                title="Song 1",
                session_id="session_1"
            ),
            CorrectionAnnotation(
                audio_hash="hash_1",
                annotation_type=CorrectionAnnotationType.BACKGROUND_VOCALS,
                action_taken=CorrectionAction.DELETE,
                original_text="(backing)",
                corrected_text="",
                confidence=4.0,
                reasoning="Background vocal",
                agentic_proposal={"action": "DeleteWord"},
                agentic_agreed=True,
                artist="Artist 1",
                title="Song 1",
                session_id="session_1"
            ),
            CorrectionAnnotation(
                audio_hash="hash_2",
                annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
                action_taken=CorrectionAction.REPLACE,
                original_text="test",
                corrected_text="test2",
                confidence=3.0,
                reasoning="Another test",
                artist="Artist 2",
                title="Song 2",
                session_id="session_2"
            )
        ]
        
        for ann in annotations:
            temp_store.save_annotation(ann)
        
        # Get statistics
        stats = temp_store.get_statistics()
        
        assert isinstance(stats, AnnotationStatistics)
        assert stats.total_annotations == 3
        assert stats.songs_annotated == 2  # Two unique hashes
        assert stats.annotations_by_type["SOUND_ALIKE"] == 2
        assert stats.annotations_by_type["BACKGROUND_VOCALS"] == 1
        assert stats.average_confidence == (5.0 + 4.0 + 3.0) / 3
        assert stats.agentic_agreement_rate == 1.0  # All agreed
    
    def test_export_training_data(self, temp_store):
        """Test exporting high-confidence annotations for training."""
        # Save mix of confidence levels
        for i, conf in enumerate([3.0, 4.0, 5.0]):
            ann = CorrectionAnnotation(
                audio_hash=f"hash_{i}",
                annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
                action_taken=CorrectionAction.REPLACE,
                original_text=f"original_{i}",
                corrected_text=f"corrected_{i}",
                confidence=conf,
                reasoning=f"Reasoning {i}",
                artist="Test Artist",
                title=f"Song {i}",
                session_id=f"session_{i}"
            )
            temp_store.save_annotation(ann)
        
        # Export
        output_file = Path(temp_store.storage_dir) / "training.jsonl"
        result_file = temp_store.export_to_training_data(output_file)
        
        assert result_file.exists()
        
        # Should only include confidence >= 4.0 (2 annotations)
        lines = result_file.read_text().strip().split('\n')
        assert len(lines) == 2
        
        # Verify format
        for line in lines:
            data = json.loads(line)
            assert "input" in data
            assert "output" in data
            assert "metadata" in data
    
    def test_handles_corrupted_line(self, temp_store):
        """Test that store handles corrupted JSONL gracefully."""
        # Write a valid line and a corrupted line
        temp_store.annotations_file.write_text(
            '{"annotation_id": "test1", "audio_hash": "hash1", "annotation_type": "SOUND_ALIKE", "action_taken": "REPLACE", "original_text": "test", "corrected_text": "test2", "confidence": 5.0, "reasoning": "test reason", "artist": "A", "title": "T", "session_id": "s", "timestamp": "2025-01-01T00:00:00"}\n'
            '{broken json line}\n'
            '{"annotation_id": "test2", "audio_hash": "hash2", "annotation_type": "SOUND_ALIKE", "action_taken": "REPLACE", "original_text": "test", "corrected_text": "test2", "confidence": 4.0, "reasoning": "test reason 2", "artist": "A", "title": "T", "session_id": "s", "timestamp": "2025-01-01T00:00:00"}\n'
        )
        
        # Should load 2 valid annotations, skip corrupted line
        loaded = temp_store.get_all_annotations()
        
        assert len(loaded) == 2
        assert loaded[0].annotation_id == "test1"
        assert loaded[1].annotation_id == "test2"

