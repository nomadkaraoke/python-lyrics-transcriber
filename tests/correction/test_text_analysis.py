import pytest
from lyrics_transcriber.correction.text_analysis import PhraseAnalyzer, PhraseType


@pytest.fixture
def analyzer():
    return PhraseAnalyzer()


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
    with pytest.raises(OSError) as exc_info:
        PhraseAnalyzer("nonexistent_model")
    assert "not found" in str(exc_info.value)


def test_french_phrases():
    """Test French phrase analysis"""
    # Skip if language models aren't installed
    pytest.importorskip("spacy")
    try:
        fr_analyzer = PhraseAnalyzer("fr_core_news_sm")
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
        es_analyzer = PhraseAnalyzer("es_core_news_sm")
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
