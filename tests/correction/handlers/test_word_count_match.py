import pytest
from lyrics_transcriber.correction.handlers.word_count_match import WordCountMatchHandler
from lyrics_transcriber.types import GapSequence, WordCorrection


def test_can_handle_single_source_match():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hello", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "world"]},
    )

    assert handler.can_handle(gap) is True


def test_can_handle_multiple_sources_agree():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hello", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "world"], "genius": ["hi", "world"]},
    )

    assert handler.can_handle(gap) is True


def test_cannot_handle_no_references():
    handler = WordCountMatchHandler()
    gap = GapSequence(words=("hello", "world"), transcription_position=5, preceding_anchor=None, following_anchor=None, reference_words={})

    assert handler.can_handle(gap) is False


def test_cannot_handle_word_count_mismatch():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hello", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "there", "world"]},
    )

    assert handler.can_handle(gap) is False


def test_cannot_handle_sources_disagree():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hello", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "world"], "genius": ["hello", "there"]},
    )

    assert handler.can_handle(gap) is False


def test_handle_creates_corrections():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hello", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "world"], "genius": ["hi", "world"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1  # Only "hello" -> "hi" needs correction
    correction = corrections[0]
    assert correction.original_word == "hello"
    assert correction.corrected_word == "hi"
    assert correction.word_index == 5
    assert correction.confidence == 1.0
    assert correction.source == "spotify, genius"
    assert correction.reason == "Reference sources had same word count as gap"


def test_handle_no_corrections_needed():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("hi", "world"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"spotify": ["hi", "world"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 0  # No corrections needed as words match


def test_handle_real_world_example():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("gotta",),
        transcription_position=11,
        preceding_anchor=None,  # We don't need to populate these for this test
        following_anchor=None,  # since they aren't used by this handler
        reference_words={"genius": ["can"], "spotify": ["can"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    correction = corrections[0]
    assert correction.original_word == "gotta"
    assert correction.corrected_word == "can"
    assert correction.word_index == 11
    assert correction.confidence == 1.0
    assert correction.source == "genius, spotify"
    assert correction.reason == "Reference sources had same word count as gap"


def test_cannot_handle_real_world_disagreement():
    handler = WordCountMatchHandler()
    gap = GapSequence(
        words=("martyr", "youre", "a"),
        transcription_position=3,
        preceding_anchor=None,  # Not needed for this test
        following_anchor=None,
        reference_words={"genius": ["martyr"], "spotify": ["mother"]},
    )

    assert handler.can_handle(gap) is False
