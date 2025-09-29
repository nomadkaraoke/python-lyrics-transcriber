from __future__ import annotations

from typing import Dict, Any

from .providers.config import ProviderConfig


class ModelRouter:
    """Rules-based routing by gap type/length/uncertainty (scaffold)."""

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig.from_env()

    def choose_model(self, gap_type: str, uncertainty: float) -> str:
        # Simple baseline per technical guidance
        if self._config.privacy_mode:
            return "ollama/local-default"
        if uncertainty > 0.5:
            return "anthropic/claude-4-sonnet"
        return "gpt-5"


