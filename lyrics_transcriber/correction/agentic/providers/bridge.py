from __future__ import annotations

import json
from typing import List, Dict, Any

from .base import BaseAIProvider
from .config import ProviderConfig
import time
import random
from typing import ClassVar, Tuple


class LiteLLMBridge(BaseAIProvider):
    """Unified provider via LiteLLM/OpenRouter-compatible interface.

    This class encapsulates retries/timeouts configured via env, and returns
    structured proposal dictionaries. Actual schema enforcement happens at
    workflow level (Instructor/pydantic-ai).
    """

    # Circuit breaker state per model
    _failures: ClassVar[dict[str, int]] = {}
    _open_until: ClassVar[dict[str, float]] = {}

    def __init__(self, model: str, config: ProviderConfig | None = None):
        self._model = model
        self._config = config or ProviderConfig.from_env()

    def name(self) -> str:
        return f"litellm:{self._model}"

    def generate_correction_proposals(self, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Circuit breaker: if open, short-circuit
        now = time.time()
        open_until = self._open_until.get(self._model, 0)
        if now < open_until:
            return [{"error": "circuit_open", "until": open_until}]

        # Lazy import to avoid mandatory runtime dependency when unused
        try:
            import litellm  # type: ignore
        except Exception as e:
            # Count as failure and maybe open circuit
            self._register_failure()
            return [{"error": "litellm_missing"}]

        attempts = max(1, int(self._config.max_retries) + 1)
        last_error_text: str | None = None
        for i in range(attempts):
            try:
                response = litellm.completion(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=self._config.request_timeout_seconds,
                )

                content = response.choices[0].message["content"] if hasattr(response.choices[0], "message") else response["choices"][0]["message"]["content"]
                try:
                    data = json.loads(content)
                    self._reset_failures()
                    if isinstance(data, dict):
                        return [data]
                    if isinstance(data, list):
                        return data
                except Exception:
                    self._reset_failures()
                    return [{"raw": content}]
            except Exception as e:
                last_error_text = str(e)
                # backoff
                if i < attempts - 1:
                    sleep_s = self._config.retry_backoff_base_seconds * (self._config.retry_backoff_factor ** i)
                    sleep_s += random.uniform(0, 0.05)
                    time.sleep(sleep_s)
                self._register_failure()

        # Open circuit if threshold exceeded
        self._maybe_open_circuit()
        return [{"error": "provider_error", "message": last_error_text or "unknown"}]

    # --- Circuit breaker helpers ---
    def _register_failure(self) -> None:
        self._failures[self._model] = self._failures.get(self._model, 0) + 1

    def _reset_failures(self) -> None:
        self._failures[self._model] = 0

    def _maybe_open_circuit(self) -> None:
        failures = self._failures.get(self._model, 0)
        if failures >= int(self._config.circuit_breaker_failure_threshold):
            self._open_until[self._model] = time.time() + int(self._config.circuit_breaker_open_seconds)


