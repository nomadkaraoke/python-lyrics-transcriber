from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, conint, confloat


class CorrectionProposal(BaseModel):
    word_id: Optional[str] = Field(None, description="ID of the word to correct")
    word_ids: Optional[List[str]] = Field(None, description="IDs of multiple words when applicable")
    action: str = Field(..., description="ReplaceWord|SplitWord|DeleteWord|AdjustTiming")
    replacement_text: Optional[str] = Field(None, description="Text to insert/replace with")
    timing_delta_ms: Optional[conint(ge=-1000, le=1000)] = None
    confidence: confloat(ge=0.0, le=1.0) = 0.0
    reason: str = Field(..., description="Short rationale for the proposal")


class CorrectionProposalList(BaseModel):
    proposals: List[CorrectionProposal]


