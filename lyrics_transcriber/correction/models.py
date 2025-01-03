from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any


@dataclass
class WordCorrection:
    """Details about a single word correction."""

    original_word: str
    corrected_word: str
    segment_index: int
    word_index: int
    source: str  # e.g., "spotify", "genius"
    confidence: Optional[float]
    reason: str  # e.g., "matched_in_3_sources", "high_confidence_match"
    alternatives: Dict[str, int]  # Other possible corrections and their occurrence counts

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
