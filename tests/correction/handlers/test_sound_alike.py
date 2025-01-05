import pytest
import logging
from lyrics_transcriber.correction.handlers.sound_alike import SoundAlikeHandler
from lyrics_transcriber.types import GapSequence


@pytest.fixture
def logger():
    logger = logging.getLogger("test_sound_alike")
    logger.setLevel(logging.DEBUG)
    return logger


def test_handle_phonetic_example(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap = GapSequence(
        words=("fone", "lite", "nite"),  # Common phonetic misspellings
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["phone", "light", "night"], "spotify": ["phone", "light", "night"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 3  # All words need correction

    assert corrections[0].original_word == "fone"
    assert corrections[0].corrected_word == "phone"
    assert corrections[0].word_index == 0
    assert corrections[0].confidence >= 0.7

    assert corrections[1].original_word == "lite"
    assert corrections[1].corrected_word == "light"
    assert corrections[1].word_index == 1

    assert corrections[2].original_word == "nite"
    assert corrections[2].corrected_word == "night"
    assert corrections[2].word_index == 2


def test_handle_disagreeing_references(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap = GapSequence(
        words=("fone",),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["phone"], "spotify": ["foam"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    assert corrections[0].confidence < 0.7  # Lower confidence due to disagreeing sources


def test_cannot_handle_no_sound_alike_matches(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.9)
    gap = GapSequence(
        words=("xyz", "abc", "def"),  # Use words with completely different phonetic codes
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["one", "two", "three"], "spotify": ["one", "two", "three"]},
    )

    corrections = handler.handle(gap)
    assert len(corrections) == 0  # Should find no matches above threshold


def test_handle_preserves_exact_matches(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap = GapSequence(
        words=("fone", "light", "night"),  # middle and last words exact matches
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["phone", "light", "night"], "spotify": ["phone", "light", "night"]},
    )

    corrections = handler.handle(gap)

    # Should only correct "fone", leaving exact matches alone
    assert len(corrections) == 1
    assert corrections[0].original_word == "fone"
    assert corrections[0].corrected_word == "phone"


def test_handle_complex_sound_alike_example(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap = GapSequence(
        words=("relax", "your", "conscience"),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={
            "genius": ["you", "relapse", "unconscious"],
            "spotify": ["you", "relapse", "unconscious"],
        },
    )

    corrections = handler.handle(gap)
    assert len(corrections) == 3  # Should find all three matches
    
    # Check specific corrections
    assert corrections[0].original_word == "relax"
    assert corrections[0].corrected_word == "relapse"
    assert corrections[0].confidence >= 0.7
    
    assert corrections[1].original_word == "your"
    assert corrections[1].corrected_word == "you"
    assert corrections[1].confidence >= 0.7
    
    assert corrections[2].original_word == "conscience"
    assert corrections[2].corrected_word == "unconscious"
    assert corrections[2].confidence >= 0.7


def test_handle_substring_code_match(logger):
    """Test the substring code matching."""
    handler = SoundAlikeHandler(logger, similarity_threshold=0.65)
    gap = GapSequence(
        words=("conscience",),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["unconscious"], "spotify": ["unconscious"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    assert corrections[0].original_word == "conscience"
    assert corrections[0].corrected_word == "unconscious"
    assert corrections[0].confidence >= 0.65
