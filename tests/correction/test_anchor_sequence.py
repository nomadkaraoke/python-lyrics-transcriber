import pytest
from lyrics_transcriber.correction.anchor_sequence import AnchorSequence, AnchorSequenceFinder


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
    filtered = finder._remove_overlapping_sequences(anchors)
    assert len(filtered) == 1
    assert filtered[0].words == ["a", "b", "c"]


def test_find_anchors_simple(finder):
    transcribed = "hello world test"
    references = {"source1": "hello world different", "source2": "hello world test"}
    anchors = finder.find_anchors(transcribed, references)
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


def test_find_anchors_with_repeated_phrases():
    """Test that repeated phrases in transcription are only matched if they're also repeated in references"""
    transcribed = "hello world hello world hello world"
    references = {"source1": "hello world something hello world", "source2": "hello world only once"}  # repeated twice  # appears once
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

    # Should only find two occurrences, as that's the maximum times it appears in any reference
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

    # Should find "son of a father" at minimum
    assert any(anchor.text == "son of a father" for anchor in anchors)
    # "son of a" might appear separately depending on overlap handling
    texts = [anchor.text for anchor in anchors]
    assert "son of a father" in texts


def test_find_anchors_with_punctuation():
    """Test that punctuation and extra whitespace don't affect matching"""
    transcribed = "hello,  world! test... something"
    references = {"source1": "hello world test", "source2": "hello    world, test"}
    finder = AnchorSequenceFinder(min_sequence_length=2, min_sources=1)
    anchors = finder.find_anchors(transcribed, references)

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


def test_real_world_lyrics_scenario_debug():
    """Debug test for real-world lyrics pattern"""
    transcribed = "son of a martyr you're a son of a father you gotta look inside"
    references = {
        "source1": "son of a martyr\nson of a father\nyou can look inside",
        "source2": "son of a mother\nson of a father\nyou can look inside",
    }
    finder = AnchorSequenceFinder(min_sequence_length=3, min_sources=1)

    # Clean and split texts for inspection
    trans_words = finder._clean_text(transcribed).split()
    ref_texts_clean = {source: finder._clean_text(text).split() for source, text in references.items()}

    print("\nTranscribed words:", trans_words)
    print("\nReference texts:")
    for source, words in ref_texts_clean.items():
        print(f"{source}: {words}")

    # Find all possible n-grams of length 4 (for "son of a father")
    target_length = 4
    trans_ngrams = finder._find_ngrams(trans_words, target_length)
    print("\nTranscribed 4-grams:")
    for ngram, pos in trans_ngrams:
        print(f"Position {pos}: {ngram}")
        # Check if this n-gram appears in references
        for source, ref_words in ref_texts_clean.items():
            for i in range(len(ref_words) - target_length + 1):
                if ref_words[i : i + target_length] == ngram:
                    print(f"  Found in {source} at position {i}")

    # Get actual anchors
    anchors = finder.find_anchors(transcribed, references)
    print("\nFound anchors:")
    for anchor in anchors:
        print(f"Text: '{anchor.text}' at position {anchor.transcription_position} (confidence: {anchor.confidence})")

    # Original assertions
    assert any(anchor.text == "son of a father" for anchor in anchors)
    texts = [anchor.text for anchor in anchors]
    assert "son of a father" in texts
