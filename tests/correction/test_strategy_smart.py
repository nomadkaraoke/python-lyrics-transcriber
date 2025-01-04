import pytest
from unittest.mock import Mock, patch
import torch


from lyrics_transcriber.types import (
    LyricsData,
    LyricsMetadata,
    LyricsSegment,
    Word,
    TranscriptionData,
    TranscriptionResult,
    GapSequence,
)

from lyrics_transcriber.correction.strategy_smart import SmartCorrectionStrategy, PhoneticMatcher, SemanticMatcher


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def mock_anchor_finder():
    finder = Mock()
    finder.find_anchors.return_value = []
    finder.find_gaps.return_value = []
    return finder


@pytest.fixture
def phonetic_matcher():
    return PhoneticMatcher()


@pytest.fixture
def semantic_matcher():
    with patch("lyrics_transcriber.correction.strategy_smart.AutoTokenizer"), patch(
        "lyrics_transcriber.correction.strategy_smart.AutoModel"
    ):
        matcher = SemanticMatcher()

        # Create more realistic mock embeddings
        def mock_embedding(text: str) -> torch.Tensor:
            # Map common phrases to specific embeddings
            embeddings = {
                "hello world": torch.tensor([[1.0, 0.8, 0.6]]),
                "hi world": torch.tensor([[0.9, 0.7, 0.5]]),
                "goodbye universe": torch.tensor([[-0.8, -0.6, -0.4]]),
                "how are you": torch.tensor([[0.8, 0.6, 0.4]]),
                "how're you doing": torch.tensor([[0.7, 0.5, 0.3]]),
                "what is the weather": torch.tensor([[-0.7, -0.5, -0.3]]),
                "i love music": torch.tensor([[0.9, 0.7, 0.5]]),
                "music is my passion": torch.tensor([[0.8, 0.6, 0.4]]),
                "i hate noise": torch.tensor([[-0.9, -0.7, -0.5]]),
            }

            # Return matching embedding or default
            return embeddings.get(text.lower(), torch.tensor([[0.1, 0.1, 0.1]]))

        matcher.get_embedding = Mock(side_effect=mock_embedding)
        return matcher


@pytest.fixture
def sample_transcription():
    words = [
        Word(text="hello", start_time=0.0, end_time=0.5),
        Word(text="wurld", start_time=0.5, end_time=1.0),
    ]
    segment = LyricsSegment(
        text="hello wurld",
        words=words,
        start_time=0.0,
        end_time=1.0,
    )
    return TranscriptionResult(
        name="test",
        priority=1,
        result=TranscriptionData(
            segments=[segment],
            text="hello wurld",
            source="test",
            words=[{"text": w.text, "start": w.start_time, "end": w.end_time} for w in words],
            metadata={"language": "en"},
        ),
    )


@pytest.fixture
def sample_lyrics():
    # Create a basic word
    word = Word(text="world", start_time=0.5, end_time=1.0)

    # Create a lyrics segment
    segment = LyricsSegment(text="hello world", words=[word], start_time=0.0, end_time=1.0)

    # Create the lyrics data objects
    return [
        LyricsData(
            lyrics="hello world",
            segments=[segment],
            metadata=LyricsMetadata(
                source="source1",
                track_name="Test Song",
                artist_names="Test Artist",
                language="en",
                provider_metadata={},
            ),
            source="source1",
        ),
        LyricsData(
            lyrics="hello world",
            segments=[segment],
            metadata=LyricsMetadata(
                source="source2",
                track_name="Test Song",
                artist_names="Test Artist",
                language="en",
                provider_metadata={},
            ),
            source="source2",
        ),
    ]


class TestPhoneticMatcher:
    def test_similar_words(self, phonetic_matcher):
        """Test phonetic matching with similar sounding words."""
        test_pairs = [
            ("hello", "helo"),
            ("world", "wurld"),
            ("beautiful", "butiful"),
        ]
        for word1, word2 in test_pairs:
            similarity = phonetic_matcher.get_similarity(word1, word2)
            print(f"\nTesting similar words: '{word1}' vs '{word2}'")
            print(f"Similarity score: {similarity:.3f}")
            assert similarity >= 0.7

    def test_different_words(self, phonetic_matcher):
        """Test phonetic matching with different sounding words."""
        test_pairs = [
            ("hello", "world"),
            ("you're", "mother"),
            ("beautiful", "ugly"),
        ]
        for word1, word2 in test_pairs:
            similarity = phonetic_matcher.get_similarity(word1, word2)
            print(f"\nTesting different words: '{word1}' vs '{word2}'")
            print(f"Similarity score: {similarity:.3f}")
            assert similarity < 0.6


class TestSemanticMatcher:
    def test_similar_phrases(self, semantic_matcher):
        """Test semantic matching with similar meaning phrases."""
        test_pairs = [
            ("hello world", "hi world"),
            ("how are you", "how're you doing"),
            ("I love music", "music is my passion"),
        ]
        for phrase1, phrase2 in test_pairs:
            similarity = semantic_matcher.get_similarity(phrase1, phrase2)
            print(f"\nTesting similar phrases: '{phrase1}' vs '{phrase2}'")
            print(f"Similarity score: {similarity:.3f}")
            assert similarity >= 0.7

    def test_different_phrases(self, semantic_matcher):
        """Test semantic matching with different meaning phrases."""
        test_pairs = [
            ("hello world", "goodbye universe"),
            ("I love music", "I hate noise"),
            ("how are you", "what is the weather"),
        ]
        for phrase1, phrase2 in test_pairs:
            similarity = semantic_matcher.get_similarity(phrase1, phrase2)
            print(f"\nTesting different phrases: '{phrase1}' vs '{phrase2}'")
            print(f"Similarity score: {similarity:.3f}")
            assert similarity < 0.5


class TestSmartCorrectionStrategy:
    def test_phrase_matching(self, mock_logger, mock_anchor_finder):
        """Test the combined phrase matching approach."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["world"],
                "source2": ["world"],
            },
        )

        match = strategy._find_best_phrase_match(gap, {"source1": "hello world", "source2": "hello world"})
        assert match is not None
        assert match.reference_phrase == "world"
        assert match.combined_score >= 0.7

    def test_correction_with_similar_words(self, mock_logger, mock_anchor_finder, sample_transcription, sample_lyrics):
        """Test correction of similar sounding words."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a more complete gap sequence
        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,  # Position of "wurld" in the transcription
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["world"],
                "source2": ["world"],
            },
            corrections=[],  # Initialize empty corrections list
        )

        # Set up mock anchor finder to return our gap
        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        # Mock both matchers to return high similarity scores
        with patch.object(strategy.phonetic_matcher, "get_similarity", return_value=0.8), patch.object(
            strategy.semantic_matcher, "get_similarity", return_value=0.8
        ):

            print("\nDebug: Starting test")
            print(f"Sample transcription: {sample_transcription.result.segments[0].words}")
            print(f"Sample lyrics: {sample_lyrics[0].lyrics}")

            result = strategy.correct([sample_transcription], sample_lyrics)

            # Debug output
            print("\nDebug information:")
            print(f"Gap sequences: {result.gap_sequences}")
            print(f"Corrections: {result.corrections}")
            print(f"Corrections made: {result.corrections_made}")
            print(f"Confidence: {result.confidence}")
            print(f"Metadata: {result.metadata}")

            # Additional debug for gap processing
            for gap in result.gap_sequences:
                print(f"\nProcessing gap:")
                print(f"Gap words: {gap.words}")
                print(f"Gap position: {gap.transcription_position}")
                print(f"Reference words: {gap.reference_words}")
                print(f"Corrections: {gap.corrections}")

            assert len(result.corrections) == 1, "Expected one correction"
            assert (
                result.corrections[0].original_word == "wurld"
            ), f"Expected 'wurld', got {result.corrections[0].original_word if result.corrections else 'no correction'}"
            assert result.corrections[0].corrected_word == "world"
            assert result.corrections[0].confidence >= 0.7
            assert result.corrections_made == 1
            assert result.confidence > 0

    def test_no_correction_for_different_words(self, mock_logger, mock_anchor_finder):
        """Test that very different words aren't corrected."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        gap = GapSequence(
            words=["you're"],
            transcription_position=0,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["mother"],
                "source2": ["mother"],
            },
        )

        match = strategy._find_best_phrase_match(gap, {"source1": "mother", "source2": "mother"})
        assert match is None or match.combined_score < strategy.combined_threshold

    def test_find_best_phrase_match(self, mock_logger, mock_anchor_finder):
        """Test the phrase matching logic directly."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        gap = GapSequence(
            words=["wurld"],
            transcription_position=0,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["world"],
                "source2": ["world"],
            },
            corrections=[],
        )

        # Mock both matchers to return known values
        with patch.object(strategy.phonetic_matcher, "get_similarity", return_value=0.8), patch.object(
            strategy.semantic_matcher, "get_similarity", return_value=0.8
        ):

            match = strategy._find_best_phrase_match(gap, {"source1": "world", "source2": "world"})

            print("\nDebug information:")
            print(f"Match result: {match}")
            if match:
                print(f"Phonetic score: {match.phonetic_score}")
                print(f"Semantic score: {match.semantic_score}")
                print(f"Combined score: {match.combined_score}")

            assert match is not None
            assert match.reference_phrase == "world"
            assert match.combined_score >= 0.7

    def test_empty_reference_words(self, mock_logger, mock_anchor_finder, sample_transcription):
        """Test handling of gaps with empty reference words."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a gap with empty reference words
        gap = GapSequence(
            words=["problematic"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={},  # Empty reference words
            corrections=[],
        )

        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        result = strategy.correct([sample_transcription], [])

        assert len(result.corrections) == 0, "Should not make corrections when reference words are empty"
        assert result.corrections_made == 0

    def test_empty_source_words(self, mock_logger, mock_anchor_finder, sample_transcription):
        """Test handling of gaps where sources have empty word lists."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a gap with sources that have empty word lists
        gap = GapSequence(
            words=["problematic"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": [],  # Empty word list
                "source2": [],  # Empty word list
            },
            corrections=[],
        )

        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        result = strategy.correct([sample_transcription], [])

        assert len(result.corrections) == 0, "Should not make corrections when sources have empty word lists"
        assert result.corrections_made == 0

    def test_disagreeing_sources(self, mock_logger, mock_anchor_finder, sample_transcription):
        """Test handling of gaps where sources disagree on corrections."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a gap where sources suggest different corrections
        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["world"],
                "source2": ["whirled"],  # Different suggestion
            },
            corrections=[],
        )

        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        # Mock both matchers to return high similarity scores
        with patch.object(strategy.phonetic_matcher, "get_similarity", return_value=0.8), patch.object(
            strategy.semantic_matcher, "get_similarity", return_value=0.8
        ):

            result = strategy.correct([sample_transcription], [])

            # Should still correct using first source
            assert len(result.corrections) == 1
            assert result.corrections[0].source == "source1"
            assert result.corrections[0].corrected_word == "world"

    def test_invalid_gap_position(self, mock_logger, mock_anchor_finder, sample_transcription):
        """Test handling of gaps with invalid positions."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a gap with position beyond transcription length
        gap = GapSequence(
            words=["problematic"],
            transcription_position=999,  # Invalid position
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["correction"],
            },
            corrections=[],
        )

        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        result = strategy.correct([sample_transcription], [])

        assert len(result.corrections) == 0, "Should not make corrections for gaps with invalid positions"
        assert result.corrections_made == 0

    def test_mixed_source_availability(self, mock_logger, mock_anchor_finder, sample_transcription):
        """Test handling of gaps where some sources have words and others don't."""
        strategy = SmartCorrectionStrategy(logger=mock_logger, anchor_finder=mock_anchor_finder)

        # Create a gap with mixed source availability
        gap = GapSequence(
            words=["wurld"],
            transcription_position=1,
            preceding_anchor=None,
            following_anchor=None,
            reference_words={
                "source1": ["world"],
                "source2": [],  # Empty source
                "source3": None,  # None source
            },
            corrections=[],
        )

        mock_anchor_finder.find_anchors.return_value = []
        mock_anchor_finder.find_gaps.return_value = [gap]

        # Mock both matchers to return high similarity scores
        with patch.object(strategy.phonetic_matcher, "get_similarity", return_value=0.8), patch.object(
            strategy.semantic_matcher, "get_similarity", return_value=0.8
        ):

            result = strategy.correct([sample_transcription], [])

            assert len(result.corrections) == 1, "Should make correction using available source"
            assert result.corrections[0].source == "source1"
            assert result.corrections[0].corrected_word == "world"
