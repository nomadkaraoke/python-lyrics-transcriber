from abc import ABC, abstractmethod
from typing import Optional
import logging
from ollama import chat as ollama_chat
import openai


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional provider-specific parameters

        Returns:
            str: The LLM's response
        """
        pass


class OllamaProvider(LLMProvider):
    """Provider for local Ollama models."""

    def __init__(self, model: str, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.model = model

    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            response = ollama_chat(model=self.model, messages=[{"role": "user", "content": prompt}], format="json")
            return response.message.content
        except Exception as e:
            self.logger.error(f"Error generating Ollama response: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (including OpenRouter)."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.model = model
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generating OpenAI response: {e}")
            raise
