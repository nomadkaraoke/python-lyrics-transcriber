import pytest
from lyrics_transcriber.correction.anchor_sequence import AnchorSequence, AnchorSequenceFinder, ScoredAnchor
from lyrics_transcriber.correction.text_analysis import PhraseScore, PhraseType


@pytest.fixture
def finder():
    return AnchorSequenceFinder(min_sequence_length=2, min_sources=1)


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


def test_clean_text(finder):
    assert finder._clean_text("Hello  World") == "hello world"
    assert finder._clean_text("  Multiple   Spaces  ") == "multiple spaces"


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
    assert filtered[0].words == ["a", "b", "c"]


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
            # Check matches in references
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
    for anchor in anchors:
        scored = finder._score_anchor(anchor, transcribed)
        priority = finder._get_sequence_priority(scored)
        print(f"\nText: '{anchor.text}'")
        print(f"Position: {anchor.transcription_position}")
        print(f"Confidence: {anchor.confidence}")
        print(f"Reference positions: {anchor.reference_positions}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Priority: {priority}")

    # Original assertions
    assert len(anchors) == 1
    assert anchors[0].text == "hello world"
    assert anchors[0].confidence == 1.0


def test_find_anchors_no_matches(finder):
    transcribed = "completely different text"
    references = {"source1": "no matching words here", "source2": "another non matching text"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 0


def test_find_anchors_min_sources(finder):
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=2)
    transcribed = "hello world test"
    references = {"source1": "hello world different", "source2": "different hello world"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 1
    assert anchors[0].text == "hello world"


def test_find_anchors_case_insensitive(finder):
    transcribed = "Hello World"
    references = {"source1": "hello world", "source2": "HELLO WORLD"}
    anchors = finder.find_anchors(transcribed, references)
    assert len(anchors) == 1
    assert anchors[0].text == "hello world"


def test_find_anchors_with_repeated_phrases(finder):
    """Test that repeated phrases in transcription are only matched if they're also repeated in references"""
    transcribed = "hello world hello world hello world"
    references = {"source1": "hello world something hello world", "source2": "hello world only once"}  # repeated twice  # appears once
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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
        print(f"Text: '{anchor.text}'")
        print(f"Position: {anchor.transcription_position}")
        print(f"Reference positions: {anchor.reference_positions}")
        print(f"Confidence: {anchor.confidence}")

    # Original assertions
    assert len(anchors) == 2
    assert all(anchor.text == "hello world" for anchor in anchors)
    assert anchors[0].transcription_position == 0
    assert anchors[1].transcription_position == 2


def test_find_anchors_with_single_source_repeated_phrase():
    """Test that matches work even if phrase is only repeated in one source"""
    transcribed = "test one two test one two"
    references = {"source1": "test one two something test one two", "source2": "different text entirely"}  # repeated  # no match
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    assert len(anchors) == 2
    assert all(anchor.text == "test one two" for anchor in anchors)
    assert all(anchor.confidence == 0.5 for anchor in anchors)  # only matches one source


def test_real_world_lyrics_scenario():
    """Test based on real-world lyrics pattern"""
    transcribed = "son of a martyr you're a son of a father you gotta look inside"
    references = {
        "source1": "son of a martyr\nson of a father\nyou can look inside",
        "source2": "son of a mother\nson of a father\nyou can look inside",
    }
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    # Should find at least one of these sequences
    expected_sequences = ["son of a father", "son of a", "of a father"]
    found_sequences = [anchor.text for anchor in anchors]
    assert any(seq in found_sequences for seq in expected_sequences), f"Expected one of {expected_sequences}, but found {found_sequences}"


def test_find_anchors_with_punctuation():
    """Test that punctuation and extra whitespace don't affect matching"""
    transcribed = "hello,  world! test... something"
    references = {"source1": "hello world test", "source2": "hello    world, test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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
        scored = finder._score_anchor(anchor, transcribed)
        priority = finder._get_sequence_priority(scored)
        print(f"Text: '{anchor.text}'")
        print(f"Position: {anchor.transcription_position}")
        print(f"Reference positions: {anchor.reference_positions}")
        print(f"Break score: {scored.phrase_score.natural_break_score}")
        print(f"Total score: {scored.phrase_score.total_score}")
        print(f"Priority: {priority}")
        print(f"Confidence: {anchor.confidence}")

    assert len(anchors) > 0
    assert any("hello world" in anchor.text for anchor in anchors)


def test_find_anchors_respects_word_boundaries():
    """Test that partial word matches aren't considered"""
    transcribed = "testing the tester test"
    references = {"source1": "test the tester", "source2": "testing test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    # Should not match "test" within "testing" or "tester"
    matched_words = set()
    for anchor in anchors:
        matched_words.update(anchor.words)

    assert "testing" not in matched_words or "tester" not in matched_words


def test_find_anchors_minimum_length():
    """Test that sequences shorter than minimum length are not matched"""
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)
    transcribed = "a b c d e"
    references = {"source1": "a b something c d e", "source2": "a b different c d e"}
    anchors = finder.find_anchors(transcribed, references)

    # Should find "c d e" but not "a b"
    assert len(anchors) == 1
    assert anchors[0].text == "c d e"


def test_find_anchors_confidence_calculation():
    """Test that confidence is correctly calculated based on source matches"""
    transcribed = "test sequence here"
    references = {"source1": "test sequence here", "source2": "test sequence here", "source3": "different text entirely"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    assert len(anchors) == 1
    assert anchors[0].confidence == 2 / 3  # matches 2 out of 3 sources


def test_scored_anchor_total_score():
    """Test that ScoredAnchor combines confidence and phrase quality correctly"""
    anchor = AnchorSequence(["hello", "world"], 0, {"source1": 0}, confidence=0.8)
    phrase_score = PhraseScore(phrase_type=PhraseType.COMPLETE, natural_break_score=0.9, length_score=1.0)
    scored_anchor = ScoredAnchor(anchor=anchor, phrase_score=phrase_score)

    # confidence (0.8 * 0.8) + phrase_score.total_score (~0.97 * 0.2) + length_bonus (0.1)
    assert 0.93 <= scored_anchor.total_score <= 0.94


def test_remove_overlapping_sequences_prioritizes_better_phrases(finder):
    """Test that overlapping sequences are resolved by total score"""
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

    # Filter sequences
    filtered = finder._remove_overlapping_sequences(sequences, transcribed)

    # Debug: Print filtered sequences
    print("\nFiltered sequences:")
    for seq in filtered:
        score = finder.phrase_analyzer.score_phrase(seq.words, transcribed)
        print(f"\nSequence: '{seq.text}'")
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")

    # Should prefer the better-scoring sequence
    assert len(filtered) == 1
    assert filtered[0].text == "my heart will go on"


def test_remove_overlapping_sequences_with_line_breaks(finder):
    """Test that natural breaks affect sequence selection"""
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
    for anchor in anchors:
        print(f"Text: '{anchor.text}'")
        print(f"Position: {anchor.transcription_position}")
        print(f"Confidence: {anchor.confidence}")
        score = finder.phrase_analyzer.score_phrase(anchor.words, transcribed)
        print(f"Break score: {score.natural_break_score}")
        print(f"Total score: {score.total_score}")
        print(f"Phrase type: {score.phrase_type}")
        print(f"Length: {len(anchor.words)}")

    # Original assertions
    assert len(anchors) > 0
    assert "my heart will go on" in [a.text for a in anchors]
    assert "go on and" not in [a.text for a in anchors]  # crosses line break


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

    # Debug: Print comparison details
    score1 = finder.phrase_analyzer.score_phrase(seq1.words, transcribed)
    score2 = finder.phrase_analyzer.score_phrase(seq2.words, transcribed)
    print("\nComparing sequences:")
    print(f"seq1 vs seq2: {score1.total_score} vs {score2.total_score}")

    # Get filtered sequences
    filtered = finder._remove_overlapping_sequences(sequences, transcribed)

    # Debug: Print result
    print("\nChosen sequence:")
    chosen = filtered[0]
    score = finder.phrase_analyzer.score_phrase(chosen.words, transcribed)
    print(f"Text: '{chosen.text}'")
    print(f"Length: {len(chosen.words)}")
    print(f"Total score: {score.total_score}")
    print(f"Break score: {score.natural_break_score}")
    print(f"Phrase type: {score.phrase_type}")

    # Should choose the sequence with better score
    assert len(filtered) == 1
    assert filtered[0].text == "my heart will go on"


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


def test_get_sequence_priority(finder):
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
