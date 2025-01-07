import pytest
import os
import tempfile
import shutil

from lyrics_transcriber.types import AnchorSequence, ScoredAnchor, PhraseScore, PhraseType
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder


@pytest.fixture(autouse=True)
def setup_teardown():
    """Clean up the test cache directory before and after each test."""
    # Use a test-specific cache directory
    test_cache_dir = os.path.join(tempfile.gettempdir(), "lyrics-transcriber-test-cache")

    # Clean up before test
    if os.path.exists(test_cache_dir):
        shutil.rmtree(test_cache_dir)

    # Set environment variable
    os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"] = test_cache_dir

    yield test_cache_dir

    # Clean up after test
    if os.path.exists(test_cache_dir):
        shutil.rmtree(test_cache_dir)

    # Clean up environment variable
    del os.environ["LYRICS_TRANSCRIBER_CACHE_DIR"]


@pytest.fixture
def finder(setup_teardown):
    return AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)


def test_complete_line_matching(setup_teardown):
    """Test that complete lines are preferred over partial matches when they exist in all sources."""
    transcribed = "hello world test phrase"
    references = {"source1": "hello world test phrase", "source2": "hello world test phrase"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Debug: Test the full line first
    full_line = trans_words
    matches = finder._find_matching_sources(full_line, ref_texts_clean, len(full_line))
    print(f"\nTesting full line '{' '.join(full_line)}':")
    print(f"Matches: {matches}")

    if matches:
        anchor = AnchorSequence(full_line, 0, matches, len(matches) / len(references))
        scored = finder._score_anchor(anchor, transcribed)
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Should find the complete line
    assert len(anchors) == 1, f"Expected 1 anchor but found {len(anchors)}: {[a.anchor.text for a in anchors]}"
    assert anchors[0].anchor.text == "hello world test phrase"
    assert anchors[0].anchor.confidence == 1.0

    # Also test with a slightly different reference to ensure it still works
    references_with_diff = {
        "source1": "hello world test phrase",
        "source2": "hello world test phrase yeah",  # Longer but contains the complete line
    }
    anchors = finder.find_anchors(transcribed, references_with_diff)
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "hello world test phrase"


def test_complete_line_matching_with_apostrophe(setup_teardown):
    """Test that complete lines with apostrophes are handled correctly."""
    transcribed = "let's say I got a number"  # Note the apostrophe
    references = {"source1": "let's say I got a number", "source2": "let's say I got a number"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts and raw texts
    print("\nRaw texts:")
    print(f"Transcribed: {transcribed}")
    for source, text in references.items():
        print(f"{source}: {text}")

    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Debug: Test the full line first
    full_line = trans_words
    matches = finder._find_matching_sources(full_line, ref_texts_clean, len(full_line))
    print(f"\nTesting full line '{' '.join(full_line)}':")
    print(f"Matches: {matches}")

    if matches:
        anchor = AnchorSequence(full_line, 0, matches, len(matches) / len(references))
        scored = finder._score_anchor(anchor, transcribed)
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Should find the complete line
    assert len(anchors) == 1, f"Expected 1 anchor but found {len(anchors)}: {[a.anchor.text for a in anchors]}"
    assert anchors[0].anchor.text == "lets say i got a number"
    assert anchors[0].anchor.confidence == 1.0


def test_complete_line_matching_simple(setup_teardown):
    """Test complete line matching with a simpler case to isolate the issue."""
    # Use same word count as "let's say I got a number" but simpler words
    transcribed = "one two three four five six"
    references = {"source1": "one two three four five six", "source2": "one two three four five six"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Debug: Test the full line first
    full_line = trans_words
    matches = finder._find_matching_sources(full_line, ref_texts_clean, len(full_line))
    print(f"\nTesting full line '{' '.join(full_line)}':")
    print(f"Matches: {matches}")

    if matches:
        anchor = AnchorSequence(full_line, 0, matches, len(matches) / len(references))
        scored = finder._score_anchor(anchor, transcribed)
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Should find the complete line
    assert len(anchors) == 1, f"Expected 1 anchor but found {len(anchors)}: {[a.anchor.text for a in anchors]}"
    assert anchors[0].anchor.text == "one two three four five six"
    assert anchors[0].anchor.confidence == 1.0


def test_break_score_calculation(setup_teardown):
    """Test break score calculation with various line formats."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    test_cases = [
        # Simple case (known working)
        ("one two three", "one two three", ["one", "two", "three"]),
        # With apostrophe (problematic case)
        ("let's say test", "let's say test", ["lets", "say", "test"]),
        # Mixed case (to test case sensitivity)
        ("Hello World Test", "Hello World Test", ["hello", "world", "test"]),
        # With extra spaces (to test space normalization)
        ("hello   world   test", "hello   world   test", ["hello", "world", "test"]),
    ]

    print("\nBreak score calculation tests:")
    for original, context, words in test_cases:
        print(f"\nOriginal text: '{original}'")
        print(f"Context text: '{context}'")
        print(f"Cleaned words: {words}")

        # Create anchor and get score
        anchor = AnchorSequence(words, 0, {"source1": 0}, 1.0)
        scored = finder._score_anchor(anchor, context)

        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")

        # For debugging position calculation
        clean_context = finder._clean_text(context)
        clean_text = " ".join(words)
        print(f"Clean context: '{clean_context}'")
        print(f"Clean text: '{clean_text}'")
        print(f"Text position in context: {clean_context.find(clean_text)}")


def test_break_score_with_text_cleaning(setup_teardown):
    """Test that break score calculation works correctly with cleaned text."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    test_cases = [
        # Control case - no cleaning needed
        ("one two", "one two", ["one", "two"]),
        # Test cases where cleaning is needed
        ("Let's go", "Let's go", ["lets", "go"]),
        ("Hello World", "Hello World", ["hello", "world"]),
        # Test case with identical cleaned text but different original
        ("let's go", "Let's go", ["lets", "go"]),
        ("HELLO world", "Hello World", ["hello", "world"]),
    ]

    print("\nBreak score tests with text cleaning:")
    for original, context, words in test_cases:
        print(f"\nOriginal text: '{original}'")
        print(f"Context text: '{context}'")
        print(f"Cleaned words: {words}")

        # Create anchor and get score
        anchor = AnchorSequence(words, 0, {"source1": 0}, 1.0)
        scored = finder._score_anchor(anchor, context)

        # Debug the text cleaning and position calculation
        clean_context = finder._clean_text(context)
        clean_text = " ".join(words)
        print(f"Clean context: '{clean_context}'")
        print(f"Clean text: '{clean_text}'")
        print(f"Text position in context: {clean_context.find(clean_text)}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")

        # These should all be equivalent after cleaning
        assert clean_context == clean_text, f"Cleaned context '{clean_context}' doesn't match cleaned text '{clean_text}'"


def test_break_score_uses_cleaned_text(setup_teardown):
    """Test that break score calculation uses cleaned text rather than original text."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    test_cases = [
        # Base case - no cleaning needed
        (
            "one two three",  # original
            ["one", "two", "three"],  # words
            1.0,  # expected break score
            "Simple text should get full break score",
        ),
        # Case with apostrophe
        (
            "Let's go now",  # original
            ["lets", "go", "now"],  # words
            1.0,  # expected break score
            "Cleaned text should get full break score despite apostrophe",
        ),
        # Case with capitalization
        (
            "Hello World Test",  # original
            ["hello", "world", "test"],  # words
            1.0,  # expected break score
            "Cleaned text should get full break score despite capitalization",
        ),
        # Case with extra spaces
        (
            "hello   world   test",  # original
            ["hello", "world", "test"],  # words
            1.0,  # expected break score
            "Cleaned text should get full break score despite extra spaces",
        ),
    ]

    print("\nBreak score calculation with cleaned text:")
    for original, words, expected_score, message in test_cases:
        print(f"\nOriginal text: '{original}'")
        print(f"Cleaned words: {words}")

        # Create anchor and get score
        anchor = AnchorSequence(words, 0, {"source1": 0}, 1.0)
        scored = finder._score_anchor(anchor, original)

        # Debug output
        clean_context = finder._clean_text(original)
        clean_text = " ".join(words)
        print(f"Clean context: '{clean_context}'")
        print(f"Clean text: '{clean_text}'")
        print(f"Text position in context: {clean_context.find(clean_text)}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Expected score: {expected_score}")

        # Assert that break score is calculated using cleaned text
        assert (
            scored.phrase_score.natural_break_score == expected_score
        ), f"Failed: {message} (got {scored.phrase_score.natural_break_score}, expected {expected_score})"

        # Verify that cleaned versions match
        assert clean_context == clean_text, f"Cleaned context '{clean_context}' doesn't match cleaned text '{clean_text}'"


def test_get_reference_words(finder):
    """Test extracting reference words between positions"""
    ref_words = ["hello", "world", "test", "phrase"]

    # Test with both positions specified
    assert finder._get_reference_words("source1", ref_words, 1, 3) == ["world", "test"]

    # Test with start position only
    assert finder._get_reference_words("source1", ref_words, 2, None) == ["test", "phrase"]

    # Test with end position only
    assert finder._get_reference_words("source1", ref_words, None, 2) == ["hello", "world"]

    # Test with neither position specified
    assert finder._get_reference_words("source1", ref_words, None, None) == ref_words


def test_create_initial_gap(finder):
    """Test creating gap before first anchor"""
    words = ["hello", "world", "test", "phrase"]
    ref_texts_clean = {"source1": ["hello", "world", "different", "text"], "source2": ["start", "hello", "world", "end"]}

    # Test with no anchors
    gap = finder._create_initial_gap(words, None, ref_texts_clean)
    assert gap is not None
    assert gap.words == tuple(words)
    assert gap.transcription_position == 0
    assert gap.preceding_anchor is None
    assert gap.following_anchor is None
    assert gap.reference_words == ref_texts_clean

    # Test with first anchor at position 0 (should return None)
    first_anchor = ScoredAnchor(
        anchor=AnchorSequence(["test", "phrase"], 2, {"source1": 2}, 1.0), phrase_score=PhraseScore(PhraseType.COMPLETE, 1.0, 1.0)
    )
    gap = finder._create_initial_gap(words, first_anchor, ref_texts_clean)
    assert gap is not None
    assert gap.words == ("hello", "world")
    assert gap.transcription_position == 0
    assert gap.preceding_anchor is None
    assert gap.following_anchor == first_anchor.anchor


def test_create_between_gap(finder):
    """Test creating gap between two anchors"""
    words = ["hello", "world", "middle", "test", "phrase"]
    ref_texts_clean = {
        "source1": ["hello", "world", "middle", "test", "phrase"],
        "source2": ["hello", "world", "different", "test", "phrase"],
    }

    current_anchor = ScoredAnchor(
        anchor=AnchorSequence(["hello", "world"], 0, {"source1": 0, "source2": 0}, 1.0),
        phrase_score=PhraseScore(PhraseType.COMPLETE, 1.0, 1.0),
    )

    next_anchor = ScoredAnchor(
        anchor=AnchorSequence(["test", "phrase"], 3, {"source1": 3, "source2": 3}, 1.0),
        phrase_score=PhraseScore(PhraseType.COMPLETE, 1.0, 1.0),
    )

    # Test with gap between anchors
    gap = finder._create_between_gap(words, current_anchor, next_anchor, ref_texts_clean)
    assert gap is not None
    assert gap.words == ("middle",)
    assert gap.transcription_position == 2
    assert gap.preceding_anchor == current_anchor.anchor
    assert gap.following_anchor == next_anchor.anchor
    assert gap.reference_words == {"source1": ["middle"], "source2": ["different"]}

    # Test with no gap between anchors
    next_anchor.anchor.transcription_position = 2
    gap = finder._create_between_gap(words, current_anchor, next_anchor, ref_texts_clean)
    assert gap is None


def test_create_final_gap(finder):
    """Test creating gap after last anchor"""
    words = ["hello", "world", "test", "phrase", "end"]
    ref_texts_clean = {"source1": ["hello", "world", "final", "words", "here"], "source2": ["hello", "world", "different", "ending"]}

    last_anchor = ScoredAnchor(
        anchor=AnchorSequence(["hello", "world"], 0, {"source1": 0, "source2": 0}, 1.0),
        phrase_score=PhraseScore(PhraseType.COMPLETE, 1.0, 1.0),
    )

    # Test with words after last anchor
    gap = finder._create_final_gap(words, last_anchor, ref_texts_clean)
    assert gap is not None
    assert gap.words == ("test", "phrase", "end")
    assert gap.transcription_position == 2
    assert gap.preceding_anchor == last_anchor.anchor
    assert gap.following_anchor is None
    assert gap.reference_words == {"source1": ["final", "words", "here"], "source2": ["different", "ending"]}

    # Test with no words after last anchor
    words = ["hello", "world"]
    gap = finder._create_final_gap(words, last_anchor, ref_texts_clean)
    assert gap is None


def test_find_gaps_integration(finder):
    """Integration test for find_gaps"""
    transcribed = "hello world test phrase end"
    references = {"source1": "hello world middle test phrase final", "source2": "hello world different test phrase end"}

    # First find some anchors
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) > 0

    # Then find gaps
    gaps = finder.find_gaps(transcribed, anchors, references)

    # Basic validation of gaps
    assert len(gaps) > 0

    # Verify gaps don't overlap with anchors
    for gap in gaps:
        # Check gap has correct structure
        assert isinstance(gap.words, tuple)
        assert isinstance(gap.transcription_position, int)
        assert isinstance(gap.reference_words, dict)

        # If gap has surrounding anchors, verify positions make sense
        if gap.preceding_anchor:
            assert gap.transcription_position >= (gap.preceding_anchor.transcription_position + len(gap.preceding_anchor.words))

        if gap.following_anchor:
            assert gap.transcription_position + len(gap.words) <= gap.following_anchor.transcription_position


def test_pull_it_apart_sequence(finder):
    """Test that 'pull it apart' is properly identified as a complete phrase."""
    transcribed = "Put it together, or you can pull it apart"
    references = {"genius": "You can put it together\nYou can pull it apart", "spotify": "You can put it together\nYou can pull it apart"}

    # First, let's see what n-grams are being considered
    words = finder._clean_text(transcribed).split()
    print("\nCleaned words:", words)

    # Try different n-gram lengths and score each candidate
    print("\nScoring potential anchors:")
    ref_texts_clean = {k: finder._clean_text(v).split() for k, v in references.items()}

    candidates = []
    for n in range(3, 6):
        ngrams = finder._find_ngrams(words, n)
        for ngram, pos in ngrams:
            matches = finder._find_matching_sources(ngram, ref_texts_clean, len(ngram))
            if matches:
                # Create and score the anchor
                anchor = AnchorSequence(ngram, pos, matches, len(matches) / len(references))
                scored = finder._score_anchor(anchor, transcribed)
                candidates.append(scored)
                print(f"\nCandidate: '{' '.join(ngram)}' at position {pos}")
                print(f"Length: {len(ngram)}")
                print(f"Phrase type: {scored.phrase_score.phrase_type}")
                print(f"Break score: {scored.phrase_score.natural_break_score}")
                print(f"Total score: {scored.phrase_score.total_score}")
                print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Now check the actual anchors
    anchors = finder.find_anchors(transcribed, references)

    print("\nFinal selected anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Length: {len(scored_anchor.anchor.words)}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Check that "pull it apart" is included in some anchor
    found_phrase = False
    for scored_anchor in anchors:
        if "pull it apart" in scored_anchor.anchor.text:
            found_phrase = True
            break

    assert found_phrase, "Expected to find 'pull it apart' in anchor sequences"


def test_get_sequence_priority_real_case_1(finder):
    """Test that longer matching sequences are preferred over shorter ones."""
    # Use the exact context from the real case
    context = "Put it together, or you can pull it apart"

    # Create test cases with same source count and break score
    short_anchor = AnchorSequence(
        words=["you", "can", "pull"],
        transcription_position=4,
        reference_positions={"genius": 5, "spotify": 5},  # Use actual reference positions
        confidence=1.0,
    )

    long_anchor = AnchorSequence(
        words=["you", "can", "pull", "it", "apart"],
        transcription_position=4,
        reference_positions={"genius": 5, "spotify": 5},
        confidence=1.0,
    )

    # Score both anchors
    short_scored = finder._score_anchor(short_anchor, context)
    long_scored = finder._score_anchor(long_anchor, context)

    # Get priorities
    short_priority = finder._get_sequence_priority(short_scored)
    long_priority = finder._get_sequence_priority(long_scored)

    print(f"\nContext: '{context}'")
    print(f"\nShort sequence ({short_anchor.text}):")
    print(f"Priority: {short_priority}")
    print(f"\nLong sequence ({long_anchor.text}):")
    print(f"Priority: {long_priority}")

    # Debug the break score calculation
    print("\nBreak score analysis:")
    clean_context = finder._clean_text(context)
    print(f"Clean context: '{clean_context}'")
    print(f"Short sequence position: {clean_context.find(' '.join(short_anchor.words))}")
    print(f"Long sequence position: {clean_context.find(' '.join(long_anchor.words))}")

    # The longer sequence should have higher priority
    assert long_priority > short_priority, "Longer matching sequence should have higher priority"
