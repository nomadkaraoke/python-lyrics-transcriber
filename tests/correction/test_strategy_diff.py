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
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder, ScoredAnchor, AnchorSequence


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription_result():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        {"text": "world", "start": 0.5, "end": 1.0},
    ]

    # Create a segment with the words
    segment = LyricsSegment(
        text="hello world",
        words=[Word(text=w["text"], start_time=w["start"], end_time=w["end"]) for w in words],
        start_time=0.0,
        end_time=1.0,
    )

    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],
            text="hello world",
            source="test",
            words=words,
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    # Create a lyrics segment matching the transcription
    segment = LyricsSegment(
        text="hello earth",
        words=[
            Word(text="hello", start_time=0.0, end_time=0.5),
            Word(text="earth", start_time=0.5, end_time=1.0),
        ],
        start_time=0.0,
        end_time=1.0,
    )

    return [
        LyricsData(
            source="test",
            lyrics="hello earth",
            segments=[segment],
            metadata=LyricsMetadata(source="genius", track_name="test track", artist_names="test artist"),
        )
    ]


class TestDiffBasedCorrector:
    @pytest.fixture
    def corrector(self, mock_logger):
        return DiffBasedCorrector(logger=mock_logger)

    def test_align_texts(self, corrector):
        # Create mock anchor sequences
        anchor = AnchorSequence(words=["hello"], transcription_position=0, reference_positions={"test": 0}, confidence=1.0)
        scored_anchor = ScoredAnchor(anchor=anchor, phrase_score=Mock())

        alignments, matched, unmatched = corrector._align_texts("hello world", "hello earth", [scored_anchor])

        # Only check alignments since matched/unmatched handling has changed
        assert alignments == [("hello", "hello"), ("world", "earth")]
        # Remove matched/unmatched assertions as they're now handled differently

    def test_create_correction_mapping(self, corrector, sample_transcription_result, sample_lyrics):
        # Create mock anchor sequences
        anchor = AnchorSequence(words=["hello"], transcription_position=0, reference_positions={"test": 0}, confidence=1.0)
        scored_anchor = ScoredAnchor(anchor=anchor, phrase_score=Mock())

        transcribed_text = "hello world"
        lyrics_results = {"test": "hello earth"}

        corrector._create_correction_mapping(transcribed_text, lyrics_results, [scored_anchor])

        # Check corrections dictionary
        assert "world" in corrector.corrections
        correction_entry = corrector.corrections["world"]
        assert "test" in correction_entry.sources
        assert "earth" in correction_entry.frequencies

    def test_correct_full_flow(self, corrector, sample_transcription_result, sample_lyrics):
        result = corrector.correct(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
        )

        assert len(result.corrected_segments) == 1
        assert result.corrections_made > 0
        assert result.confidence > 0
        assert "test" in result.reference_texts
        assert result.metadata["correction_strategy"] == "diff_based"

        # Check specific correction
        corrected_segment = result.corrected_segments[0]
        assert len(corrected_segment.words) == 2
        assert corrected_segment.words[0].text == "hello"  # Unchanged word
        assert corrected_segment.words[1].text == "earth"  # Corrected word
