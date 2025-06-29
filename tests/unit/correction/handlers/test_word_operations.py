import pytest
from unittest.mock import Mock, patch
from lyrics_transcriber.correction.handlers.word_operations import WordOperations
from lyrics_transcriber.types import GapSequence, WordCorrection, AnchorSequence, Word, ScoredAnchor, PhraseScore, PhraseType


class TestWordOperations:
    """Test cases for WordOperations class."""

    @pytest.fixture
    def sample_gap(self):
        """Sample gap sequence for testing."""
        return GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},
            transcription_position=5,
            preceding_anchor_id="anchor_1",
            following_anchor_id="anchor_2",
        )

    @pytest.fixture
    def sample_anchor_sequences(self):
        """Sample anchor sequences for testing."""
        anchor1 = AnchorSequence(
            id="anchor_1",
            transcribed_word_ids=["t1", "t2"],
            reference_word_ids={"source1": ["r1", "r2"]},
            transcription_position=0,
            reference_positions={"source1": 2},
            confidence=0.9,
        )
        
        anchor2 = AnchorSequence(
            id="anchor_2",
            transcribed_word_ids=["t3", "t4"],
            reference_word_ids={"source1": ["r3", "r4"]},
            transcription_position=10,
            reference_positions={"source1": 6},
            confidence=0.95,
        )
        
        # Create ScoredAnchor objects with PhraseScore
        phrase_score = PhraseScore(
            phrase_type=PhraseType.COMPLETE,
            natural_break_score=0.8,
            length_score=0.7
        )
        
        return [
            ScoredAnchor(anchor=anchor1, phrase_score=phrase_score),
            ScoredAnchor(anchor=anchor2, phrase_score=phrase_score)
        ]

    def test_calculate_reference_positions_with_anchors(self, sample_gap, sample_anchor_sequences):
        """Test calculating reference positions with anchor sequences."""
        sources = ["source1"]
        
        result = WordOperations.calculate_reference_positions(
            sample_gap, 
            sources, 
            sample_anchor_sequences
        )
        
        assert isinstance(result, dict)
        assert "source1" in result
        # Should have calculated a position based on anchors (returns single int)
        assert isinstance(result["source1"], int)

    def test_calculate_reference_positions_without_anchors(self, sample_gap):
        """Test calculating reference positions without anchor sequences."""
        sources = ["source1"]
        
        result = WordOperations.calculate_reference_positions(sample_gap, sources)
        
        assert isinstance(result, dict)
        # Should return empty dict when no anchors
        assert len(result) == 0

    def test_calculate_reference_positions_single_source_string(self, sample_gap, sample_anchor_sequences):
        """Test calculating reference positions with single source as string."""
        source = ["source1"]  # Method expects a list, not a string
        
        result = WordOperations.calculate_reference_positions(
            sample_gap, 
            source, 
            sample_anchor_sequences
        )
        
        assert isinstance(result, dict)
        assert "source1" in result

    def test_calculate_reference_positions_missing_anchor(self, sample_gap):
        """Test calculating positions when anchor is missing."""
        # Create anchor sequences that don't match the gap's anchor IDs
        anchor = AnchorSequence(
            id="different_anchor",
            transcribed_word_ids=["t1"],
            reference_word_ids={"source1": ["r1"]},
            transcription_position=0,
            reference_positions={"source1": 0},
            confidence=0.9,
        )
        phrase_score = PhraseScore(
            phrase_type=PhraseType.COMPLETE,
            natural_break_score=0.8,
            length_score=0.7
        )
        anchor_sequences = [ScoredAnchor(anchor=anchor, phrase_score=phrase_score)]
        
        result = WordOperations.calculate_reference_positions(
            sample_gap, 
            ["source1"], 
            anchor_sequences
        )
        
        # Should return empty dict when anchor not found
        assert len(result) == 0

    def test_create_word_replacement_correction(self):
        """Test creating a word replacement correction."""
        correction = WordOperations.create_word_replacement_correction(
            original_word="hello",
            corrected_word="hi",
            original_position=5,
            source="test_source",
            confidence=0.9,
            reason="test reason",
            handler="TestHandler",
            reference_positions={"source1": [10, 11]},
            original_word_id="word_1",
            corrected_word_id="word_2"
        )
        
        assert isinstance(correction, WordCorrection)
        assert correction.original_word == "hello"
        assert correction.corrected_word == "hi"
        assert correction.original_position == 5
        assert correction.source == "test_source"
        assert correction.confidence == 0.9
        assert correction.reason == "test reason"
        assert correction.handler == "TestHandler"
        assert correction.reference_positions == {"source1": [10, 11]}
        assert correction.word_id == "word_1"
        assert correction.corrected_word_id == "word_2"
        assert not correction.is_deletion

    def test_create_word_split_corrections(self):
        """Test creating word split corrections."""
        corrections = WordOperations.create_word_split_corrections(
            original_word="hello",
            reference_words=["hi", "there"],
            original_position=3,
            source="test_source",
            confidence=0.8,
            reason="split reason",
            handler="TestHandler",
            reference_positions={"source1": [7, 8]},
            original_word_id="word_1",
            corrected_word_ids=["word_2", "word_3"]
        )
        
        assert len(corrections) == 2
        
        # First correction (replacement)
        first = corrections[0]
        assert first.original_word == "hello"
        assert first.corrected_word == "hi"
        assert first.original_position == 3
        assert first.split_index == 0
        assert first.split_total == 2
        assert first.word_id is not None  # Generated ID
        assert first.corrected_word_id == "word_2"  # Provided ID
        
        # Second correction (insertion)
        second = corrections[1]
        assert second.original_word == "hello"  # All splits use the same original word
        assert second.corrected_word == "there"
        assert second.original_position == 3
        assert second.split_index == 1
        assert second.split_total == 2
        assert second.corrected_word_id == "word_3"

    def test_create_word_split_corrections_single_word(self):
        """Test creating word split corrections with single reference word."""
        corrections = WordOperations.create_word_split_corrections(
            original_word="hello",
            reference_words=["hi"],
            original_position=3,
            source="test_source",
            confidence=0.8,
            reason="split reason",
            handler="TestHandler",
        )
        
        assert len(corrections) == 1
        assert corrections[0].original_word == "hello"
        assert corrections[0].corrected_word == "hi"

    def test_create_word_combine_corrections(self):
        """Test creating word combine corrections."""
        corrections = WordOperations.create_word_combine_corrections(
            original_words=["hello", "there"],
            reference_word="hi",
            original_position=2,
            source="test_source",
            confidence=0.7,
            combine_reason="combine reason",
            delete_reason="delete reason",
            handler="TestHandler",
            reference_positions={"source1": [5]},
            original_word_ids=["word_1", "word_2"],
            corrected_word_id="word_3"
        )
        
        assert len(corrections) == 2
        
        # First correction (replacement)
        first = corrections[0]
        assert first.original_word == "hello"
        assert first.corrected_word == "hi"
        assert first.original_position == 2
        assert first.reason == "combine reason"
        assert first.word_id is not None  # Generated ID
        assert first.corrected_word_id == "word_3"  # Provided ID
        assert not first.is_deletion
        
        # Second correction (deletion)
        second = corrections[1]
        assert second.original_word == "there"
        assert second.corrected_word == ""
        assert second.original_position == 3
        assert second.reason == "delete reason"
        assert second.word_id is not None  # Generated ID
        assert second.is_deletion

    def test_create_word_combine_corrections_single_word(self):
        """Test creating word combine corrections with single original word."""
        corrections = WordOperations.create_word_combine_corrections(
            original_words=["hello"],
            reference_word="hi",
            original_position=2,
            source="test_source",
            confidence=0.7,
            combine_reason="combine reason",
            delete_reason="delete reason",
            handler="TestHandler",
        )
        
        assert len(corrections) == 1
        assert corrections[0].original_word == "hello"
        assert corrections[0].corrected_word == "hi"
        assert not corrections[0].is_deletion

    def test_create_word_replacement_correction_minimal_args(self):
        """Test creating word replacement with minimal arguments."""
        correction = WordOperations.create_word_replacement_correction(
            original_word="test",
            corrected_word="fixed",
            original_position=0,
            source="manual",
            confidence=0.8,
            reason="test reason",
            handler="TestHandler"
        )
        
        assert correction.original_word == "test"
        assert correction.corrected_word == "fixed"
        assert correction.original_position == 0
        assert correction.source == "manual"
        assert correction.confidence == 0.8
        assert correction.reason == "test reason"
        assert correction.handler == "TestHandler"
        assert correction.reference_positions is None  # Default when not provided
        assert correction.word_id is None  # Default when not provided
        assert correction.corrected_word_id is not None  # Generated ID

    def test_create_word_split_corrections_minimal_args(self):
        """Test creating word split with minimal arguments."""
        corrections = WordOperations.create_word_split_corrections(
            original_word="test",
            reference_words=["t", "est"],
            original_position=0,
            source="manual",
            confidence=0.8,
            reason="test reason",
            handler="TestHandler"
        )
        
        assert len(corrections) == 2
        assert corrections[0].original_word == "test"
        assert corrections[0].corrected_word == "t"
        assert corrections[1].original_word == "test"  # All splits use the same original word
        assert corrections[1].corrected_word == "est"

    def test_create_word_combine_corrections_minimal_args(self):
        """Test creating word combine with minimal arguments."""
        corrections = WordOperations.create_word_combine_corrections(
            original_words=["hello", "world"],
            reference_word="hi",
            original_position=0,
            source="manual",
            confidence=0.8,
            combine_reason="test combine",
            delete_reason="test delete",
            handler="TestHandler"
        )
        
        assert len(corrections) == 2
        assert corrections[0].original_word == "hello"
        assert corrections[0].corrected_word == "hi"
        assert corrections[1].original_word == "world"
        assert corrections[1].corrected_word == ""
        assert corrections[1].is_deletion

    def test_calculate_reference_positions_no_preceding_anchor(self, sample_anchor_sequences):
        """Test calculating positions when no preceding anchor exists."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,  # No preceding anchor
            following_anchor_id="anchor_2",
        )
        
        result = WordOperations.calculate_reference_positions(
            gap, 
            ["source1"], 
            sample_anchor_sequences
        )
        
        # Should return empty dict when no preceding anchor
        assert len(result) == 0

    def test_calculate_reference_positions_no_following_anchor(self, sample_anchor_sequences):
        """Test calculating positions when no following anchor exists."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=8,
            preceding_anchor_id="anchor_1",
            following_anchor_id=None,  # No following anchor
        )

        result = WordOperations.calculate_reference_positions(
            gap,
            ["source1"],
            sample_anchor_sequences
        )
        
        # Should calculate position based on preceding anchor (even without following anchor)
        assert "source1" in result
        assert isinstance(result["source1"], int)

    def test_calculate_reference_positions_source_not_in_anchors(self, sample_anchor_sequences):
        """Test calculating positions when source is not in anchor reference words."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source2": ["ref_word_1"]},  # Different source
            transcription_position=8,
            preceding_anchor_id="anchor_1",
            following_anchor_id="anchor_2",
        )
        
        result = WordOperations.calculate_reference_positions(
            gap, 
            ["source2"], 
            sample_anchor_sequences
        )
        
        # Should return empty dict when source not in anchors
        assert len(result) == 0

    def test_calculate_reference_positions_interpolation(self, sample_anchor_sequences):
        """Test reference position interpolation between anchors."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},
            transcription_position=5,  # Between anchors at positions 0 and 10
            preceding_anchor_id="anchor_1",
            following_anchor_id="anchor_2",
        )
        
        result = WordOperations.calculate_reference_positions(
            gap, 
            ["source1"], 
            sample_anchor_sequences
        )
        
        # Should calculate position based on anchors
        assert "source1" in result
        assert isinstance(result["source1"], int)

    def test_word_operations_is_static_class(self):
        """Test that WordOperations methods are static/class methods."""
        # Should be able to call methods without instantiation
        assert hasattr(WordOperations, 'calculate_reference_positions')
        assert hasattr(WordOperations, 'create_word_replacement_correction')
        assert hasattr(WordOperations, 'create_word_split_corrections')
        assert hasattr(WordOperations, 'create_word_combine_corrections')
        
        # Methods should be callable without instantiation
        correction = WordOperations.create_word_replacement_correction(
            "test", "fixed", 0, "manual", 0.8, "test reason", "TestHandler"
        )
        assert isinstance(correction, WordCorrection) 