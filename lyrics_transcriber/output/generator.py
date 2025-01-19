from dataclasses import dataclass
import os
import logging
from typing import List, Optional
import json

from lyrics_transcriber.types import LyricsData
from lyrics_transcriber.correction.corrector import CorrectionResult
from lyrics_transcriber.output.plain_text import PlainTextGenerator
from lyrics_transcriber.output.lyrics_file import LyricsFileGenerator
from lyrics_transcriber.output.subtitles import SubtitlesGenerator
from lyrics_transcriber.output.video import VideoGenerator
from lyrics_transcriber.output.segment_resizer import SegmentResizer
from lyrics_transcriber.output.cdg import CDGGenerator


@dataclass
class OutputGeneratorConfig:
    """Configuration for output generation."""

    output_dir: str
    cache_dir: str
    styles: dict
    video_resolution: str = "360p"
    max_line_length: int = 36

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.output_dir:
            raise ValueError("output_dir must be provided")
        if not self.cache_dir:
            raise ValueError("cache_dir must be provided")


@dataclass
class OutputPaths:
    """Holds paths for generated output files."""

    lrc: Optional[str] = None
    ass: Optional[str] = None
    video: Optional[str] = None
    original_txt: Optional[str] = None
    corrected_txt: Optional[str] = None
    corrections_json: Optional[str] = None
    cdg: Optional[str] = None
    mp3: Optional[str] = None
    cdg_zip: Optional[str] = None


class OutputGenerator:
    """Handles generation of various lyrics output formats."""

    def __init__(
        self,
        config: OutputGeneratorConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize OutputGenerator with configuration.

        Args:
            config: OutputGeneratorConfig instance with required paths
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        self.logger.debug(f"Initializing OutputGenerator with config: {self.config}")

        # Set video resolution parameters
        self.video_resolution_num, self.font_size, self.line_height = self._get_video_params(self.config.video_resolution)

        # Initialize generators
        self.plain_text = PlainTextGenerator(self.config.output_dir, self.logger)
        self.lyrics_file = LyricsFileGenerator(self.config.output_dir, self.logger)
        self.cdg = CDGGenerator(self.config.output_dir, self.logger)
        self.subtitle = SubtitlesGenerator(
            output_dir=self.config.output_dir,
            video_resolution=self.video_resolution_num,
            font_size=self.font_size,
            line_height=self.line_height,
            styles=self.config.styles,
            logger=self.logger,
        )
        self.video = VideoGenerator(
            output_dir=self.config.output_dir,
            cache_dir=self.config.cache_dir,
            video_resolution=self.video_resolution_num,
            styles=self.config.styles,
            logger=self.logger,
        )
        self.segment_resizer = SegmentResizer(max_line_length=self.config.max_line_length, logger=self.logger)

        # Log the configured directories
        self.logger.debug(f"Initialized OutputGenerator with output_dir: {self.config.output_dir}")
        self.logger.debug(f"Using cache_dir: {self.config.cache_dir}")

    def generate_outputs(
        self,
        transcription_corrected: CorrectionResult,
        lyrics_results: List[LyricsData],
        output_prefix: str,
        audio_filepath: str,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        render_video: bool = False,
    ) -> OutputPaths:
        """Generate all requested output formats."""
        outputs = OutputPaths()

        try:
            # Generate plain lyrics files for each provider
            for lyrics_data in lyrics_results:
                self.plain_text.write_lyrics(lyrics_data, output_prefix)

            # Write original (uncorrected) transcription
            outputs.original_txt = self.plain_text.write_original_transcription(transcription_corrected, output_prefix)

            # Resize corrected segments to ensure none are longer than max_line_length
            resized_segments = self.segment_resizer.resize_segments(transcription_corrected.corrected_segments)
            transcription_corrected.resized_segments = resized_segments
            outputs.corrections_json = self.write_corrections_data(transcription_corrected, output_prefix)

            # Write corrected lyrics as plain text
            outputs.corrected_txt = self.plain_text.write_corrected_lyrics(resized_segments, output_prefix)

            # Generate LRC using LyricsFileGenerator
            outputs.lrc = self.lyrics_file.generate_lrc(resized_segments, output_prefix)

            # Generate CDG file using LRC
            outputs.cdg, outputs.mp3, outputs.cdg_zip = self.cdg.generate_cdg(
                segments=resized_segments,
                audio_file=audio_filepath,
                title=title or output_prefix,
                artist=artist or "",
                cdg_styles=self.config.styles["cdg"],
            )

            # Generate ASS subtitles
            outputs.ass = self.subtitle.generate_ass(resized_segments, output_prefix, audio_filepath)

            # Generate video if requested
            if render_video and outputs.ass:
                outputs.video = self.video.generate_video(outputs.ass, audio_filepath, output_prefix)

            return outputs

        except Exception as e:
            self.logger.error(f"Failed to generate outputs: {str(e)}")
            raise

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.config.output_dir or self.config.cache_dir, f"{output_prefix}.{extension}")

    def _get_video_params(self, resolution: str) -> tuple:
        """Get video parameters: (width, height), font_size, line_height based on video resolution config."""
        match resolution:
            case "4k":
                return (3840, 2160), 250, 250
            case "1080p":
                return (1920, 1080), 120, 120
            case "720p":
                return (1280, 720), 100, 100
            case "360p":
                return (640, 360), 40, 50
            case _:
                raise ValueError("Invalid video_resolution value. Must be one of: 4k, 1080p, 720p, 360p")

    def write_corrections_data(self, correction_result: CorrectionResult, output_prefix: str) -> str:
        """Write corrections data to JSON file."""
        self.logger.info("Writing corrections data JSON")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrections)", "json")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(correction_result.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.info(f"Corrections data JSON generated: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to write corrections data JSON: {str(e)}")
            raise
