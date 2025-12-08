from typing import Optional, Dict, Any
import os
import threading


def setup_langfuse(client_name: str = "agentic-corrector") -> Optional[object]:
    """Initialize Langfuse client if keys are present; return client or None.

    This avoids hard dependency at import time; caller can check for None and
    no-op if observability is not configured.
    """
    secret = os.getenv("LANGFUSE_SECRET_KEY")
    public = os.getenv("LANGFUSE_PUBLIC_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if not (secret and public):
        return None
    try:
        from langfuse import Langfuse  # type: ignore

        client = Langfuse(secret_key=secret, public_key=public, host=host, sdk_integration=client_name)
        return client
    except Exception:
        return None


def record_metrics(client: Optional[object], name: str, metrics: Dict[str, Any]) -> None:
    """Record custom metrics to Langfuse if initialized."""
    if client is None:
        return
    try:
        # Minimal shape to avoid strict coupling; callers can extend
        client.trace(name=name, metadata=metrics)
    except Exception:
        # Swallow observability errors to never impact core flow
        pass
