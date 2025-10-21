"""Factory for creating LangChain ChatModels with Langfuse callbacks."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional, List

from .config import ProviderConfig

logger = logging.getLogger(__name__)


class ModelFactory:
    """Creates and configures LangChain ChatModels with observability.
    
    This factory handles:
    - Parsing model specifications ("provider/model" format)
    - Creating Langfuse callbacks when configured
    - Instantiating the appropriate ChatModel for each provider
    
    Single Responsibility: Model creation only, no execution or state management.
    """
    
    def __init__(self):
        self._langfuse_handler: Optional[Any] = None
        self._langfuse_initialized = False
    
    def create_chat_model(self, model_spec: str, config: ProviderConfig) -> Any:
        """Create a ChatModel from a model specification.
        
        Args:
            model_spec: Model identifier in format "provider/model" 
                       e.g. "ollama/gpt-oss:latest", "openai/gpt-4"
            config: Provider configuration with timeouts, retries, etc.
            
        Returns:
            Configured LangChain ChatModel instance
            
        Raises:
            ValueError: If model_spec format is invalid or provider unsupported
        """
        provider, model_name = self._parse_model_spec(model_spec)
        callbacks = self._create_callbacks(model_spec)
        return self._instantiate_model(provider, model_name, callbacks, config)
    
    def _parse_model_spec(self, spec: str) -> tuple[str, str]:
        """Parse model specification into provider and model name.
        
        Args:
            spec: Model spec in format "provider/model"
            
        Returns:
            Tuple of (provider, model_name)
            
        Raises:
            ValueError: If format is invalid
        """
        parts = spec.split("/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Model spec must be in format 'provider/model', got: {spec}"
            )
        return parts[0], parts[1]
    
    def _create_callbacks(self, model_spec: str) -> List[Any]:
        """Create Langfuse callback handlers if configured.
        
        Args:
            model_spec: Model specification for logging
            
        Returns:
            List of callback handlers (may be empty)
        """
        # Only initialize Langfuse once
        if not self._langfuse_initialized:
            self._initialize_langfuse(model_spec)
            self._langfuse_initialized = True
        
        return [self._langfuse_handler] if self._langfuse_handler else []
    
    def _initialize_langfuse(self, model_spec: str) -> None:
        """Initialize Langfuse callback handler if keys are present.
        
        Langfuse reads credentials from environment variables automatically:
        - LANGFUSE_PUBLIC_KEY
        - LANGFUSE_SECRET_KEY  
        - LANGFUSE_HOST (optional)
        
        Args:
            model_spec: Model specification for logging
            
        Raises:
            RuntimeError: If Langfuse keys are set but initialization fails
        """
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if not (public_key and secret_key):
            logger.debug("🤖 Langfuse keys not found, tracing disabled")
            return
        
        try:
            from langfuse import Langfuse
            from langfuse.langchain import CallbackHandler
            
            # Initialize Langfuse client first (this is required!)
            langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            
            # Then create callback handler with the same public_key
            # The handler will use the initialized client
            self._langfuse_handler = CallbackHandler(public_key=public_key)
            logger.info(f"🤖 Langfuse callback handler initialized for {model_spec}")
        except Exception as e:
            # If Langfuse keys are set, we MUST fail fast
            raise RuntimeError(
                f"Langfuse keys are set but initialization failed: {e}\n"
                f"This indicates a configuration or dependency problem.\n"
                f"Check:\n"
                f"  - LANGFUSE_PUBLIC_KEY: {public_key[:10]}...\n"
                f"  - LANGFUSE_SECRET_KEY: {'set' if secret_key else 'not set'}\n"
                f"  - LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'default')}\n"
                f"  - langfuse package version: pip show langfuse"
            ) from e
    
    def _instantiate_model(
        self, 
        provider: str, 
        model_name: str, 
        callbacks: List[Any], 
        config: ProviderConfig
    ) -> Any:
        """Instantiate the appropriate ChatModel for the provider.
        
        Args:
            provider: Provider name (ollama, openai, anthropic)
            model_name: Model name within that provider
            callbacks: List of callback handlers
            config: Provider configuration
            
        Returns:
            Configured ChatModel instance
            
        Raises:
            ValueError: If provider is not supported
            ImportError: If provider package is not installed
        """
        try:
            if provider == "ollama":
                return self._create_ollama_model(model_name, callbacks, config)
            elif provider == "openai":
                return self._create_openai_model(model_name, callbacks, config)
            elif provider == "anthropic":
                return self._create_anthropic_model(model_name, callbacks, config)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except ImportError as e:
            raise ImportError(
                f"Failed to import {provider} provider. "
                f"Install with: pip install langchain-{provider}"
            ) from e
    
    def _create_ollama_model(
        self, model_name: str, callbacks: List[Any], config: ProviderConfig
    ) -> Any:
        """Create ChatOllama model."""
        from langchain_ollama import ChatOllama
        
        model = ChatOllama(
            model=model_name,
            timeout=config.request_timeout_seconds,
            callbacks=callbacks,
        )
        logger.debug(f"🤖 Created Ollama model: {model_name}")
        return model
    
    def _create_openai_model(
        self, model_name: str, callbacks: List[Any], config: ProviderConfig
    ) -> Any:
        """Create ChatOpenAI model."""
        from langchain_openai import ChatOpenAI
        
        model = ChatOpenAI(
            model=model_name,
            timeout=config.request_timeout_seconds,
            max_retries=config.max_retries,
            callbacks=callbacks,
        )
        logger.debug(f"🤖 Created OpenAI model: {model_name}")
        return model
    
    def _create_anthropic_model(
        self, model_name: str, callbacks: List[Any], config: ProviderConfig
    ) -> Any:
        """Create ChatAnthropic model."""
        from langchain_anthropic import ChatAnthropic
        
        model = ChatAnthropic(
            model=model_name,
            timeout=config.request_timeout_seconds,
            max_retries=config.max_retries,
            callbacks=callbacks,
        )
        logger.debug(f"🤖 Created Anthropic model: {model_name}")
        return model

