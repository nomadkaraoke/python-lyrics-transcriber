from __future__ import annotations

from typing import List, Dict, Any

from .base import BaseAIProvider
from .bridge import LiteLLMBridge
from .config import ProviderConfig


class AnthropicProvider(BaseAIProvider):
    """Anthropic provider wrapper delegating to LiteLLMBridge."""

    def __init__(self, model: str = "anthropic/claude-4-sonnet", config: ProviderConfig | None = None):
        self._delegate = LiteLLMBridge(model=model, config=config)

    def name(self) -> str:
        return f"anthropic:{self._delegate._model}"  # type: ignore[attr-defined]

    def generate_correction_proposals(self, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._delegate.generate_correction_proposals(prompt, schema)


