from pathlib import Path
from typing import Optional, Dict, Any
from .base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig
from lyrics_transcriber.types import LyricsData
from karaoke_lyrics_processor import KaraokeLyricsProcessor


class FileProvider(BaseLyricsProvider):
    """Provider that loads lyrics from a local file."""

    def _fetch_data_from_source(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Load lyrics from the specified file."""
        if not self.config.lyrics_file:
            return None

        lyrics_file = Path(self.config.lyrics_file)
        if not lyrics_file.exists():
            self.logger.error(f"Lyrics file not found: {lyrics_file}")
            return None

        processor = KaraokeLyricsProcessor(
            log_level=self.logger.getEffectiveLevel(),
            log_formatter=self.logger.handlers[0].formatter if self.logger.handlers else None,
            input_filename=str(lyrics_file),
            max_line_length=self.max_line_length,
        )

        processed_text = processor.process()

        return {"text": processed_text, "source": "file", "filepath": str(lyrics_file)}

    def _convert_result_format(self, raw_data: Dict[str, Any]) -> LyricsData:
        """Convert the raw file data to LyricsData format."""
        return LyricsData(
            source="file",
            lyrics=raw_data["text"],
            segments=[],  # No timing information from file
            metadata={"filepath": raw_data["filepath"]},
        )
