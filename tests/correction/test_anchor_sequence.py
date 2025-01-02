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
