from dataclasses import dataclass
from typing import Optional
import os


@dataclass(frozen=True)
class ProviderConfig:
    """Centralized configuration for AI providers.

    Values are loaded from environment variables to keep credentials out of code.
    This module is safe to import during setup; it does not perform any network I/O.
    """

    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    google_api_key: Optional[str]
    openrouter_api_key: Optional[str]
    privacy_mode: bool

    request_timeout_seconds: float = 4.0
    max_retries: int = 2
    retry_backoff_base_seconds: float = 0.2
    retry_backoff_factor: float = 2.0
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_open_seconds: int = 60

    @staticmethod
    def from_env() -> "ProviderConfig":
        return ProviderConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            privacy_mode=os.getenv("PRIVACY_MODE", "false").lower() in {"1", "true", "yes"},
        )

    def validate_environment(self, logger: Optional[object] = None) -> None:
        """Log warnings if required keys are missing for non-privacy mode."""
        def _log(msg: str) -> None:
            try:
                if logger is not None:
                    logger.warning(msg)
                else:
                    print(msg)
            except Exception:
                pass

        if self.privacy_mode:
            return
        if not any([self.openai_api_key, self.anthropic_api_key, self.google_api_key, self.openrouter_api_key]):
            _log("No AI provider API keys configured; set PRIVACY_MODE=1 to avoid cloud usage or add provider keys.")


