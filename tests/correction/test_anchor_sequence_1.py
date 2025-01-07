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


def test_anchor_sequence_properties():
    anchor = AnchorSequence(words=["hello", "world"], transcription_position=0, reference_positions={"source1": 0}, confidence=1.0)
    assert anchor.text == "hello world"
    assert anchor.length == 2
    assert anchor.to_dict() == {
        "words": ["hello", "world"],
        "text": "hello world",
        "length": 2,
        "transcription_position": 0,
        "reference_positions": {"source1": 0},
        "confidence": 1.0,
    }


def test_find_ngrams(finder):
    words = ["a", "b", "c", "d"]
    assert finder._find_ngrams(words, 2) == [(["a", "b"], 0), (["b", "c"], 1), (["c", "d"], 2)]


def test_find_matching_sources(finder):
    finder.used_positions = {"source1": set(), "source2": set()}

    ref_texts = {
        "source1": ["hello", "world", "test"],
        "source2": ["hello", "world", "different"],
    }
    ngram = ["hello", "world"]
    matches = finder._find_matching_sources(ngram, ref_texts, 2)
    assert matches == {"source1": 0, "source2": 0}


def test_create_anchor(finder):
    ngram = ["hello", "world"]
    matching_sources = {"source1": 0, "source2": 0}
    anchor = finder._create_anchor(ngram, 0, matching_sources, 2)
    assert anchor is not None
    assert anchor.confidence == 1.0
    assert anchor.words == ngram


def test_remove_overlapping_sequences(finder):
    anchors = [
        AnchorSequence(["a", "b"], 0, {"s1": 0}, 1.0),
        AnchorSequence(["b", "c"], 1, {"s1": 1}, 1.0),
        AnchorSequence(["a", "b", "c"], 0, {"s1": 0}, 1.0),
    ]
    # Provide a context that matches the sequence structure
    context = "a b c"
    filtered = finder._remove_overlapping_sequences(anchors, context)
    assert len(filtered) == 1
    assert filtered[0].anchor.words == ["a", "b", "c"]


def test_find_anchors_simple(finder):
    """Test basic anchor finding with detailed debug output"""
    transcribed = "hello world test"
    references = {"source1": "hello world different", "source2": "hello world test"}

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Initialize used_positions for debug
    finder.used_positions = {source: set() for source in references.keys()}

    # Debug: Print all possible n-grams and their scores
    print("\nPossible n-grams with scores:")
    max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))
    for n in range(max_length, finder.min_sequence_length - 1, -1):
        print(f"\n{n}-grams:")
        ngrams = finder._find_ngrams(trans_words, n)
        for ngram, pos in ngrams:
            print(f"\nPosition {pos}: {ngram}")
            matches = finder._find_matching_sources(ngram, ref_texts_clean, n)
            if matches:
                print(f"  Matches in: {list(matches.keys())}")
                # Debug matching process
                print("  Matching details:")
                for source, ref_words in ref_texts_clean.items():
                    print(f"    {source}: ", end="")
                    for i in range(len(ref_words) - len(ngram) + 1):
                        candidate = ref_words[i : i + len(ngram)]
                        if candidate == ngram:
                            print(f"Match at position {i}")
                        else:
                            print(f"No match at {i} ({candidate})")

                # Score the sequence
                anchor = AnchorSequence(ngram, pos, matches, len(matches) / len(references))
                scored = finder._score_anchor(anchor, transcribed)
                priority = finder._get_sequence_priority(scored)
                print(f"  Break score: {scored.phrase_score.natural_break_score}")
                print(f"  Total score: {scored.phrase_score.total_score}")
                print(f"  Priority: {priority}")
                print(f"  Confidence: {len(matches) / len(references)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors with details
    print("\nFound anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Reference positions: {scored_anchor.anchor.reference_positions}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Priority: {priority}")

    # Update assertions to expect the longest common sequence
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "hello world test"  # Now expects the full matching phrase
    assert anchors[0].anchor.confidence == 0.5  # Only matches in source2


def test_find_anchors_no_matches(finder):
    transcribed = "completely different text"
    references = {"source1": "no matching words here", "source2": "another non matching text"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 0


def test_find_anchors_min_sources(setup_teardown):
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=2, cache_dir=setup_teardown)
    transcribed = "hello world test"
    references = {"source1": "hello world different", "source2": "different hello world"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "hello world"


def test_find_anchors_case_insensitive(finder):
    """Test that case differences don't affect matching"""
    transcribed = "Hello World Test"
    references = {"source1": "hello world test", "source2": "HELLO WORLD TEST"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "hello world test"  # Now expects the full phrase


def test_find_anchors_with_repeated_phrases(setup_teardown):
    """Test that repeated phrases in transcription are only matched if they're also repeated in references"""
    transcribed = "hello world hello world hello world"
    references = {"source1": "hello world something hello world", "source2": "hello world only once"}  # repeated twice  # appears once
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Debug: Print all matches before filtering
    print("\nAll potential matches:")
    ngram = ["hello", "world"]
    for pos in range(len(trans_words) - 1):
        if trans_words[pos : pos + 2] == ngram:
            matches = finder._find_matching_sources(ngram, ref_texts_clean, 2)
            unused = finder._filter_used_positions(matches)
            print(f"\nPosition {pos}:")
            print(f"  All matches: {matches}")
            print(f"  Unused matches: {unused}")
            print(f"  Used positions: {finder.used_positions}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    for anchor in anchors:
        print(f"Text: '{anchor.anchor.text}'")
        print(f"Position: {anchor.anchor.transcription_position}")
        print(f"Reference positions: {anchor.anchor.reference_positions}")
        print(f"Confidence: {anchor.anchor.confidence}")

    # Original assertions
    assert len(anchors) == 2
    assert all(anchor.anchor.text == "hello world" for anchor in anchors)
    assert anchors[0].anchor.transcription_position == 0
    assert anchors[1].anchor.transcription_position == 2


def test_find_anchors_with_single_source_repeated_phrase(setup_teardown):
    """Test that matches work even if phrase is only repeated in one source"""
    transcribed = "test one two test one two"
    references = {"source1": "test one two something test one two", "source2": "different text entirely"}  # repeated  # no match
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)
    anchors = finder.find_anchors(transcribed, references)

    assert len(anchors) == 2
    assert all(anchor.anchor.text == "test one two" for anchor in anchors)
    assert all(anchor.anchor.confidence == 0.5 for anchor in anchors)  # only matches one source


def test_real_world_lyrics_scenario(setup_teardown):
    """Test based on real-world lyrics pattern"""
    transcribed = "son of a martyr you're a son of a father you gotta look inside"
    references = {
        "source1": "son of a martyr\nson of a father\nyou can look inside",
        "source2": "son of a mother\nson of a father\nyou can look inside",
    }
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)
    anchors = finder.find_anchors(transcribed, references)

    # Should find at least one of these sequences
    expected_sequences = ["son of a father", "son of a", "of a father"]
    found_sequences = [anchor.anchor.text for anchor in anchors]
    assert any(seq in found_sequences for seq in expected_sequences), f"Expected one of {expected_sequences}, but found {found_sequences}"


def test_find_anchors_with_punctuation(setup_teardown):
    """Test that punctuation and extra whitespace don't affect matching"""
    transcribed = "hello,  world! test... something"
    references = {"source1": "hello world test", "source2": "hello    world, test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Original transcribed: {transcribed}")
    print(f"Cleaned transcribed: {trans_words}")
    for source, text in references.items():
        print(f"Original {source}: {text}")
        print(f"Cleaned {source}: {ref_texts_clean[source]}")

    # Debug: Print all possible n-grams and their matches
    print("\nPossible n-grams with matches:")
    max_length = min(len(trans_words), min(len(words) for words in ref_texts_clean.values()))
    for n in range(max_length, finder.min_sequence_length - 1, -1):
        print(f"\n{n}-grams:")
        ngrams = finder._find_ngrams(trans_words, n)
        for ngram, pos in ngrams:
            print(f"\nPosition {pos}: {ngram}")
            matches = finder._find_matching_sources(ngram, ref_texts_clean, n)
            if matches:
                print(f"  Matches in: {list(matches.keys())}")
                # Score the sequence
                anchor = AnchorSequence(ngram, pos, matches, len(matches) / len(references))
                scored = finder._score_anchor(anchor, transcribed)
                priority = finder._get_sequence_priority(scored)
                print(f"  Break score: {scored.phrase_score.natural_break_score}")
                print(f"  Total score: {scored.phrase_score.total_score}")
                print(f"  Priority: {priority}")
                print(f"  Confidence: {len(matches) / len(references)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    for anchor in anchors:
        scored = finder._score_anchor(anchor.anchor, transcribed)
        priority = finder._get_sequence_priority(scored)
        print(f"Text: '{anchor.anchor.text}'")
        print(f"Position: {anchor.anchor.transcription_position}")
        print(f"Reference positions: {anchor.anchor.reference_positions}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Priority: {priority}")
        print(f"Confidence: {anchor.anchor.confidence}")

    assert len(anchors) > 0
    assert any("hello world" in anchor.anchor.text for anchor in anchors)


def test_find_anchors_respects_word_boundaries(setup_teardown):
    """Test that partial word matches aren't considered"""
    transcribed = "testing the tester test"
    references = {"source1": "test the tester", "source2": "testing test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)
    anchors = finder.find_anchors(transcribed, references)

    # Should not match "test" within "testing" or "tester"
    matched_words = set()
    for anchor in anchors:
        matched_words.update(anchor.anchor.words)

    assert "testing" not in matched_words or "tester" not in matched_words


def test_find_anchors_minimum_length(setup_teardown):
    """Test that sequences shorter than minimum length are not matched"""
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)
    transcribed = "a b c d e"
    references = {"source1": "a b something c d e", "source2": "a b different c d e"}
    anchors = finder.find_anchors(transcribed, references)

    # Should find "c d e" but not "a b"
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "c d e"


def test_find_anchors_confidence_calculation(setup_teardown):
    """Test that confidence is correctly calculated based on source matches"""
    transcribed = "test sequence here"
    references = {"source1": "test sequence here", "source2": "test sequence here", "source3": "different text entirely"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)
    anchors = finder.find_anchors(transcribed, references)

    assert len(anchors) == 1
    assert anchors[0].anchor.confidence == 2 / 3  # matches 2 out of 3 sources


def test_scored_anchor_total_score():
    """Test that ScoredAnchor combines confidence and phrase quality correctly"""
    anchor = AnchorSequence(["hello", "world"], 0, {"source1": 0}, confidence=0.8)
    phrase_score = PhraseScore(phrase_type=PhraseType.COMPLETE, natural_break_score=0.9, length_score=1.0)
    scored_anchor = ScoredAnchor(anchor=anchor, phrase_score=phrase_score)

    # confidence (0.8 * 0.8) + phrase_score.total_score (~0.97 * 0.2) + length_bonus (0.1)
    assert 0.93 <= scored_anchor.total_score <= 0.94


def test_remove_overlapping_sequences_prioritizes_better_phrases(finder):
    """Test that overlapping sequences are resolved by preferring longer matches"""
    # Override the default min_sequence_length for this test
    finder.min_sequence_length = 4

    transcribed = "my heart will go on\nand on forever more"
    references = {"source1": "my heart will go on and on forever more", "source2": "my heart will go on\nand on forever more"}

    # Create test sequences
    sequences = [
        AnchorSequence(["my", "heart", "will", "go", "on"], 0, {"source1": 0, "source2": 0}, 1.0),
        AnchorSequence(["my", "heart", "will", "go", "on", "and", "on", "forever", "more"], 0, {"source1": 0, "source2": 0}, 1.0),
    ]

    # Debug: Print scores for each sequence
    print("\nScoring sequences:")
    for seq in sequences:
        score = finder.phrase_analyzer.score_phrase(seq.words, transcribed)
        print(f"\nSequence: '{seq.text}'")
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")
        priority = finder._get_sequence_priority(finder._score_anchor(seq, transcribed))
        print(f"Priority: {priority}")  # Add priority debug output

    # Filter sequences
    filtered = finder._remove_overlapping_sequences(sequences, transcribed)

    # Debug: Print filtered sequences
    print("\nFiltered sequences:")
    for seq in filtered:
        score = finder.phrase_analyzer.score_phrase(seq.anchor.words, transcribed)
        print(f"\nSequence: '{seq.anchor.text}'")
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")
        priority = finder._get_sequence_priority(finder._score_anchor(seq.anchor, transcribed))
        print(f"Priority: {priority}")  # Add priority debug output

    # Should prefer the longer sequence
    assert len(filtered) == 1
    assert filtered[0].anchor.text == "my heart will go on and on forever more"


def test_remove_overlapping_sequences_with_line_breaks(finder):
    """Test that longer sequences are preferred even across line breaks"""
    transcribed = "my heart will go on\nand on forever more"
    references = {"source1": "my heart will go on and on forever more", "source2": "my heart will go on\nand on forever more"}

    # Set minimum sequence length to ensure we don't get too-short matches
    finder.min_sequence_length = 4
    # Initialize used_positions
    finder.used_positions = {source: set() for source in references.keys()}

    # Debug: Test specific sequence we want
    target_sequence = ["my", "heart", "will", "go", "on"]
    target_score = finder.phrase_analyzer.score_phrase(target_sequence, transcribed)
    print("\nTarget sequence 'my heart will go on':")
    print(f"Break score: {target_score.natural_break_score}")
    print(f"Total score: {target_score.total_score}")
    print(f"Phrase type: {target_score.phrase_type}")

    # Debug: Test full sequence for comparison
    full_sequence = transcribed.split()
    full_score = finder.phrase_analyzer.score_phrase(full_sequence, transcribed)
    print("\nFull sequence 'my heart will go on and on forever more':")
    print(f"Break score: {full_score.natural_break_score}")
    print(f"Total score: {full_score.total_score}")
    print(f"Phrase type: {full_score.phrase_type}")

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors with details
    print("\nFound anchors:")
    for scored_anchor in anchors:
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        score = finder.phrase_analyzer.score_phrase(scored_anchor.anchor.words, transcribed)
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")
        print(f"Length: {len(scored_anchor.anchor.words)}")

    # Updated assertions to expect longer sequences
    assert len(anchors) > 0
    assert "my heart will go on and on forever more" in [a.anchor.text for a in anchors]
    assert "go on and" not in [a.anchor.text for a in anchors]  # crosses line break


def test_remove_overlapping_sequences_with_line_breaks_debug(finder):
    """Debug test for overlapping sequence selection"""
    transcribed = "my heart will go on\nand on forever more"

    # Create two overlapping sequences
    seq1 = AnchorSequence(["my", "heart", "will", "go", "on"], 0, {"source1": 0, "source2": 0}, 1.0)
    seq2 = AnchorSequence(["my", "heart", "will", "go", "on", "and", "on", "forever", "more"], 0, {"source1": 0, "source2": 0}, 1.0)
    sequences = [seq1, seq2]

    # Debug: Print initial sequence details
    print("\nInitial sequences:")
    for seq in sequences:
        score = finder.phrase_analyzer.score_phrase(seq.words, transcribed)
        print(f"\nSequence: '{seq.text}'")
        print(f"Length: {len(seq.words)}")
        print(f"Position: {seq.transcription_position}")
        print(f"Confidence: {seq.confidence}")
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")
        priority = finder._get_sequence_priority(finder._score_anchor(seq, transcribed))
        print(f"Priority: {priority}")

    # Debug: Print comparison details
    score1 = finder.phrase_analyzer.score_phrase(seq1.words, transcribed)
    score2 = finder.phrase_analyzer.score_phrase(seq2.words, transcribed)
    print("\nComparing sequences:")
    print(f"seq1 vs seq2: {score1.total_score} vs {score2.total_score}")

    # Get filtered sequences
    filtered = finder._remove_overlapping_sequences(sequences, transcribed)

    # Debug: Print result
    print("\nChosen sequence:")
    chosen = filtered[0].anchor  # Fix: access the anchor property
    score = finder.phrase_analyzer.score_phrase(chosen.words, transcribed)
    print(f"Text: '{chosen.text}'")
    print(f"Length: {len(chosen.words)}")
    print(f"Total score: {score.total_score}")
    print(f"Break score: {score.natural_break_score}")
    print(f"Phrase type: {score.phrase_type}")
    priority = finder._get_sequence_priority(finder._score_anchor(chosen, transcribed))
    print(f"Priority: {priority}")

    # Should choose the longer sequence
    assert len(filtered) == 1
    assert filtered[0].anchor.text == "my heart will go on and on forever more"


def test_score_anchor(finder):
    """Test anchor scoring logic"""
    transcribed = "hello world\ntest phrase"

    # Test sequence that respects line break
    anchor1 = AnchorSequence(["hello", "world"], 0, {"source1": 0, "source2": 0}, 1.0)
    scored1 = finder._score_anchor(anchor1, transcribed)
    print("\nScoring sequence that respects line break:")
    print(f"Sequence: '{anchor1.text}'")
    print(f"Break score: {scored1.phrase_score.natural_break_score}")
    print(f"Total score: {scored1.phrase_score.total_score}")
    assert scored1.phrase_score.natural_break_score == 1.0

    # Test sequence that crosses line break
    anchor2 = AnchorSequence(["world", "test"], 1, {"source1": 1}, 0.5)
    scored2 = finder._score_anchor(anchor2, transcribed)
    print("\nScoring sequence that crosses line break:")
    print(f"Sequence: '{anchor2.text}'")
    print(f"Break score: {scored2.phrase_score.natural_break_score}")
    print(f"Total score: {scored2.phrase_score.total_score}")
    assert scored2.phrase_score.natural_break_score == 0.0


def test_get_sequence_priority_simple(finder):
    """Test sequence priority calculation"""
    transcribed = "hello world test"

    # Test sequence with high confidence and source count
    anchor1 = AnchorSequence(["hello", "world"], 0, {"source1": 0, "source2": 0}, 1.0)
    scored1 = finder._score_anchor(anchor1, transcribed)
    priority1 = finder._get_sequence_priority(scored1)

    # Test sequence with lower confidence and fewer sources
    anchor2 = AnchorSequence(["world", "test"], 1, {"source1": 1}, 0.5)
    scored2 = finder._score_anchor(anchor2, transcribed)
    priority2 = finder._get_sequence_priority(scored2)

    print("\nComparing sequence priorities:")
    print(f"Sequence 1: '{anchor1.text}'")
    print(f"Priority: {priority1}")
    print(f"Sequence 2: '{anchor2.text}'")
    print(f"Priority: {priority2}")

    assert priority1 > priority2  # First sequence should have higher priority


def test_viet_nam_lyrics_scenario(setup_teardown):
    """Test based on a song's lyrics pattern"""
    transcribed = "Let's say I got a number\nThat number's fifty thousand\nThat's ten percent of five hundred thousand\nOh, here we are\nIn French Indochina"
    references = {
        "genius": "Let's say I got a number\nThat number's fifty thousand\nThat's ten percent of five hundred thousand\nOh, here we are in French Indochina",
        "spotify": "Let's say I got a number\nThat number's fifty-thousand\nThat's ten percent of five-hundred-thousand\nOh, here we are in French Indochina",
    }
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Debug: Try specific phrases we expect to find
    expected_phrases = [
        ["lets", "say", "i", "got", "a", "number", "that", "numbers", "fifty", "thousand"],
        ["thats", "ten", "percent", "of", "five", "hundred", "thousand"],
        ["oh", "here", "we", "are", "in", "french", "indochina"],
    ]

    print("\nTesting expected phrases:")
    for phrase in expected_phrases:
        print(f"\nPhrase: '{' '.join(phrase)}'")
        # Check if phrase exists in references
        matches = finder._find_matching_sources(phrase, ref_texts_clean, len(phrase))
        print(f"Matches found: {matches}")

        if matches:
            # Score the phrase
            anchor = AnchorSequence(phrase, 0, matches, len(matches) / len(references))
            scored = finder._score_anchor(anchor, transcribed)
            print(f"Break score: {scored.phrase_score.natural_break_score}")
            print(f"Total score: {scored.phrase_score.total_score}")
            print(f"Phrase type: {scored.phrase_score.phrase_type}")
            print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Get actual anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors
    print("\nFound anchors:")
    found_texts = set()  # Use a set to store found texts
    for scored_anchor in anchors:
        found_texts.add(scored_anchor.anchor.text)  # Add each anchor text to the set
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Phrase type: {scored.phrase_score.phrase_type}")
        print(f"Priority: {finder._get_sequence_priority(scored)}")

    # Test specific expectations
    expected_texts = {
        "lets say i got a number that numbers fifty thousand thats ten percent of five hundred thousand oh here we are in french indochina"
    }

    # Check for missing expected phrases
    missing_phrases = expected_texts - found_texts
    assert not missing_phrases, f"Expected phrases not found: {missing_phrases}"


def test_viet_nam_first_line(setup_teardown):
    """Specific test for the first line of Viet Nam lyrics"""
    transcribed = "Let's say I got a number"
    references = {"genius": "Let's say I got a number", "spotify": "Let's say I got a number"}
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1, cache_dir=setup_teardown)

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

        # Debug the break score calculation
        print("\nBreak score calculation details:")
        phrase_start = transcribed.find(anchor.text)
        phrase_end = phrase_start + len(anchor.text)
        print(f"Phrase start: {phrase_start}")
        print(f"Phrase end: {phrase_end}")
        print(f"Text length: {len(transcribed)}")
        print(f"Is full line? {phrase_start == 0 and phrase_end == len(transcribed)}")

    # Get anchors
    anchors = finder.find_anchors(transcribed, references)

    # Debug: Print found anchors with detailed scoring
    print("\nFound anchors:")
    for scored_anchor in anchors:
        scored = finder._score_anchor(scored_anchor.anchor, transcribed)
        print(f"\nText: '{scored_anchor.anchor.text}'")
        print(f"Position: {scored_anchor.anchor.transcription_position}")
        print(f"Confidence: {scored_anchor.anchor.confidence}")

        # Debug the break score calculation for each anchor
        phrase_start = transcribed.find(scored_anchor.anchor.text)
        phrase_end = phrase_start + len(scored_anchor.anchor.text)
        print(f"Phrase start: {phrase_start}")
        print(f"Phrase end: {phrase_end}")
        print(f"Is full line? {phrase_start == 0 and phrase_end == len(transcribed)}")

    # Should find the complete line
    assert len(anchors) == 1, f"Expected 1 anchor but found {len(anchors)}: {[a.anchor.text for a in anchors]}"
    assert anchors[0].anchor.text == "lets say i got a number"
    assert anchors[0].anchor.confidence == 1.0


def test_hyphenated_words(setup_teardown):
    """Test that hyphenated words are handled correctly"""
    transcribed = "fifty-thousand five-hundred-thousand"
    references = {"source1": "fifty-thousand five-hundred-thousand", "source2": "fifty thousand five hundred thousand"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1, cache_dir=setup_teardown)

    # Debug: Print cleaned texts
    print("\nCleaned texts:")
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}
    print(f"Transcribed: {trans_words}")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    anchors = finder.find_anchors(transcribed, references)

    # Should find the complete phrase despite different hyphenation
    found_texts = {anchor.anchor.text for anchor in anchors}
    assert "fifty thousand five hundred thousand" in found_texts
