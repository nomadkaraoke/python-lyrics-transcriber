from __future__ import annotations

import json
from typing import List, Dict, Any

from .base import BaseAIProvider
from .config import ProviderConfig


class LiteLLMBridge(BaseAIProvider):
    """Unified provider via LiteLLM/OpenRouter-compatible interface.

    This class encapsulates retries/timeouts configured via env, and returns
    structured proposal dictionaries. Actual schema enforcement happens at
    workflow level (Instructor/pydantic-ai).
    """

    def __init__(self, model: str, config: ProviderConfig | None = None):
        self._model = model
        self._config = config or ProviderConfig.from_env()

    def name(self) -> str:
        return f"litellm:{self._model}"

    def generate_correction_proposals(self, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Lazy import to avoid mandatory runtime dependency when unused
        try:
            import litellm  # type: ignore
        except Exception as e:
            raise RuntimeError("litellm is required for LiteLLMBridge") from e

        # Use JSON mode; let upstream enforce schema strictly
        response = litellm.completion(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._config.request_timeout_seconds,
        )

        # Extract text and parse as JSON list or object
        content = response.choices[0].message["content"] if hasattr(response.choices[0], "message") else response["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
        except Exception:
            # Fallback: return as single proposal with raw text; upstream validator will reject/handle
            return [{"raw": content}]

        return []


