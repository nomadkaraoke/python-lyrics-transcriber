from __future__ import annotations

from typing import Dict, Any, List

from .models.schemas import CorrectionProposal
from lyrics_transcriber.types import WordCorrection, Word


def adapt_proposals_to_word_corrections(
    proposals: List[CorrectionProposal],
    word_map: Dict[str, Word],
    linear_position_map: Dict[str, int],
) -> List[WordCorrection]:
    """Convert CorrectionProposal items into WordCorrection objects.

    Minimal mapping: supports ReplaceWord and DeleteWord actions with single word_id.
    Unknown or unsupported actions are ignored.
    """
    results: List[WordCorrection] = []
    for p in proposals:
        action = (p.action or "").lower()
        target_id = p.word_id or (p.word_ids[0] if p.word_ids else None)
        if not target_id or target_id not in word_map:
            continue
        original = word_map[target_id]
        original_position = linear_position_map.get(target_id, 0)

        if action == "replaceword" and p.replacement_text:
            results.append(
                WordCorrection(
                    original_word=original.text,
                    corrected_word=p.replacement_text,
                    original_position=original_position,
                    source="agentic",
                    reason=p.reason or "agentic_proposal",
                    confidence=float(p.confidence or 0.0),
                    is_deletion=False,
                    word_id=target_id,
                )
            )
        elif action == "deleteword":
            results.append(
                WordCorrection(
                    original_word=original.text,
                    corrected_word="",
                    original_position=original_position,
                    source="agentic",
                    reason=p.reason or "agentic_proposal",
                    confidence=float(p.confidence or 0.0),
                    is_deletion=True,
                    word_id=target_id,
                )
            )

    return results


