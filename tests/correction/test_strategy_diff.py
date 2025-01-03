import pytest
from unittest.mock import Mock
from lyrics_transcriber.correction.strategy_diff import DiffBasedCorrector
from lyrics_transcriber.transcribers.base_transcriber import (
    TranscriptionData,
    TranscriptionResult,
    LyricsSegment,
    Word,
)
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsData, LyricsMetadata
from lyrics_transcriber.correction.anchor_sequence import (
    AnchorSequenceFinder,
    AnchorSequence,
    GapSequence,
)


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        {"text": "cruel", "start": 0.5, "end": 1.0},
        {"text": "world", "start": 1.0, "end": 1.5},
    ]

    segment = LyricsSegment(
        text="hello cruel world",
        words=[Word(text=w["text"], start_time=w["start"], end_time=w["end"]) for w in words],
        start_time=0.0,
        end_time=1.5,
    )

    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],
            text="hello cruel world",
            source="test",
            words=words,
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    return [
        LyricsData(
            source="source1",
            lyrics="hello beautiful world",
            segments=[],
            metadata=LyricsMetadata(source="genius", track_name="test track", artist_names="test artist"),
        ),
        LyricsData(
            source="source2",
            lyrics="hello beautiful world",
            segments=[],
            metadata=LyricsMetadata(source="musixmatch", track_name="test track", artist_names="test artist"),
        ),
    ]


@pytest.fixture
def mock_anchor_finder(mock_logger):
    finder = Mock()

    # Create anchor sequences for "hello" and "world"
    anchor1 = AnchorSequence(words=["hello"], transcription_position=0, reference_positions={"source1": 0, "source2": 0}, confidence=1.0)

    anchor2 = AnchorSequence(words=["world"], transcription_position=2, reference_positions={"source1": 2, "source2": 2}, confidence=1.0)

    # Create gap sequence for "cruel" vs "beautiful"
    gap = GapSequence(
        words=["cruel"],
        transcription_position=1,
        preceding_anchor=anchor1,
        following_anchor=anchor2,
        reference_words={"source1": ["beautiful"], "source2": ["beautiful"]},
    )

    finder.find_anchors.return_value = [anchor1, anchor2]
    finder.find_gaps.return_value = [gap]

    return finder


class TestDiffBasedCorrector:
    @pytest.fixture
    def corrector(self, mock_logger, mock_anchor_finder):
        return DiffBasedCorrector(logger=mock_logger, anchor_finder=mock_anchor_finder)

    def test_preserve_formatting(self, corrector):
        assert corrector._preserve_formatting(" hello ", "world") == " world "
        assert corrector._preserve_formatting("hello", "world") == "world"
        assert corrector._preserve_formatting(" hello", "world") == " world"
        assert corrector._preserve_formatting("hello ", "world") == "world "

    def test_correct_with_matching_gap_length(self, corrector, sample_transcription_result, sample_lyrics):
        result = corrector.correct(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
        )

        # Verify the correction was made
        assert len(result.corrected_segments) == 1
        assert result.corrections_made == 1
        assert result.confidence > 0

        # Check specific correction
        corrected_segment = result.corrected_segments[0]
        assert len(corrected_segment.words) == 3
        assert corrected_segment.words[0].text == "hello"  # Anchor (unchanged)
        assert corrected_segment.words[1].text == "beautiful"  # Gap (corrected)
        assert corrected_segment.words[2].text == "world"  # Anchor (unchanged)

        # Check metadata
        assert result.metadata["correction_strategy"] == "gap_based"
        assert result.metadata["anchor_sequences_count"] == 2
        assert result.metadata["gap_sequences_count"] == 1

    def test_no_correction_when_sources_disagree(self, corrector, sample_transcription_result, sample_lyrics, mock_anchor_finder):
        # Modify mock to make sources disagree
        gap = mock_anchor_finder.find_gaps.return_value[0]
        gap.reference_words = {"source1": ["beautiful"], "source2": ["wonderful"]}

        result = corrector.correct(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
        )

        # Verify no correction was made
        assert len(result.corrected_segments) == 1
        assert result.corrections_made == 0
        assert result.corrected_segments[0].words[1].text == "cruel"  # Original word preserved

    def test_no_correction_when_length_mismatch(self, corrector, sample_transcription_result, sample_lyrics, mock_anchor_finder):
        # Modify mock to make reference words longer than gap
        gap = mock_anchor_finder.find_gaps.return_value[0]
        gap.reference_words = {"source1": ["very", "beautiful"], "source2": ["very", "beautiful"]}

        result = corrector.correct(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
        )

        # Verify no correction was made
        assert len(result.corrected_segments) == 1
        assert result.corrections_made == 0
        assert result.corrected_segments[0].words[1].text == "cruel"  # Original word preserved
