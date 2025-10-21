from __future__ import annotations

import logging
import os
from typing import Dict, Any, List, Optional

from .providers.base import BaseAIProvider
from .providers.langchain_bridge import LangChainBridge
from .providers.config import ProviderConfig
from .models.schemas import CorrectionProposal
from .workflows.correction_graph import build_correction_graph

logger = logging.getLogger(__name__)


class AgenticCorrector:
    """Main entry for agentic AI correction using LangChain + LangGraph.

    This orchestrates correction workflows using LangGraph for state management
    and LangChain ChatModels for provider integration. Langfuse tracing is
    automatic via LangChain callbacks.
    
    Uses dependency injection for better testability - you can inject a
    mock provider for testing.
    """

    def __init__(
        self, 
        provider: BaseAIProvider,
        graph: Optional[Any] = None,
        langfuse_handler: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        """Initialize with injected dependencies.
        
        Args:
            provider: AI provider implementation (e.g., LangChainBridge)
            graph: Optional LangGraph workflow (builds default if None)
            langfuse_handler: Optional Langfuse callback handler (if None, will try to get from provider)
            session_id: Optional Langfuse session ID to group related traces
        """
        self._provider = provider
        self._session_id = session_id
        
        # Get Langfuse handler from provider if available (avoids duplication)
        self._langfuse_handler = langfuse_handler or self._get_provider_handler()
        
        # Build graph with Langfuse callback if available
        self._graph = graph if graph is not None else build_correction_graph(
            callbacks=[self._langfuse_handler] if self._langfuse_handler else None
        )
    
    def _get_provider_handler(self) -> Optional[Any]:
        """Get Langfuse handler from provider if it has one.
        
        This avoids duplicating Langfuse initialization - if the provider
        (e.g., LangChainBridge) already has a handler, we reuse it.
        
        Returns:
            CallbackHandler instance from provider, or None
        """
        # Check if provider is LangChainBridge and has a factory
        if hasattr(self._provider, '_factory'):
            factory = self._provider._factory
            
            # Force initialization of Langfuse if keys are present
            # This ensures the handler is available when we need it
            if hasattr(factory, '_langfuse_initialized'):
                if not factory._langfuse_initialized:
                    # Initialize by calling _create_callbacks (which triggers _initialize_langfuse)
                    factory._create_callbacks(self._provider._model)
            
            # Now check if handler is available
            if hasattr(factory, '_langfuse_handler'):
                handler = factory._langfuse_handler
                if handler:
                    logger.debug("🤖 Reusing Langfuse handler from ModelFactory")
                    return handler
        
        logger.debug("🤖 No Langfuse handler from provider")
        return None
    
    @classmethod
    def from_model(
        cls, 
        model: str, 
        config: ProviderConfig | None = None,
        session_id: Optional[str] = None
    ) -> "AgenticCorrector":
        """Factory method to create corrector from model specification.
        
        This is a convenience method for the common case where you want
        to use LangChainBridge with a model spec string.
        
        Args:
            model: Model identifier in format "provider/model"
            config: Optional provider configuration
            session_id: Optional Langfuse session ID to group related traces
            
        Returns:
            AgenticCorrector instance with LangChainBridge provider
        """
        config = config or ProviderConfig.from_env()
        provider = LangChainBridge(model=model, config=config)
        return cls(provider=provider, session_id=session_id)

    def propose(self, prompt: str) -> List[CorrectionProposal]:
        """Generate correction proposals using LangGraph + LangChain.
        
        Args:
            prompt: The correction prompt with gap text and reference context
            
        Returns:
            List of validated CorrectionProposal objects
        """
        # Prepare config with session_id in metadata (Langfuse format)
        config = {}
        if self._langfuse_handler:
            config["callbacks"] = [self._langfuse_handler]
            if self._session_id:
                config["metadata"] = {"langfuse_session_id": self._session_id}
                logger.debug(f"🤖 Set Langfuse session_id in metadata: {self._session_id}")
        
        # Run LangGraph workflow (with Langfuse tracing if configured)
        if self._graph:
            try:
                self._graph.invoke(
                    {"prompt": prompt, "proposals": []},
                    config=config
                )
            except Exception as e:
                logger.debug(f"🤖 LangGraph workflow invocation failed: {e}")

        # Get proposals from LangChain ChatModel
        # Pass the session_id via metadata to the provider
        data = self._provider.generate_correction_proposals(
            prompt, 
            schema=CorrectionProposal.model_json_schema(),
            session_id=self._session_id
        )
        
        # Validate via Pydantic; invalid entries are dropped
        proposals: List[CorrectionProposal] = []
        for item in data:
            # Check if this is an error response from the provider
            if isinstance(item, dict) and "error" in item:
                logger.warning(f"🤖 Provider returned error: {item}")
                continue
            
            try:
                proposals.append(CorrectionProposal.model_validate(item))
            except Exception as e:
                # Log validation errors for debugging
                logger.debug(f"🤖 Failed to validate proposal: {e}, item: {item}")
                continue
                
        return proposals


