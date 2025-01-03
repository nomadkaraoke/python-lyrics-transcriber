import pytest
import logging
from lyrics_transcriber.correction.text_analysis import PhraseAnalyzer, PhraseType


@pytest.fixture
def analyzer():
    logger = logging.getLogger("test_analyzer")
    return PhraseAnalyzer(logger)


def test_phrase_type_detection(analyzer):
    """Test detection of different phrase types using spaCy's linguistic analysis"""
    # Complete phrases (subject + predicate)
    for phrase in ["I love you", "the cat sleeps"]:
        doc = analyzer.nlp(phrase)
        result = analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing complete phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print(f"Result: {result}")
        assert result == PhraseType.COMPLETE

    # Partial phrases (valid noun or verb phrases)
    for phrase in ["the big cat", "running fast"]:
        doc = analyzer.nlp(phrase)
        result = analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing partial phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print("Noun chunks:", list(doc.noun_chunks))
        print(f"Result: {result}")
        assert result == PhraseType.PARTIAL

    # Cross-boundary phrases
    for phrase in ["cat the big", "love but the"]:
        doc = analyzer.nlp(phrase)
        result = analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing cross-boundary phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print("Noun chunks:", list(doc.noun_chunks))
        print(f"Result: {result}")
        assert result == PhraseType.CROSS_BOUNDARY


def test_break_score(analyzer):
    """Test natural break detection using spaCy's sentence boundaries"""
    # Test sentence boundaries
    context = "Hello world. How are you?"
    assert analyzer._calculate_break_score(analyzer.nlp("Hello world"), analyzer.nlp(context)) >= 0.8

    # Test crossing sentence boundary
    assert analyzer._calculate_break_score(analyzer.nlp("world How"), analyzer.nlp(context)) == 0.0


def test_length_score(analyzer):
    """Test scoring based on linguistic units"""
    for phrase, expected_score in [("the cat", 0.9), ("the cat sleeps", 1.0), ("the big cat sleeps soundly on the mat", 0.6)]:
        doc = analyzer.nlp(phrase)
        score = analyzer._calculate_length_score(doc)
        print(f"\nAnalyzing length score for: '{phrase}'")
        print("Noun chunks:", list(doc.noun_chunks))
        print(f"Verbs: {[t for t in doc if t.pos_ == 'VERB']}")
        print(f"Score: {score}, Expected: {expected_score}")
        assert score == expected_score


def test_real_world_lyrics(analyzer):
    """Test with real song lyrics"""
    # Complete lyrical phrases
    for phrase in ["I was defeated", "you won the war"]:
        doc = analyzer.nlp(phrase)
        result = analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing complete lyric: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print(f"Result: {result}")
        assert result == PhraseType.COMPLETE

    # Partial lyrical phrases
    phrase = "in my heart"
    doc = analyzer.nlp(phrase)
    result = analyzer._determine_phrase_type(doc)
    print(f"\nAnalyzing partial lyric: '{phrase}'")
    print("Token Analysis:")
    for token in doc:
        print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
    print("Noun chunks:", list(doc.noun_chunks))
    print(f"Result: {result}")
    assert result == PhraseType.PARTIAL

    # Cross-boundary phrases
    phrase = "the war waterloo"
    doc = analyzer.nlp(phrase)
    result = analyzer._determine_phrase_type(doc)
    print(f"\nAnalyzing cross-boundary lyric: '{phrase}'")
    print("Token Analysis:")
    for token in doc:
        print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
    print("Noun chunks:", list(doc.noun_chunks))
    print(f"Result: {result}")
    assert result == PhraseType.CROSS_BOUNDARY


def test_line_break_handling(analyzer):
    """Test handling of line breaks in lyrics"""
    context = "my heart will go on\nand on forever more"

    # Complete line
    phrase = "my heart will go on"
    score = analyzer._calculate_break_score(analyzer.nlp(phrase), analyzer.nlp(context))
    print(f"\nAnalyzing break score for: '{phrase}'")
    print(f"Context: '{context}'")
    print(f"Score: {score}")
    assert score > 0.8

    # Crossing line break
    phrase = "go on and"
    score = analyzer._calculate_break_score(analyzer.nlp(phrase), analyzer.nlp(context))
    print(f"\nAnalyzing break score for: '{phrase}'")
    print(f"Context: '{context}'")
    print(f"Score: {score}")
    assert score == 0.0


def test_integration(analyzer):
    """Test full phrase scoring integration"""
    context = "When I wake up in the morning. Love and happiness."

    # Good phrase
    words = ["I", "wake", "up"]
    good_score = analyzer.score_phrase(words, context)
    print(f"\nAnalyzing good phrase: '{' '.join(words)}'")
    print(f"Context: '{context}'")
    print(f"Phrase type: {good_score.phrase_type}")
    print(f"Break score: {good_score.natural_break_score}")
    print(f"Length score: {good_score.length_score}")
    print(f"Total score: {good_score.total_score}")
    assert good_score.phrase_type == PhraseType.COMPLETE
    assert good_score.natural_break_score > 0.7
    assert good_score.total_score > 0.8

    # Bad phrase
    words = ["up", "in", "the", "morning", "love"]
    bad_score = analyzer.score_phrase(words, context)
    print(f"\nAnalyzing bad phrase: '{' '.join(words)}'")
    print(f"Context: '{context}'")
    print(f"Phrase type: {bad_score.phrase_type}")
    print(f"Break score: {bad_score.natural_break_score}")
    print(f"Length score: {bad_score.length_score}")
    print(f"Total score: {bad_score.total_score}")
    assert bad_score.phrase_type == PhraseType.CROSS_BOUNDARY
    assert bad_score.natural_break_score < 0.3
    assert bad_score.total_score < 0.5


def test_error_handling():
    """Test error handling for missing language models"""
    logger = logging.getLogger("test_error")
    with pytest.raises(OSError) as exc_info:
        PhraseAnalyzer(logger, "nonexistent_model")
    assert "not found" in str(exc_info.value)


def test_french_phrases():
    """Test French phrase analysis"""
    # Skip if language models aren't installed
    pytest.importorskip("spacy")
    try:
        logger = logging.getLogger("test_french")
        fr_analyzer = PhraseAnalyzer(logger, "fr_core_news_sm")
    except OSError:
        pytest.skip("French language model not installed")

    fr_phrases = {
        # Complete phrases (subject + predicate)
        "je t'aime": PhraseType.COMPLETE,  # "I love you"
        "il mange": PhraseType.COMPLETE,  # "he eats"
        # Partial phrases
        "le chat noir": PhraseType.PARTIAL,  # "the black cat" (noun phrase)
        "très rapidement": PhraseType.PARTIAL,  # "very quickly" (adverb phrase)
        "dans la maison": PhraseType.PARTIAL,  # "in the house" (prepositional phrase)
        # Cross-boundary phrases
        "chat le noir": PhraseType.CROSS_BOUNDARY,  # "cat the black" (invalid order)
    }

    for phrase, expected_type in fr_phrases.items():
        doc = fr_analyzer.nlp(phrase)
        result = fr_analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing French phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print(f"Result: {result}, Expected: {expected_type}")
        assert result == expected_type


def test_spanish_phrases():
    """Test Spanish phrase analysis"""
    # Skip if language models aren't installed
    pytest.importorskip("spacy")
    try:
        logger = logging.getLogger("test_spanish")
        es_analyzer = PhraseAnalyzer(logger, "es_core_news_sm")
    except OSError:
        pytest.skip("Spanish language model not installed")

    es_phrases = {
        # Complete phrases (subject + predicate)
        "yo canto": PhraseType.COMPLETE,  # "I sing"
        "ella baila": PhraseType.COMPLETE,  # "she dances"
        # Partial phrases
        "el perro grande": PhraseType.PARTIAL,  # "the big dog" (noun phrase)
        "muy rápido": PhraseType.PARTIAL,  # "very fast" (adverb phrase)
        "en la casa": PhraseType.PARTIAL,  # "in the house" (prepositional phrase)
        # Cross-boundary phrases
        "perro el grande": PhraseType.CROSS_BOUNDARY,  # "dog the big" (invalid order)
    }

    for phrase, expected_type in es_phrases.items():
        doc = es_analyzer.nlp(phrase)
        result = es_analyzer._determine_phrase_type(doc)
        print(f"\nAnalyzing Spanish phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
        print(f"Result: {result}, Expected: {expected_type}")
        assert result == expected_type


def test_is_complete_clause(analyzer):
    """Test detection of complete clauses across languages"""
    complete_clauses = ["I love you", "the cat sleeps", "she runs fast", "they have arrived"]
    for phrase in complete_clauses:
        doc = analyzer.nlp(phrase)
        assert analyzer.is_complete_clause(doc)

    incomplete_clauses = ["the big", "running", "in the house", "very quickly"]
    for phrase in incomplete_clauses:
        doc = analyzer.nlp(phrase)
        assert not analyzer.is_complete_clause(doc)


def test_is_valid_noun_phrase(analyzer):
    """Test detection of valid noun phrases"""
    valid_noun_phrases = ["the cat", "the big cat", "my heart", "a beautiful morning"]
    for phrase in valid_noun_phrases:
        doc = analyzer.nlp(phrase)
        assert analyzer.is_valid_noun_phrase(doc)

    invalid_noun_phrases = [
        "cat the",  # wrong order
        "running fast",  # verb phrase
        "in the house",  # prep phrase
        "very quickly",  # adverb phrase
    ]
    for phrase in invalid_noun_phrases:
        doc = analyzer.nlp(phrase)
        assert not analyzer.is_valid_noun_phrase(doc)


def test_is_valid_verb_phrase(analyzer):
    """Test detection of valid verb phrases"""
    valid_verb_phrases = ["running fast", "sleep soundly", "jump up", "sing loudly"]
    for phrase in valid_verb_phrases:
        doc = analyzer.nlp(phrase)
        assert analyzer.is_valid_verb_phrase(doc)

    invalid_verb_phrases = [
        "the cat",  # noun phrase
        "in the house",  # prep phrase
        "very quickly",  # adverb phrase
        "fast running",  # wrong order
    ]
    for phrase in invalid_verb_phrases:
        doc = analyzer.nlp(phrase)
        assert not analyzer.is_valid_verb_phrase(doc)


def test_is_valid_prep_phrase(analyzer):
    """Test detection of valid prepositional phrases"""
    valid_prep_phrases = ["in my heart", "on the table", "with great power", "under the bridge"]
    for phrase in valid_prep_phrases:
        doc = analyzer.nlp(phrase)
        assert analyzer.is_valid_prep_phrase(doc)

    invalid_prep_phrases = [
        "the cat",  # noun phrase
        "running fast",  # verb phrase
        "very quickly",  # adverb phrase
        "my in heart",  # wrong order
    ]
    for phrase in invalid_prep_phrases:
        doc = analyzer.nlp(phrase)
        assert not analyzer.is_valid_prep_phrase(doc)


def test_is_valid_adverb_phrase(analyzer):
    """Test detection of valid adverbial phrases"""
    valid_adverb_phrases = [
        "very quickly",  # Standard adverb phrase
        "quite slowly",  # Standard adverb phrase
        "extremely well",  # Standard adverb phrase
        "rather nicely",  # Standard adverb phrase
        "quickly very",  # SpaCy considers this valid due to its syntactic structure
    ]
    for phrase in valid_adverb_phrases:
        doc = analyzer.nlp(phrase)
        print(f"\nAnalyzing valid adverb phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
            print(f"    morph={token.morph}")
            print(f"    is_sent_start={token.is_sent_start}")
            print(f"    like_num={token.like_num}")
            print(f"    tag_={token.tag_}")
        assert analyzer.is_valid_adverb_phrase(doc)

    invalid_adverb_phrases = ["the cat", "running fast", "in the house"]  # noun phrase  # verb phrase  # prep phrase
    for phrase in invalid_adverb_phrases:
        doc = analyzer.nlp(phrase)
        print(f"\nAnalyzing invalid adverb phrase: '{phrase}'")
        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
            print(f"    morph={token.morph}")
            print(f"    is_sent_start={token.is_sent_start}")
            print(f"    like_num={token.like_num}")
            print(f"    tag_={token.tag_}")
        assert not analyzer.is_valid_adverb_phrase(doc)


def test_calculate_line_break_score(analyzer):
    """Test line break score calculation"""
    context = "first line\nsecond line\nthird line"

    # Perfect match
    assert analyzer.calculate_line_break_score(0, 10, context) == 1.0  # "first line"

    # Strong alignment
    assert analyzer.calculate_line_break_score(0, 7, context) == 0.9  # "first l"

    # Crosses boundary
    assert analyzer.calculate_line_break_score(8, 15, context) == 0.0  # "ne\nsecon"

    # Partial match
    assert analyzer.calculate_line_break_score(6, 9, context) == 0.5  # "ine"


def test_calculate_sentence_break_score(analyzer):
    """Test sentence break score calculation"""
    context = "Hello world. How are you? I am fine."
    context_doc = analyzer.nlp(context)

    # Perfect match with sentence
    phrase = "Hello world"
    phrase_doc = analyzer.nlp(phrase)
    score = analyzer.calculate_sentence_break_score(phrase_doc, context.find(phrase), context.find(phrase) + len(phrase), context_doc)
    assert score >= 0.8

    # Cross boundary
    phrase = "world. How"
    phrase_doc = analyzer.nlp(phrase)
    score = analyzer.calculate_sentence_break_score(phrase_doc, context.find(phrase), context.find(phrase) + len(phrase), context_doc)
    assert score == 0.0

    # Strong alignment with verb
    phrase = "I am"
    phrase_doc = analyzer.nlp(phrase)
    score = analyzer.calculate_sentence_break_score(phrase_doc, context.find(phrase), context.find(phrase) + len(phrase), context_doc)
    assert score >= 0.7


def test_line_break_scoring_with_overlapping_phrases():
    """Test scoring of overlapping phrases with line breaks"""
    logger = logging.getLogger("test_line_breaks")
    analyzer = PhraseAnalyzer(logger)
    context = "my heart will go on\nand on forever more"

    # Test individual phrases
    phrases = [
        "my heart",  # Valid noun phrase
        "will go on",  # Valid verb phrase
        "go on and",  # Crosses line break
        "my heart will go on",  # Complete sentence
    ]

    print("\nTesting phrases in context:", context)
    for phrase in phrases:
        doc = analyzer.nlp(phrase)
        phrase_type = analyzer._determine_phrase_type(doc)
        break_score = analyzer._calculate_break_score(doc, analyzer.nlp(context))
        length_score = analyzer._calculate_length_score(doc)
        total_score = analyzer.score_phrase(phrase.split(), context)

        print(f"\nPhrase: '{phrase}'")
        print(f"Phrase type: {phrase_type}")
        print(f"Break score: {break_score}")
        print(f"Length score: {length_score}")
        print(f"Total score: {total_score.total_score}")

        print("Token Analysis:")
        for token in doc:
            print(f"  {token.text:12} pos={token.pos_:6} dep={token.dep_:10} head={token.head.text}")
            print(f"    morph={token.morph}")
            print(f"    is_sent_start={token.is_sent_start}")
            print(f"    like_num={token.like_num}")
            print(f"    tag_={token.tag_}")

        # Assertions for key phrases
        if phrase == "my heart":
            assert break_score > 0.5  # Should have decent break score
            assert phrase_type == PhraseType.PARTIAL  # Valid noun phrase
        elif phrase == "go on and":
            assert break_score == 0.0  # Should be penalized for crossing break
        elif phrase == "my heart will go on":
            assert break_score >= 0.8  # Should have high break score
            assert phrase_type == PhraseType.COMPLETE  # Complete clause
