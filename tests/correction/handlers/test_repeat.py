import pytest
import logging
from lyrics_transcriber.correction.handlers.repeat import RepeatCorrectionHandler
from lyrics_transcriber.types import GapSequence, WordCorrection


@pytest.fixture
def logger():
    logger = logging.getLogger("test_repeat")
    logger.setLevel(logging.DEBUG)
    return logger


def test_cannot_handle_without_previous_corrections(logger):
    handler = RepeatCorrectionHandler(logger)
    gap = GapSequence(
        words=("test", "words"),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]},
    )

    assert not handler.can_handle(gap)


def test_handle_repeat_correction(logger):
    handler = RepeatCorrectionHandler(logger)

    # Set up previous corrections
    previous_corrections = [
        WordCorrection(
            original_word="war",
            corrected_word="waterloo",
            segment_index=0,
            word_index=0,
            confidence=0.9,
            source="genius",
            reason="Previous handler correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    # Create gap with same word
    gap = GapSequence(
        words=("war", "again"),
        transcription_position=5,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    assert corrections[0].original_word == "war"
    assert corrections[0].corrected_word == "waterloo"
    assert corrections[0].word_index == 5  # Should use gap's transcription_position
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
            word_index=0,
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
            word_index=1,
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
            word_index=2,
            confidence=0.85,
            source="genius",
            reason="Third correction",
            alternatives={},
            is_deletion=False,
        ),
    ]
    handler.set_previous_corrections(previous_corrections)

    gap = GapSequence(
        words=("word",),
        transcription_position=10,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["some"], "spotify": ["some"]},
    )

    corrections = handler.handle(gap)

    assert len(corrections) == 1
    assert corrections[0].original_word == "word"
    assert corrections[0].corrected_word == "correction2"  # Should pick most common correction
    assert corrections[0].word_index == 10


def test_ignore_low_confidence_corrections(logger):
    handler = RepeatCorrectionHandler(logger, confidence_threshold=0.8)

    # Set up previous corrections with low confidence
    previous_corrections = [
        WordCorrection(
            original_word="test",
            corrected_word="low_confidence",
            segment_index=0,
            word_index=0,
            confidence=0.6,  # Below threshold
            source="genius",
            reason="Low confidence correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    gap = GapSequence(
        words=("test",),
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["some"], "spotify": ["some"]},
    )

    corrections = handler.handle(gap)
    assert len(corrections) == 0  # Should not apply low confidence corrections


def test_case_insensitive_matching(logger):
    handler = RepeatCorrectionHandler(logger)

    previous_corrections = [
        WordCorrection(
            original_word="Word",
            corrected_word="Correction",
            segment_index=0,
            word_index=0,
            confidence=0.9,
            source="genius",
            reason="Previous correction",
            alternatives={},
            is_deletion=False,
        )
    ]
    handler.set_previous_corrections(previous_corrections)

    gap = GapSequence(
        words=("word", "WORD", "Word"),  # Different cases
        transcription_position=0,
        preceding_anchor=None,
        following_anchor=None,
        reference_words={"genius": ["some", "words"], "spotify": ["some", "words"]},
    )

    corrections = handler.handle(gap)
    assert len(corrections) == 3  # Should correct all variations
    assert all(c.corrected_word == "Correction" for c in corrections)
