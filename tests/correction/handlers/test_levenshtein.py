import pytest
import logging
from lyrics_transcriber.correction.handlers.levenshtein import LevenshteinHandler
from lyrics_transcriber.types import GapSequence


@pytest.fixture
def logger():
    logger = logging.getLogger("test_levenshtein")
    logger.setLevel(logging.DEBUG)
    return logger


def test_handle_basic_example(logger):
    handler = LevenshteinHandler(logger=logger)
    gap = GapSequence(
        words=("wold", "worde"),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["world", "words"], "spotify": ["world", "words"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 2

    assert corrections[0].original_word == "wold"
    assert corrections[0].corrected_word == "world"
    assert corrections[0].confidence > 0.8  # High confidence - small edit distance
    assert corrections[0].source == "genius, spotify"

    assert corrections[1].original_word == "worde"
    assert corrections[1].corrected_word == "words"
    assert corrections[1].confidence > 0.7


def test_handle_sound_alike_example(logger):
    handler = LevenshteinHandler(logger=logger)
    gap = GapSequence(
        words=("shush", "look", "deep"),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["search", "look", "deep"], "spotify": ["search", "look", "deep"]},
    )

    # First check if handler thinks it can handle this
    can_handle = handler.can_handle(gap)
    logger.debug(f"Can handle 'shush' -> 'search': {can_handle}")

    corrections = handler.handle(gap)
    logger.debug(f"Corrections for sound-alike example: {corrections}")

    # We expect this to fail or have very low confidence
    # as Levenshtein distance between "shush" and "search" is quite large
    assert len(corrections) <= 1  # Might not find any matches


def test_handle_disagreeing_references(logger):
    handler = LevenshteinHandler(logger=logger)
    gap = GapSequence(
        words=("worde",),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["world"], "spotify": ["words"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    assert corrections[0].confidence < 0.8  # Lower confidence due to disagreeing sources


def test_preserves_exact_matches(logger):
    handler = LevenshteinHandler(logger=logger)
    gap = GapSequence(
        words=("wold", "words", "test"),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["world", "words", "test"], "spotify": ["world", "words", "test"]},
    )

    corrections = handler.handle(gap)

    # Should only correct "wold", leaving exact matches alone
    assert len(corrections) == 1
    assert corrections[0].original_word == "wold"
    assert corrections[0].corrected_word == "world"


def test_similarity_thresholds(logger):
    handler = LevenshteinHandler(similarity_threshold=0.8, logger=logger)
    gap = GapSequence(
        words=("completely",),  # More different from reference
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["different"], "spotify": ["different"]},
    )

    # With high threshold, should not find matches
    assert handler.can_handle(gap) is False

    # Lower threshold should still not match these very different words
    handler.similarity_threshold = 0.6
    assert handler.can_handle(gap) is False

    # But should match similar words
    gap = GapSequence(
        words=("worde",),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["words"], "spotify": ["words"]},
    )
    assert handler.can_handle(gap) is True
