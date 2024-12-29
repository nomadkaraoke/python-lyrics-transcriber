from abc import ABC, abstractmethod
from typing import Dict, Any
import logging


class BaseTranscriber(ABC):
    """Base class for all transcription services."""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def transcribe(self, audio_filepath: str) -> Dict[str, Any]:
        """
        Transcribe an audio file and return the results in a standardized format.
        
        Args:
            audio_filepath (str): Path to the audio file to transcribe
            
        Returns:
            Dict containing:
                - segments: List of segments with start/end times and word-level data
                - text: Full text transcription
                - metadata: Dict of additional info (confidence, language, etc)
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this transcription service."""
        pass 