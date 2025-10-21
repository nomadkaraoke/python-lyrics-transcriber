from __future__ import annotations

import os
from typing import Dict, Any

from .providers.config import ProviderConfig


class ModelRouter:
    """Rules-based routing by gap type/length/uncertainty (scaffold)."""

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig.from_env()

    def choose_model(self, gap_type: str, uncertainty: float) -> str:
        """Choose appropriate model based on gap characteristics.
        
        Returns model identifier in format "provider/model" for LangChain:
        - "ollama/gpt-oss:latest" for local Ollama models
        - "openai/gpt-4" for OpenAI models  
        - "anthropic/claude-3-sonnet-20240229" for Anthropic models
        """
        # Simple baseline per technical guidance
        if self._config.privacy_mode:
            # Use the actual model from env, or default to a common Ollama model
            return os.getenv("AGENTIC_AI_MODEL", "ollama/gpt-oss:latest")
        
        # For high-uncertainty gaps, use Claude (best reasoning)
        if uncertainty > 0.5:
            return "anthropic/claude-3-sonnet-20240229"
        
        # Default to GPT-4 for general cases
        return "openai/gpt-4"


