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

    def test_find_anchor_words(self, corrector, sample_transcription_result):
        anchors = corrector._find_anchor_words(sample_transcription_result.result.segments)
        assert "hello" in anchors  # Longer word
        assert "world" in anchors  # Longer word

    def test_align_texts(self, corrector):
        alignments = corrector._align_texts("hello world", "hello earth")
        # Should return both matching and non-matching pairs
        assert len(alignments) == 2
        assert alignments == [
            ("hello", "hello"),  # Matching pair
            ("world", "earth"),  # Non-matching pair
        ]

    def test_create_correction_mapping(self, corrector, sample_transcription_result, sample_lyrics):
        # Test with more explicit differences
        transcription = sample_transcription_result.result
        transcription.text = "hello world"  # Make sure text matches segments
        lyrics = sample_lyrics[0]
        lyrics.lyrics = "hello earth"  # Make sure lyrics text matches segments

        anchor_words = {"hello"}
        corrections = corrector._create_correction_mapping(transcription, sample_lyrics, anchor_words)

        # Debug output
        print(f"Transcription text: {transcription.text}")
        print(f"Lyrics text: {lyrics.lyrics}")
        print(f"Alignments: {corrector._align_texts(transcription.text, lyrics.lyrics)}")
        print(f"Corrections: {corrections}")

        # The correction mapping should contain 'world' as a key since it differs between sources
        assert "world" in corrections
        # 'earth' should be a suggested correction for 'world'
        assert "earth" in corrections["world"]
        # 'hello' should not be in corrections as it's identical in both sources
        assert "hello" not in corrections

    def test_correct_full_flow(self, corrector, sample_transcription_result, sample_lyrics):
        # Ensure texts are properly set
        sample_transcription_result.result.text = "hello world"
        sample_lyrics[0].lyrics = "hello earth"

        result = corrector.correct(
            transcription_results=[sample_transcription_result],
            lyrics_results=sample_lyrics,
        )

        # Debug output
        print(f"Result: {result}")
        print(f"Segments: {result.segments}")
        print(f"Corrections made: {result.corrections_made}")
        print(f"Source mapping: {result.source_mapping}")

        assert len(result.segments) == 1
        assert result.corrections_made > 0
        assert result.confidence > 0
        assert "earth" in result.source_mapping
        assert result.metadata["correction_strategy"] == "diff_based"

        # Check specific correction
        corrected_segment = result.segments[0]
        assert len(corrected_segment.words) == 2
        assert corrected_segment.words[0].text == "hello"  # Unchanged word
        assert corrected_segment.words[1].text == "earth"  # Corrected word
