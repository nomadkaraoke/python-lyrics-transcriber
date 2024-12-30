import pytest
from unittest.mock import Mock
from lyrics_transcriber.core.corrector import (
    DiffBasedCorrector,
    LyricsCorrector,
    InternetLyrics,
    CorrectionResult,
)
from lyrics_transcriber.transcribers.base_transcriber import (
    TranscriptionData,
    LyricsSegment,
    Word,
)


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def sample_transcription():
    return TranscriptionData(
        segments=[
            LyricsSegment(
                text="hello world",
                words=[
                    Word(text="hello", start_time=0.0, end_time=0.5, confidence=0.9),
                    Word(text="world", start_time=0.5, end_time=1.0, confidence=0.6),
                ],
                start_time=0.0,
                end_time=1.0,
            )
        ],
        text="hello world",
        source="test",
        metadata={"language": "en"},
    )


@pytest.fixture
def sample_internet_lyrics():
    return [InternetLyrics(text="hello earth", source="genius"), InternetLyrics(text="hello earth", source="spotify")]


class TestDiffBasedCorrector:
    @pytest.fixture
    def corrector(self, mock_logger):
        return DiffBasedCorrector(logger=mock_logger, confidence_threshold=0.7, min_anchor_confidence=0.85)

    def test_find_anchor_words(self, corrector, sample_transcription):
        anchors = corrector._find_anchor_words(sample_transcription.segments)
        assert "hello" in anchors  # Word with 0.9 confidence
        assert "world" not in anchors  # Word with 0.6 confidence

    def test_align_texts(self, corrector):
        alignments = corrector._align_texts("hello world", "hello earth")
        assert alignments == [("hello", "hello")]

    def test_create_correction_mapping(self, corrector, sample_transcription, sample_internet_lyrics):
        anchor_words = {"hello"}
        corrections = corrector._create_correction_mapping(sample_transcription, sample_internet_lyrics, anchor_words)
        assert "hello" in corrections
        assert corrections["hello"]["hello"] == 2  # Word appears in both sources

    def test_correct_full_flow(self, corrector, sample_transcription, sample_internet_lyrics):
        result = corrector.correct(
            primary_transcription=sample_transcription, reference_transcription=None, internet_lyrics=sample_internet_lyrics
        )

        assert isinstance(result, CorrectionResult)
        assert len(result.segments) == 1
        assert result.corrections_made > 0
        assert result.confidence > 0
        assert "earth" in result.source_mapping
        assert result.metadata["correction_strategy"] == "diff_based"

        # Check specific correction
        corrected_segment = result.segments[0]
        assert len(corrected_segment.words) == 2
        assert corrected_segment.words[0].text == "hello"  # Unchanged high-confidence word
        assert corrected_segment.words[1].text == "earth"  # Corrected low-confidence word

    def test_create_correction_mapping_word_not_found(self, corrector, sample_transcription):
        # Create lyrics where anchor word isn't found
        test_lyrics = [InternetLyrics(text="completely different text", source="test")]
        anchor_words = {"hello"}

        corrections = corrector._create_correction_mapping(sample_transcription, test_lyrics, anchor_words)

        # Should handle the ValueError gracefully and return empty corrections
        assert isinstance(corrections, dict)
        assert len(corrections) == 0

    def test_correct_with_reference_transcription(self, corrector, sample_transcription):
        # Create a reference transcription with different confidence scores
        reference = TranscriptionData(
            segments=[
                LyricsSegment(
                    text="hello earth",
                    words=[
                        Word(text="hello", start_time=0.0, end_time=0.5, confidence=0.95),
                        Word(text="earth", start_time=0.5, end_time=1.0, confidence=0.95),
                    ],
                    start_time=0.0,
                    end_time=1.0,
                )
            ],
            text="hello earth",
            source="reference",
            metadata={"language": "en"},
        )

        internet_lyrics = [InternetLyrics(text="hello earth", source="test")]

        result = corrector.correct(
            primary_transcription=sample_transcription, reference_transcription=reference, internet_lyrics=internet_lyrics
        )

        # Should use anchor words from both transcriptions
        assert result.metadata["anchor_words_count"] > 1
        assert result.corrections_made > 0


class TestLyricsCorrector:
    @pytest.fixture
    def corrector(self, mock_logger):
        return LyricsCorrector(logger=mock_logger)

    def test_set_input_data(self, corrector):
        transcription = TranscriptionData(segments=[], text="test", source="test")

        corrector.set_input_data(
            spotify_lyrics_text="test lyrics", genius_lyrics_text="test lyrics", transcription_data_audioshake=transcription
        )

        assert len(corrector.internet_lyrics) == 2
        assert corrector.primary_transcription == transcription
        assert corrector.reference_transcription is None

    def test_run_corrector_no_primary_transcription(self, corrector):
        with pytest.raises(ValueError, match="No primary transcription data available"):
            corrector.run_corrector()

    def test_run_corrector_full_flow(self, corrector, sample_transcription, sample_internet_lyrics):
        # Set up test data
        corrector.primary_transcription = sample_transcription
        corrector.internet_lyrics = sample_internet_lyrics

        result = corrector.run_corrector()

        assert isinstance(result, CorrectionResult)
        assert len(result.segments) > 0
        assert result.text
        assert result.confidence > 0

    def test_run_corrector_with_error(self, corrector, sample_transcription):
        # Set up a failing correction strategy
        mock_strategy = Mock()
        mock_strategy.correct.side_effect = Exception("Test error")
        corrector.correction_strategy = mock_strategy
        corrector.primary_transcription = sample_transcription

        result = corrector.run_corrector()

        # Should fall back to original transcription
        assert isinstance(result, CorrectionResult)
        assert result.segments == sample_transcription.segments
        assert result.text == sample_transcription.text
        assert result.confidence == 1.0
        assert result.corrections_made == 0

    def test_set_input_data_with_whisper(self, corrector):
        whisper_transcription = TranscriptionData(segments=[], text="test whisper", source="whisper")

        corrector.set_input_data(transcription_data_whisper=whisper_transcription)

        assert corrector.reference_transcription == whisper_transcription
