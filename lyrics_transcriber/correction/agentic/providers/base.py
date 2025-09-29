from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseAIProvider(ABC):
    """Abstract provider interface for generating correction proposals.

    Implementations should honor timeouts and retry policies according to
    ProviderConfig and return structured proposals validated upstream.
    """

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_correction_proposals(self, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return a list of correction proposals as dictionaries matching `schema`.

        The schema is provided so implementations can guide structured outputs.
        """
        raise NotImplementedError


