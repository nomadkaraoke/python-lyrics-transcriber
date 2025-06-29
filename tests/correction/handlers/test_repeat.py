import pytest
import logging
from lyrics_transcriber.correction.handlers.repeat import RepeatCorrectionHandler
from lyrics_transcriber.types import GapSequence, WordCorrection

# Import test helpers for new API
from tests.test_helpers import create_handler_test_data


@pytest.fixture
def logger():
    logger = logging.getLogger("test_repeat")
    logger.setLevel(logging.DEBUG)
    return logger


def test_cannot_handle_without_previous_corrections(logger):
    handler = RepeatCorrectionHandler(logger)
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["test", "words"],
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]}
    )

    can_handle, _ = handler.can_handle(gap, handler_data)
    assert can_handle is False


def test_handle_repeat_correction(logger):
    handler = RepeatCorrectionHandler(logger)

    # Set up previous corrections
    previous_corrections = [
        WordCorrection(
            original_word="war",
            corrected_word="waterloo",
            segment_index=0,
            original_position=0,
            confidence=0.9,
            source="genius",
            reason="Previous handler correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    # Create gap with same word
    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["war", "again"],
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]}
    )
    gap.transcription_position = 5

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1
    assert corrections[0].original_word == "war"
    assert corrections[0].corrected_word == "waterloo"
    assert corrections[0].original_position == 5  # Should use gap's transcription_position
    assert corrections[0].confidence == 0.81  # 0.9 * 0.9
    assert "previous correction" in corrections[0].reason.lower()


def test_handle_multiple_previous_corrections(logger):
    handler = RepeatCorrectionHandler(logger)

    # Set up previous corrections with same word corrected differently
    previous_corrections = [
        WordCorrection(
            original_word="word",
            corrected_word="correction1",
            segment_index=0,
            original_position=0,
            confidence=0.8,
            source="genius",
            reason="First correction",
            alternatives={},
            is_deletion=False,
        ),
        WordCorrection(
            original_word="word",
            corrected_word="correction2",
            segment_index=0,
            original_position=1,
            confidence=0.9,
            source="spotify",
            reason="Second correction",
            alternatives={},
            is_deletion=False,
        ),
        WordCorrection(
            original_word="word",
            corrected_word="correction2",
            segment_index=0,
            original_position=2,
            confidence=0.85,
            source="genius",
            reason="Third correction",
            alternatives={},
            is_deletion=False,
        ),
    ]
    handler.set_previous_corrections(previous_corrections)

    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["word"],
        reference_words={"genius": ["some"], "spotify": ["some"]}
    )
    gap.transcription_position = 10

    corrections = handler.handle(gap, handler_data)

    assert len(corrections) == 1
    assert corrections[0].original_word == "word"
    assert corrections[0].corrected_word == "correction2"  # Should pick most common correction
    assert corrections[0].original_position == 10


def test_ignore_low_confidence_corrections(logger):
    handler = RepeatCorrectionHandler(logger, confidence_threshold=0.8)

    # Set up previous corrections with low confidence
    previous_corrections = [
        WordCorrection(
            original_word="test",
            corrected_word="low_confidence",
            segment_index=0,
            original_position=0,
            confidence=0.6,  # Below threshold
            source="genius",
            reason="Low confidence correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["test"],
        reference_words={"genius": ["some"], "spotify": ["some"]}
    )

    corrections = handler.handle(gap, handler_data)
    assert len(corrections) == 0  # Should not apply low confidence corrections


def test_case_insensitive_matching(logger):
    handler = RepeatCorrectionHandler(logger)

    previous_corrections = [
        WordCorrection(
            original_word="Word",
            corrected_word="Correction",
            segment_index=0,
            original_position=0,
            confidence=0.9,
            source="genius",
            reason="Previous correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    gap, word_map, handler_data = create_handler_test_data(
        gap_word_texts=["word", "WORD", "Word"],
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]}
    )

    corrections = handler.handle(gap, handler_data)
    assert len(corrections) == 3  # Should correct all variations
    assert all(c.corrected_word == "Correction" for c in corrections)
