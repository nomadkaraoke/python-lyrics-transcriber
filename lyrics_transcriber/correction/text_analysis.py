from dataclasses import dataclass
from enum import Enum
from typing import List
import spacy
from spacy.tokens import Doc


class PhraseType(Enum):
    """Types of phrases we can identify"""

    COMPLETE = "complete"  # Grammatically complete unit
    PARTIAL = "partial"  # Incomplete but valid fragment
    CROSS_BOUNDARY = "cross"  # Crosses natural boundaries


@dataclass
class PhraseScore:
    """Scores for a potential phrase"""

    phrase_type: PhraseType
    natural_break_score: float  # 0-1, how well it respects natural breaks
    length_score: float  # 0-1, how appropriate the length is

    @property
    def total_score(self) -> float:
        """Calculate total score with weights"""
        weights = {PhraseType.COMPLETE: 1.0, PhraseType.PARTIAL: 0.7, PhraseType.CROSS_BOUNDARY: 0.3}
        return weights[self.phrase_type] * 0.5 + self.natural_break_score * 0.3 + self.length_score * 0.2


class PhraseAnalyzer:
    """Language-agnostic phrase analyzer using spaCy"""

    def __init__(self, language_code: str = "en_core_web_sm"):
        """Initialize with specific language model"""
        try:
            self.nlp = spacy.load(language_code)
        except OSError:
            raise OSError(
                f"Language model '{language_code}' not found. " f"Please install it with: python -m spacy download {language_code}"
            )

    def score_phrase(self, words: List[str], context: str) -> PhraseScore:
        """Score a phrase based on grammatical completeness and natural breaks.

        Args:
            words: List of words in the phrase
            context: Full text containing the phrase

        Returns:
            PhraseScore with phrase_type, natural_break_score, and length_score
        """
        phrase = " ".join(words)
        phrase_doc = self.nlp(phrase)
        context_doc = self.nlp(context)

        # Get initial phrase type based on grammar
        phrase_type = self._determine_phrase_type(phrase_doc)

        # Calculate scores
        break_score = self._calculate_break_score(phrase_doc, context_doc)
        length_score = self._calculate_length_score(phrase_doc)

        # If break score is 0 (crosses boundary), override to CROSS_BOUNDARY
        if break_score == 0.0:
            phrase_type = PhraseType.CROSS_BOUNDARY

        return PhraseScore(phrase_type=phrase_type, natural_break_score=break_score, length_score=length_score)

    def _determine_phrase_type(self, doc: Doc) -> PhraseType:
        """Determine the grammatical type of a phrase using SpaCy's linguistic analysis.

        This method categorizes text into three types:
        1. COMPLETE: A grammatically complete clause with subject and predicate
           Examples: "I love you", "the cat sleeps"
           - Subject (I, the cat) + Predicate (love you, sleeps)

        2. PARTIAL: A valid but incomplete grammatical unit, which can be:
           a) Noun phrase: A group of words with a noun as the head
              Example: "the big cat"
              - Determiner (the) + Adjective (big) + Noun (cat)

           b) Verb phrase: A group of words with a verb as the head
              Example: "running fast"
              - Verb (running) + Adverb (fast)

           c) Prepositional phrase: Starting with a preposition
              Example: "in my heart"
              - Preposition (in) + Noun phrase (my heart)

           d) Adverb phrase: A group of words with an adverb as the head
              Example: "très rapidement" (French: "very quickly")
              - Adverb (très) + Adverb (rapidement)

        3. CROSS_BOUNDARY: Invalid grammatical structure
           Examples: "cat the big", "love but the"
           - Words in unnatural order or incomplete structures

        Args:
            doc: SpaCy Doc object containing the parsed text

        Returns:
            PhraseType: COMPLETE, PARTIAL, or CROSS_BOUNDARY
        """

        def is_complete_clause():
            """Check if the text forms a complete clause.

            Different languages mark subject-verb relationships differently:
            English/French:
            - Subject has nsubj/nsubjpass dependency
            - Verb is ROOT

            Spanish:
            - Sometimes marks pronoun as ROOT
            - Verb can be marked as flat/aux
            """
            # Standard subject-verb pattern (English/French)
            standard_pattern = any(token.dep_ in {"nsubj", "nsubjpass"} for token in doc) and any(
                token.dep_ == "ROOT" and token.pos_ == "VERB" for token in doc
            )

            # Spanish pronoun-verb pattern
            spanish_pattern = (
                len(doc) == 2  # Two-word phrase
                and doc[0].pos_ == "PRON"  # First word is pronoun
                and doc[1].pos_ in {"VERB", "AUX", "ADJ"}  # Second word is verb-like
                and doc[1].dep_ in {"flat", "aux"}  # Common Spanish dependencies
            )

            return standard_pattern or spanish_pattern

        def is_valid_noun_phrase():
            """Check if the text is a valid noun phrase like "the big cat".

            Valid noun phrases:
            - "the cat" (determiner + noun)
            - "the big cat" (determiner + adjective + noun)
            - "my heart" (possessive + noun)

            Invalid noun phrases:
            - "the war waterloo" (looks like a compound but semantically invalid)
            - "cat the big" (wrong word order)
            """
            chunks = list(doc.noun_chunks)
            if not chunks:
                return False

            # The noun phrase should be the entire text
            chunk = chunks[0]
            if not (chunk.start == 0 and chunk.end == len(doc)):
                return False

            # Check for valid noun phrase structure:
            # 1. Should have at most one main noun (ROOT)
            # 2. Compounds should be common English compounds (we can't verify this easily,
            #    so we'll be conservative and reject most compounds)
            root_nouns = [t for t in doc if t.dep_ == "ROOT" and t.pos_ in {"NOUN", "PROPN"}]
            compounds = [t for t in doc if t.dep_ == "compound"]

            if len(root_nouns) != 1 or len(compounds) > 0:
                return False

            return True

        def is_valid_verb_phrase():
            """Check if the text is a valid verb phrase like "running fast".

            A verb phrase must:
            1. Contain a verb
            2. Only use valid verb phrase dependencies:
               - ROOT: The main verb ("running" in "running fast")
               - advmod: Adverbial modifier ("fast" in "running fast")
               - dobj: Direct object ("ball" in "throw ball")
               - prt: Particle ("up" in "wake up")
               - prep: Preposition ("in" in "believe in")
               - pobj: Object of preposition ("box" in "think inside box")
               - compound:prt: Phrasal verb particle ("up" in "pick up")
            """
            # Must have at least one verb
            has_verb = any(token.pos_ == "VERB" for token in doc)

            # Define valid dependency types for verb phrases
            VALID_DEPS = {
                "ROOT",  # Main verb
                "advmod",  # Adverbial modifier
                "dobj",  # Direct object
                "prt",  # Verb particle
                "prep",  # Preposition
                "pobj",  # Object of preposition
                "compound:prt",  # Phrasal verb particle
            }

            # All words must have valid dependency relationships
            has_valid_deps = all(token.dep_ in VALID_DEPS for token in doc)

            return has_verb and has_valid_deps

        def is_valid_prep_phrase():
            """Check if the text is a valid prepositional phrase like "in my heart".
            A prepositional phrase must:
            - Start with a preposition
            - Have at least one more word
            - Include an object of the preposition

            Examples:
            - "in my heart" (English)
            - "dans la maison" (French: "in the house")
            - "en la casa" (Spanish: "in the house")

            Note: Different languages use different dependency labels:
            - English: prep + pobj
            - French: case + ROOT
            - Spanish: case + ROOT
            """
            # Check if it starts with a preposition
            starts_with_prep = doc[0].pos_ == "ADP"

            # Check if there's content after the preposition
            has_content = len(doc) > 1

            # Check for valid structure (either English style or French/Spanish style)
            has_valid_structure = any(t.dep_ == "pobj" for t in doc) or (  # English style
                doc[0].dep_ == "case" and any(t.dep_ == "ROOT" for t in doc)
            )  # French/Spanish style

            return starts_with_prep and has_content and has_valid_structure

        def is_valid_adverb_phrase():
            """Check if the text is a valid adverbial phrase like "très rapidement".
            An adverb phrase must:
            - Have an adverb as the root OR an adjective modified by an adverb
            - Only contain adverbs/adjectives and their modifiers

            Examples:
            - "très rapidement" (French: "very quickly")
            - "muy rápido" (Spanish: "very fast")
            - "very quickly" (English)

            Note: Different languages mark adverbial phrases differently:
            - French: ADV + ADV
            - Spanish: ADV + ADJ
            - English: ADV + ADV/ADJ
            """
            # Check for adverb as root (French style)
            has_adverb_root = any(token.pos_ == "ADV" and token.dep_ == "ROOT" for token in doc)

            # Check for adjective as root with adverb modifier (Spanish style)
            has_adj_root_with_adv = any(token.pos_ == "ADJ" and token.dep_ == "ROOT" for token in doc) and any(
                token.pos_ == "ADV" and token.dep_ == "advmod" for token in doc
            )

            # All words must be valid modifiers
            has_valid_deps = all(token.dep_ in {"ROOT", "advmod", "fixed", "goeswith"} and token.pos_ in {"ADV", "ADJ"} for token in doc)

            return (has_adverb_root or has_adj_root_with_adv) and has_valid_deps

        # First check if it's a complete clause
        if is_complete_clause():
            return PhraseType.COMPLETE

        # Check if it's a valid partial phrase
        if is_valid_noun_phrase() or is_valid_verb_phrase() or is_valid_prep_phrase() or is_valid_adverb_phrase():
            # Additional check: if the phrase crosses sentence boundaries,
            # it should be CROSS_BOUNDARY even if it's grammatically valid
            text = doc.text
            context = doc.text  # The full text containing this phrase
            if "." in text:  # Simple check for sentence boundary within phrase
                return PhraseType.CROSS_BOUNDARY
            return PhraseType.PARTIAL

        return PhraseType.CROSS_BOUNDARY

    def _calculate_break_score(self, phrase_doc: Doc, context_doc: Doc) -> float:
        """Calculate how well the phrase respects natural breaks in the text.

        Scores are based on alignment with line breaks and sentence boundaries:
        1.0 - Perfect alignment (matches full line or sentence)
        0.8-0.9 - Strong alignment (matches most of a natural unit)
        0.5-0.7 - Partial alignment (matches start or end of unit)
        0.0 - Poor alignment (crosses line/sentence boundary)

        Examples from tests:
        "my heart will go on" -> 1.0 (matches full line)
        "go on and" -> 0.0 (crosses line break)
        "Hello world" -> 1.0 (matches complete sentence)
        "world How" -> 0.0 (crosses sentence boundary)
        "I wake up" -> 0.85 (strong alignment with verb phrase)
        """
        phrase_text = phrase_doc.text
        phrase_start = context_doc.text.find(phrase_text)

        if phrase_start == -1:
            return 0.0

        phrase_end = phrase_start + len(phrase_text)
        context_text = context_doc.text

        # Check for line breaks
        lines = context_text.split("\n")
        for line in lines:
            line_start = context_text.find(line)
            line_end = line_start + len(line)

            # Perfect match with a full line
            if phrase_start == line_start and phrase_end == line_end:
                return 1.0

            # Strong alignment with most of a line
            if (phrase_start == line_start and phrase_end > line_start + len(line) * 0.7) or (
                phrase_end == line_end and phrase_start < line_end - len(line) * 0.7
            ):
                return 0.9

            # Crosses line boundary
            if any(phrase_start < context_text.find("\n", i) < phrase_end for i in range(len(context_text)) if "\n" in context_text[i:]):
                return 0.0

        # Check for sentence boundaries
        for sent in context_doc.sents:
            sent_start = sent.start_char
            sent_end = sent.end_char

            # Perfect match with a full sentence
            if phrase_start == sent_start and phrase_end == sent_end:
                return 1.0

            # Strong alignment with most of a sentence
            if phrase_start >= sent_start and phrase_end <= sent_end:
                # Check if it's a verb phrase
                has_verb = any(token.pos_ == "VERB" for token in phrase_doc)
                has_subject = any(token.dep_ in {"nsubj", "nsubjpass"} for token in phrase_doc)

                # Phrase is contained within sentence
                phrase_len = phrase_end - phrase_start
                sent_len = sent_end - sent_start
                coverage = phrase_len / sent_len

                if has_verb and has_subject:  # Subject-verb combinations get highest scores
                    return 0.85
                elif has_verb and coverage > 0.3:  # Other verb phrases
                    return 0.8
                elif coverage > 0.5:  # Other phrases need more coverage
                    return 0.8
                return 0.7

            # Crosses sentence boundary
            if any(phrase_start < s.start_char < phrase_end for s in context_doc.sents):
                return 0.0

        # Partial match (aligns with start or end)
        return 0.5

    def _calculate_length_score(self, doc: Doc) -> float:
        """Calculate score based on phrase length and complexity.

        Scores are based on the number of meaningful linguistic units:
        - Noun chunks ("the big cat", "the mat")
        - Verbs ("sleeps")
        - Adverbial modifiers ("soundly")
        - Prepositional phrases ("on the mat")

        Scoring scale:
        0.0 - No meaningful units
        0.9 - One unit (e.g., "the cat")
        1.0 - Two units (e.g., "the cat sleeps")
        0.8 - Three units (e.g., "the big cat sleeps quickly")
        0.6 - Four or more units (e.g., "the big cat sleeps soundly on the mat")

        Examples from tests:
        "the cat" -> 1 unit (noun chunk) -> 0.9
        "the cat sleeps" -> 2 units (noun chunk + verb) -> 1.0
        "the big cat sleeps soundly on the mat" -> 4 units (noun chunk + verb + adverb + prep phrase) -> 0.6
        """
        # Count meaningful linguistic units
        units = 0

        # Count noun chunks
        units += len(list(doc.noun_chunks))

        # Count verbs
        units += len([token for token in doc if token.pos_ == "VERB"])

        # Count adverbial modifiers
        units += len([token for token in doc if token.dep_ == "advmod"])

        # Count prepositional phrases (each preposition usually introduces a new phrase)
        units += len([token for token in doc if token.dep_ == "prep"])

        # Score based on complexity
        if units == 0:
            return 0.0
        elif units == 1:
            return 0.9  # Simple phrase
        elif units == 2:
            return 1.0  # Optimal complexity
        elif units == 3:
            return 0.8  # Slightly complex
        return 0.6  # Too complex
