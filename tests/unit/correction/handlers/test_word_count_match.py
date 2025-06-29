import pytest
from lyrics_transcriber.correction.handlers.word_count_match import WordCountMatchHandler
from lyrics_transcriber.types import GapSequence, WordCorrection

# Import test helpers for new API
from tests.test_helpers import create_handler_test_data


def test_can_handle_single_source_match():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={"spotify": ["hi", "world"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is True


def test_can_handle_multiple_sources_agree():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={"spotify": ["hi", "world"], "genius": ["hi", "world"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is True


def test_cannot_handle_no_references():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is False


def test_cannot_handle_word_count_mismatch():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={"spotify": ["hi", "there", "world"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is False


def test_cannot_handle_sources_disagree():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={"spotify": ["hi", "world"], "genius": ["hello", "there"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is False


def test_handle_creates_corrections():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hello", "world"],
        reference_words={"spotify": ["hi", "world"], "genius": ["hi", "world"]}
    )

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1  # Only "hello" -> "hi" needs correction
    correction = corrections[0]
    assert correction.original_word == "hello"
    assert correction.corrected_word == "hi"
    # Position is gap.transcription_position + index (0 by default + 0 for first word)
    assert correction.original_position == 0
    assert correction.confidence == 1.0
    assert correction.source == "spotify, genius"
    assert correction.reason == "Reference sources had same word count as gap"


def test_handle_no_corrections_needed():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["hi", "world"],
        reference_words={"spotify": ["hi", "world"]}
    )

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 0  # No corrections needed as words match


def test_handle_real_world_example():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["gotta"],
        reference_words={"genius": ["can"], "spotify": ["can"]}
    )
    
    # Update the gap to have the desired transcription position
    gap.transcription_position = 11

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1
    correction = corrections[0]
    assert correction.original_word == "gotta"
    assert correction.corrected_word == "can"
    assert correction.original_position == 11
    assert correction.confidence == 1.0
    assert correction.source == "genius, spotify"
    assert correction.reason == "Reference sources had same word count as gap"


def test_cannot_handle_real_world_disagreement():
    handler = WordCountMatchHandler()
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["martyr", "youre", "a"],
        reference_words={"genius": ["martyr"], "spotify": ["mother"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is False
