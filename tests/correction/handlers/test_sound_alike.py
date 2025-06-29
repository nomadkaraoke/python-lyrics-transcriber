import pytest
import logging
from lyrics_transcriber.correction.handlers.sound_alike import SoundAlikeHandler
from lyrics_transcriber.types import GapSequence

# Import test helpers for new API
from tests.test_helpers import create_handler_test_data


@pytest.fixture
def logger():
    logger = logging.getLogger("test_sound_alike")
    logger.setLevel(logging.DEBUG)
    return logger


def test_handle_phonetic_example(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["fone", "lite", "nite"],
        reference_words={"genius": ["phone", "light", "night"], "spotify": ["phone", "light", "night"]}
    )

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 3  # All words need correction

    assert corrections[0].original_word == "fone"
    assert corrections[0].corrected_word == "phone"
    assert corrections[0].original_position == 0
    assert corrections[0].confidence >= 0.7

    assert corrections[1].original_word == "lite"
    assert corrections[1].corrected_word == "light"
    assert corrections[1].original_position == 1

    assert corrections[2].original_word == "nite"
    assert corrections[2].corrected_word == "night"
    assert corrections[2].original_position == 2


def test_handle_disagreeing_references(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["fone"],
        reference_words={"genius": ["phone"], "spotify": ["foam"]}
    )

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1
    assert corrections[0].confidence < 0.7  # Lower confidence due to disagreeing sources


def test_cannot_handle_no_sound_alike_matches(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.9)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["xyz", "abc", "def"],
        reference_words={"genius": ["one", "two", "three"], "spotify": ["one", "two", "three"]}
    )

    corrections = handler.handle(gap, handler_data)
    assert len(corrections) == 0  # Should find no matches above threshold


def test_handle_preserves_exact_matches(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["fone", "light", "night"],
        reference_words={"genius": ["phone", "light", "night"], "spotify": ["phone", "light", "night"]}
    )

    corrections = handler.handle(gap, handler_data)

    # Should only correct "fone", leaving exact matches alone
    assert len(corrections) == 1
    assert corrections[0].original_word == "fone"
    assert corrections[0].corrected_word == "phone"


def test_handle_complex_sound_alike_example(logger):
    handler = SoundAlikeHandler(logger, similarity_threshold=0.7)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["relax", "your", "conscience"],
        reference_words={"genius": ["you", "relapse", "unconscious"], "spotify": ["you", "relapse", "unconscious"]}
    )

    corrections = handler.handle(gap, handler_data)
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
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["conscience"],
        reference_words={"genius": ["unconscious"], "spotify": ["unconscious"]}
    )

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1
    assert corrections[0].original_word == "conscience"
    assert corrections[0].corrected_word == "unconscious"
    assert corrections[0].confidence >= 0.65
