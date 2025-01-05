import pytest

from lyrics_transcriber.types import AnchorSequence, ScoredAnchor, PhraseScore, PhraseType
from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder


@pytest.fixture
def finder():
    return AnchorSequenceFinder(min_sequence_length=3, min_sources=1)


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


def test_find_anchors_min_sources(finder):
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=2)
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
        print(f"Text: '{anchor.anchor.text}'")
        print(f"Position: {anchor.anchor.transcription_position}")
        print(f"Reference positions: {anchor.anchor.reference_positions}")
        print(f"Confidence: {anchor.anchor.confidence}")

    # Original assertions
    assert len(anchors) == 2
    assert all(anchor.anchor.text == "hello world" for anchor in anchors)
    assert anchors[0].anchor.transcription_position == 0
    assert anchors[1].anchor.transcription_position == 2


def test_find_anchors_with_single_source_repeated_phrase():
    """Test that matches work even if phrase is only repeated in one source"""
    transcribed = "test one two test one two"
    references = {"source1": "test one two something test one two", "source2": "different text entirely"}  # repeated  # no match
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    assert len(anchors) == 2
    assert all(anchor.anchor.text == "test one two" for anchor in anchors)
    assert all(anchor.anchor.confidence == 0.5 for anchor in anchors)  # only matches one source


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
    found_sequences = [anchor.anchor.text for anchor in anchors]
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


def test_find_anchors_respects_word_boundaries():
    """Test that partial word matches aren't considered"""
    transcribed = "testing the tester test"
    references = {"source1": "test the tester", "source2": "testing test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    # Should not match "test" within "testing" or "tester"
    matched_words = set()
    for anchor in anchors:
        matched_words.update(anchor.anchor.words)

    assert "testing" not in matched_words or "tester" not in matched_words


def test_find_anchors_minimum_length():
    """Test that sequences shorter than minimum length are not matched"""
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)
    transcribed = "a b c d e"
    references = {"source1": "a b something c d e", "source2": "a b different c d e"}
    anchors = finder.find_anchors(transcribed, references)

    # Should find "c d e" but not "a b"
    assert len(anchors) == 1
    assert anchors[0].anchor.text == "c d e"


def test_find_anchors_confidence_calculation():
    """Test that confidence is correctly calculated based on source matches"""
    transcribed = "test sequence here"
    references = {"source1": "test sequence here", "source2": "test sequence here", "source3": "different text entirely"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
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


def test_viet_nam_lyrics_scenario():
    """Test based on a song's lyrics pattern"""
    transcribed = "Let's say I got a number\nThat number's fifty thousand\nThat's ten percent of five hundred thousand\nOh, here we are\nIn French Indochina"
    references = {
        "genius": "Let's say I got a number\nThat number's fifty thousand\nThat's ten percent of five hundred thousand\nOh, here we are in French Indochina",
        "spotify": "Let's say I got a number\nThat number's fifty-thousand\nThat's ten percent of five-hundred-thousand\nOh, here we are in French Indochina",
    }
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)

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


def test_viet_nam_first_line():
    """Specific test for the first line of Viet Nam lyrics"""
    transcribed = "Let's say I got a number"
    references = {"genius": "Let's say I got a number", "spotify": "Let's say I got a number"}
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)

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


def test_hyphenated_words():
    """Test that hyphenated words are handled correctly"""
    transcribed = "fifty-thousand five-hundred-thousand"
    references = {"source1": "fifty-thousand five-hundred-thousand", "source2": "fifty thousand five hundred thousand"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_complete_line_matching():
    """Test that complete lines are preferred over partial matches when they exist in all sources."""
    transcribed = "hello world test phrase"
    references = {"source1": "hello world test phrase", "source2": "hello world test phrase"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_complete_line_matching_with_apostrophe():
    """Test that complete lines with apostrophes are handled correctly."""
    transcribed = "let's say I got a number"  # Note the apostrophe
    references = {"source1": "let's say I got a number", "source2": "let's say I got a number"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_complete_line_matching_simple():
    """Test complete line matching with a simpler case to isolate the issue."""
    # Use same word count as "let's say I got a number" but simpler words
    transcribed = "one two three four five six"
    references = {"source1": "one two three four five six", "source2": "one two three four five six"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_break_score_calculation():
    """Test break score calculation with various line formats."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_break_score_with_text_cleaning():
    """Test that break score calculation works correctly with cleaned text."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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


def test_break_score_uses_cleaned_text():
    """Test that break score calculation uses cleaned text rather than original text."""
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)

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
        anchor=AnchorSequence(["test", "phrase"], 2, {"source1": 2}, 1.0),
        phrase_score=PhraseScore(PhraseType.COMPLETE, 1.0, 1.0)
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
            assert gap.transcription_position >= (
                gap.preceding_anchor.transcription_position + len(gap.preceding_anchor.words)
            )

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
