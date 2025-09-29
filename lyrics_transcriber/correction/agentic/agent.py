from __future__ import annotations

from typing import Dict, Any, List

from .providers.bridge import LiteLLMBridge
from .providers.config import ProviderConfig
from .models.schemas import CorrectionProposal, CorrectionProposalList
import os


class AgenticCorrector:
    """Main entry for agentic AI correction; minimal scaffold.

    Real logic will be implemented with LangGraph workflows; this class will
    orchestrate provider calls and schema enforcement.
    """

    def __init__(self, model: str, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig.from_env()
        self._provider = LiteLLMBridge(model=model, config=self._config)

    def propose(self, prompt: str) -> List[CorrectionProposal]:
        # If Instructor is available and enabled, use it to enforce schema
        use_instructor = os.getenv("USE_INSTRUCTOR", "").lower() in {"1", "true", "yes"}
        if use_instructor:
            try:
                from instructor import from_litellm  # type: ignore
                import litellm  # type: ignore

                client = from_litellm(litellm)
                result = client.chat.completions.create(
                    model=self._provider._model,  # type: ignore[attr-defined]
                    response_model=CorrectionProposalList,
                    messages=[{"role": "user", "content": prompt}],
                )
                return list(result.proposals)
            except Exception:
                # Fall back to plain provider path
                pass

        data = self._provider.generate_correction_proposals(prompt, schema=CorrectionProposal.model_json_schema())
        # Validate via Pydantic; invalid entries are dropped
        proposals: List[CorrectionProposal] = []
        for item in data:
            try:
                proposals.append(CorrectionProposal.model_validate(item))
            except Exception:
                # Skip invalid proposal; upstream observability can record
                continue
        return proposals


