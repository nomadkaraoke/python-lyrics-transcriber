import pytest
from lyrics_transcriber.correction.handlers.extend_anchor import ExtendAnchorHandler
from lyrics_transcriber.types import GapSequence, WordCorrection

# Import test helpers for new API
from tests.test_helpers import create_handler_test_data


class TestExtendAnchorHandler:
    def test_can_handle_real_world_example(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["martyr", "youre", "a"],
            reference_words={"genius": ["martyr"], "spotify": ["martyr"]}
        )

        can_handle, _ = handler.can_handle(gap, handler_data)
        assert can_handle is True

    def test_handle_real_world_example(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["martyr", "youre", "a"],
            reference_words={"genius": ["martyr"], "spotify": ["martyr"]}
        )

        corrections = handler.handle(gap, handler_data)

        assert len(corrections) == 1  # Just validate the matching word

        # First word matches reference, validate it
        assert corrections[0].original_word == "martyr"
        assert corrections[0].corrected_word == "martyr"
        assert corrections[0].is_deletion is False
        assert corrections[0].original_position == 0  # gap.transcription_position (0) + index (0)
        assert corrections[0].confidence == 1.0  # Full confidence as sources agree

    def test_cannot_handle_no_reference(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["hello", "world"],
            reference_words={}
        )

        can_handle, _ = handler.can_handle(gap, handler_data)
        assert can_handle is False

    def test_cannot_handle_no_matching_words(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["hello", "world", "test"],
            reference_words={"genius": ["hi"], "spotify": ["hi"]}
        )

        can_handle, _ = handler.can_handle(gap, handler_data)
        assert can_handle is False

    def test_handle_with_matching_first_word(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["hello", "extra", "world"],
            reference_words={"genius": ["hello"], "spotify": ["hello"]}
        )

        corrections = handler.handle(gap, handler_data)

        assert len(corrections) == 1  # Just validate the matching word
        # First word matches reference, validate it
        assert corrections[0].original_word == "hello"
        assert corrections[0].corrected_word == "hello"
        assert corrections[0].is_deletion is False
        assert corrections[0].confidence == 1.0

    def test_handle_real_world_disagreeing_references(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["martyr", "youre", "a"],
            reference_words={"genius": ["martyr"], "spotify": ["mother"]}
        )
        
        # Update gap position for test
        gap.transcription_position = 3
        
        # First verify we can handle this case
        can_handle, _ = handler.can_handle(gap, handler_data)
        assert can_handle is True
        
        corrections = handler.handle(gap, handler_data)
        
        assert len(corrections) == 1  # Just validate the matching word
        
        # First word matches one reference source - validate but don't change
        assert corrections[0].original_word == "martyr"
        assert corrections[0].corrected_word == "martyr"
        assert corrections[0].is_deletion is False
        assert corrections[0].original_position == 3
        assert corrections[0].confidence == 0.5  # Lower confidence due to disagreeing sources
        assert corrections[0].source == "genius"  # Only the matching source
        assert "Matched reference" in corrections[0].reason

    def test_handle_multiple_matching_words(self):
        handler = ExtendAnchorHandler()
        gap, word_map, handler_data = create_handler_test_data(
            gap_word_texts=["hello", "world", "extra", "words"],
            reference_words={"genius": ["hello", "world"], "spotify": ["hello", "world"]}
        )
        
        corrections = handler.handle(gap, handler_data)
        
        # Should:
        # 1. Validate "hello"
        # 2. Validate "world"
        # 3. Leave "extra" unchanged
        # 4. Leave "words" unchanged
        assert len(corrections) == 2  # Only the validations
        
        # First two words should be validated
        assert corrections[0].original_word == "hello"
        assert corrections[0].corrected_word == "hello"
        assert corrections[0].is_deletion is False
        assert corrections[0].confidence == 1.0
        
        assert corrections[1].original_word == "world"
        assert corrections[1].corrected_word == "world"
        assert corrections[1].is_deletion is False
        assert corrections[1].confidence == 1.0
