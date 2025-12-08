from lyrics_transcriber.correction.agentic.adapter import adapt_proposals_to_word_corrections
from lyrics_transcriber.correction.agentic.models.schemas import CorrectionProposal
from lyrics_transcriber.types import Word


def test_adapt_proposals_to_word_corrections_basic():
    wmap = {"w1": Word(id="w1", text="wurld", start_time=0.0, end_time=0.5)}
    pos = {"w1": 0}
    proposals = [CorrectionProposal(word_id="w1", action="ReplaceWord", replacement_text="world", confidence=0.9, reason="spell")] 
    corrections = adapt_proposals_to_word_corrections(proposals, wmap, pos)
    assert corrections and corrections[0].corrected_word == "world"


