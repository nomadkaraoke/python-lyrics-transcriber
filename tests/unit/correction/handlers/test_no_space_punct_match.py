import pytest
from unittest.mock import Mock, patch
import logging

from lyrics_transcriber.correction.handlers.no_space_punct_match import NoSpacePunctuationMatchHandler
from lyrics_transcriber.types import GapSequence, Word, WordCorrection


class TestNoSpacePunctuationMatchHandler:
    """Test cases for NoSpacePunctuationMatchHandler class."""

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def handler(self, mock_logger):
        """Handler instance for testing."""
        return NoSpacePunctuationMatchHandler(mock_logger)

    @pytest.fixture
    def handler_no_logger(self):
        """Handler instance without logger."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            return NoSpacePunctuationMatchHandler()

    @pytest.fixture
    def word_map(self):
        """Sample word map for testing."""
        return {
            "gap_word_1": Word(id="gap_word_1", text="don't", start_time=0.0, end_time=1.0),
            "gap_word_2": Word(id="gap_word_2", text="know", start_time=1.0, end_time=2.0),
            "gap_word_3": Word(id="gap_word_3", text="what's", start_time=2.0, end_time=3.0),
            "gap_word_4": Word(id="gap_word_4", text="up", start_time=3.0, end_time=4.0),
            "ref_word_1": Word(id="ref_word_1", text="dont", start_time=0.0, end_time=1.0),
            "ref_word_2": Word(id="ref_word_2", text="know", start_time=1.0, end_time=2.0),
            "ref_word_3": Word(id="ref_word_3", text="whats", start_time=2.0, end_time=3.0),
            "ref_word_4": Word(id="ref_word_4", text="up", start_time=3.0, end_time=4.0),
            "different_word": Word(id="different_word", text="completely", start_time=4.0, end_time=5.0),
        }

    @pytest.fixture
    def sample_gap(self):
        """Sample gap sequence for testing."""
        return GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )

    def test_init(self, mock_logger):
        """Test handler initialization."""
        handler = NoSpacePunctuationMatchHandler(mock_logger)
        assert handler.logger == mock_logger

    def test_init_without_logger(self):
        """Test handler initialization without logger."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            handler = NoSpacePunctuationMatchHandler()
            assert handler.logger == mock_logger

    def test_remove_spaces_and_punct(self, handler):
        """Test _remove_spaces_and_punct method."""
        # Test basic functionality
        assert handler._remove_spaces_and_punct(["don't", "know"]) == "dontknow"
        assert handler._remove_spaces_and_punct(["what's", "up?"]) == "whatsup"
        assert handler._remove_spaces_and_punct(["Hello,", "World!"]) == "helloworld"
        
        # Test with various punctuation
        assert handler._remove_spaces_and_punct(["it's", "a", "test..."]) == "itsatest"
        assert handler._remove_spaces_and_punct(["(test)", "[brackets]"]) == "testbrackets"
        
        # Test case insensitive
        assert handler._remove_spaces_and_punct(["HELLO"]) == "hello"

    def test_can_handle_no_reference_words(self, handler, word_map):
        """Test can_handle when no reference word IDs are available."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    def test_can_handle_no_word_map(self, handler, sample_gap):
        """Test can_handle when no word_map is provided."""
        can_handle, data = handler.can_handle(sample_gap, {})
        assert not can_handle
        assert data == {}
        
        can_handle, data = handler.can_handle(sample_gap, None)
        assert not can_handle
        assert data == {}

    def test_can_handle_missing_word_id(self, handler, word_map):
        """Test can_handle when word ID is missing from word_map."""
        gap = GapSequence(
            transcribed_word_ids=["missing_word_id"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    def test_can_handle_missing_reference_word_id(self, handler, word_map):
        """Test can_handle when reference word ID is missing from word_map."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["missing_ref_word"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    def test_can_handle_matching_text(self, handler, word_map):
        """Test can_handle when text matches after removing spaces and punctuation."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],  # "don't know"
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},  # "dont know"
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert can_handle
        assert data["matching_source"] == "source1"
        assert data["reference_word_ids"] == ["ref_word_1", "ref_word_2"]
        assert data["word_map"] == word_map

    def test_can_handle_no_matching_text(self, handler, word_map):
        """Test can_handle when text doesn't match."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],  # "don't"
            reference_word_ids={"source1": ["different_word"]},  # "completely"
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    def test_can_handle_multiple_sources_with_match(self, handler, word_map):
        """Test can_handle with multiple sources where one matches."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],  # "don't"
            reference_word_ids={
                "source1": ["different_word"],  # "completely" - no match
                "source2": ["ref_word_1"],  # "dont" - matches
            },
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert can_handle
        assert data["matching_source"] == "source2"

    def test_handle_without_data(self, handler, word_map):
        """Test handle method when data is not provided."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        with patch.object(handler, 'can_handle', return_value=(False, {})):
            corrections = handler.handle(gap)
            assert corrections == []

    def test_handle_combine_multiple_to_one(self, handler, word_map):
        """Test handle method when combining multiple transcribed words to one reference word."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],  # "don't know"
            reference_word_ids={"source1": ["ref_word_1"]},  # "dont"
            transcription_position=5,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_combine_corrections') as mock_combine:
                mock_combine.return_value = [Mock(spec=WordCorrection)]
                
                corrections = handler.handle(gap, data)
                
                assert len(corrections) == 1
                mock_combine.assert_called_once_with(
                    original_words=["don't", "know"],
                    reference_word="dont",
                    original_position=5,
                    source="source1",
                    confidence=1.0,
                    combine_reason="Words combined based on text match",
                    delete_reason="Word removed as part of text match combination",
                    reference_positions={},
                    handler="NoSpacePunctuationMatchHandler",
                    original_word_ids=["gap_word_1", "gap_word_2"],
                    corrected_word_id="ref_word_1",
                )

    def test_handle_split_one_to_multiple(self, handler, word_map):
        """Test handle method when splitting one transcribed word to multiple reference words."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],  # "don't"
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},  # "dont know"
            transcription_position=3,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1", "ref_word_2"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_split_corrections') as mock_split:
                mock_split.return_value = [Mock(spec=WordCorrection), Mock(spec=WordCorrection)]
                
                corrections = handler.handle(gap, data)
                
                assert len(corrections) == 2
                mock_split.assert_called_once_with(
                    original_word="don't",
                    reference_words=["dont", "know"],
                    original_position=3,
                    source="source1",
                    confidence=1.0,
                    reason="Split word based on text match",
                    reference_positions={},
                    handler="NoSpacePunctuationMatchHandler",
                    original_word_id="gap_word_1",
                    corrected_word_ids=["ref_word_1", "ref_word_2"],
                )

    def test_handle_one_to_one_replacement(self, handler, word_map):
        """Test handle method for one-to-one word replacement."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],  # "don't know"
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},  # "dont know"
            transcription_position=7,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1", "ref_word_2"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_replacement_correction') as mock_replacement:
                mock_replacement.return_value = Mock(spec=WordCorrection)
                
                corrections = handler.handle(gap, data)
                
                # Only "don't" -> "dont" should be corrected, "know" -> "know" should be skipped
                assert len(corrections) == 1
                mock_replacement.assert_called_once_with(
                    original_word="don't",
                    corrected_word="dont",
                    original_position=7,
                    source="source1",
                    confidence=1.0,
                    reason="Source 'source1' matched when spaces and punctuation removed",
                    reference_positions={},
                    handler="NoSpacePunctuationMatchHandler",
                    original_word_id="gap_word_1",
                    corrected_word_id="ref_word_1",
                )

    def test_handle_one_to_one_no_corrections_needed(self, handler, word_map):
        """Test handle method when words already match exactly."""
        # Create gap where transcribed and reference words are identical
        gap = GapSequence(
            transcribed_word_ids=["ref_word_2"],  # "know"
            reference_word_ids={"source1": ["ref_word_2"]},  # "know"
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_2"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            corrections = handler.handle(gap, data)
            
            # No corrections should be needed since words are identical
            assert corrections == []

    def test_handle_logs_debug_messages(self, handler, word_map):
        """Test that handle method logs appropriate debug messages."""
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_combine_corrections', return_value=[]):
                handler.handle(gap, data)
                
                handler.logger.debug.assert_called_with("Combined words into 'dont'.")

    def test_inheritance_from_base_handler(self, handler):
        """Test that handler inherits from GapCorrectionHandler."""
        from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
        assert isinstance(handler, GapCorrectionHandler) 