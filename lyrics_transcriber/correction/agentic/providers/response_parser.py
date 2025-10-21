"""Parser for LLM responses into structured correction proposals."""
from __future__ import annotations

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parses LLM responses into structured proposal dictionaries.
    
    Handles both JSON and raw text responses, providing consistent
    output format for downstream processing.
    
    Single Responsibility: Response parsing only, no model invocation.
    """
    
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse response content into proposal dictionaries.
        
        Attempts to parse as JSON first. If that fails, returns the
        raw content wrapped in a dict for logging/debugging.
        
        Args:
            content: Raw response content from LLM
            
        Returns:
            List of proposal dictionaries. On parse failure, returns
            [{"raw": content}] to preserve the response.
        """
        # Try JSON parsing first
        try:
            data = json.loads(content)
            return self._normalize_json_response(data)
        except json.JSONDecodeError as e:
            logger.debug(f"🤖 Response is not valid JSON: {e}")
            return self._handle_raw_response(content)
    
    def _normalize_json_response(self, data: Any) -> List[Dict[str, Any]]:
        """Normalize JSON data into a list of dictionaries.
        
        Handles both single dict and list of dicts responses.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            List of dictionaries
        """
        if isinstance(data, dict):
            # Single proposal - wrap in list
            return [data]
        elif isinstance(data, list):
            # Already a list - return as-is
            return data
        else:
            # Unexpected type - wrap in error dict
            logger.warning(f"🤖 Unexpected JSON type: {type(data)}")
            return [{"error": "unexpected_type", "data": str(data)}]
    
    def _handle_raw_response(self, content: str) -> List[Dict[str, Any]]:
        """Handle non-JSON responses.
        
        Wraps raw content in a dict for downstream handling.
        The "raw" key indicates this needs manual processing.
        
        Args:
            content: Raw response text
            
        Returns:
            List with single dict containing raw content
        """
        logger.info(
            f"🤖 Returning raw response (non-JSON): "
            f"{content[:100]}{'...' if len(content) > 100 else ''}"
        )
        return [{"raw": content}]

