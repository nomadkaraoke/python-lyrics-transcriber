from dataclasses import dataclass
import os
import logging
from typing import List, Optional
import subprocess
from datetime import timedelta
import json

from lyrics_transcriber.types import LyricsData, LyricsSegment
from lyrics_transcriber.correction.corrector import CorrectionResult
from lyrics_transcriber.output import subtitles


@dataclass
class OutputGeneratorConfig:
    """Configuration for output generation."""

    output_dir: str
    cache_dir: str
    video_resolution: str = "360p"
    video_background_image: Optional[str] = None
    video_background_color: str = "black"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.output_dir:
            raise ValueError("output_dir must be provided")
        if not self.cache_dir:
            raise ValueError("cache_dir must be provided")
        if self.video_background_image and not os.path.isfile(self.video_background_image):
            raise FileNotFoundError(f"Video background image not found: {self.video_background_image}")


@dataclass
class OutputPaths:
    """Holds paths for generated output files."""

    lrc: Optional[str] = None
    ass: Optional[str] = None
    video: Optional[str] = None
    original_txt: Optional[str] = None
    original_segments: Optional[str] = None
    corrected_segments: Optional[str] = None
    corrections: Optional[str] = None
    corrected_txt: Optional[str] = None


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

        # Log the configured directories
        self.logger.debug(f"Initialized OutputGenerator with output_dir: {self.config.output_dir}")
        self.logger.debug(f"Using cache_dir: {self.config.cache_dir}")

        # Set video resolution parameters
        self.video_resolution_num, self.font_size, self.line_height = self._get_video_params(self.config.video_resolution)

    def generate_outputs(
        self,
        transcription_corrected: CorrectionResult,
        lyrics_results: List[LyricsData],
        output_prefix: str,
        audio_filepath: str,
        render_video: bool = False,
    ) -> OutputPaths:
        """Generate all requested output formats."""
        outputs = OutputPaths()

        try:
            # Generate plain lyrics files for each provider
            for lyrics_data in lyrics_results:
                provider_name = lyrics_data.metadata.source.title()
                self.write_plain_lyrics(lyrics_data, f"{output_prefix} (Lyrics {provider_name})")

            if transcription_corrected:
                # Write original (uncorrected) transcription
                outputs.original_txt = self.write_original_transcription(transcription_corrected, output_prefix)
                outputs.corrections = self.write_corrections_data(transcription_corrected, output_prefix)

                # Write corrected lyrics as plain text
                outputs.corrected_txt = self.write_plain_lyrics_from_correction(
                    transcription_corrected, f"{output_prefix} (Lyrics Corrected)"
                )

                # Generate LRC
                outputs.lrc = self.generate_lrc(transcription_corrected, output_prefix)

                # Generate ASS
                outputs.ass = self.generate_ass(transcription_corrected, output_prefix)

                # Generate video if requested
                if render_video:
                    outputs.video = self.generate_video(outputs.ass, audio_filepath, output_prefix)

        except Exception as e:
            self.logger.error(f"Error generating outputs: {str(e)}")
            raise

        return outputs

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.config.output_dir or self.config.cache_dir, f"{output_prefix}.{extension}")

    def generate_lrc(self, transcription_data: CorrectionResult, output_prefix: str) -> str:
        """Generate LRC format lyrics file."""
        self.logger.info("Generating LRC format lyrics")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "lrc")

        try:
            self._write_lrc_file(output_path, transcription_data.corrected_segments)
            self.logger.info(f"LRC file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate LRC file: {str(e)}")
            raise

    def _write_lrc_file(self, output_path: str, segments: List[LyricsSegment]) -> None:
        """Write LRC file content with MidiCo-compatible word-level timestamps.

        Args:
            output_path: Path to write the LRC file
            segments: List of LyricsSegment objects containing word timing data
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write MidiCo header
            f.write("[re:MidiCo]\n")

            for segment in segments:
                for i, word in enumerate(segment.words):
                    start_time = self._format_lrc_timestamp(word.start_time)

                    # Add space after all words except last in segment
                    text = word.text
                    if i != len(segment.words) - 1:
                        text += " "

                    # Add "/" prefix for first word in segment
                    prefix = "/" if i == 0 else ""

                    # Write MidiCo formatted line
                    f.write(f"[{start_time}]1:{prefix}{text}\n")

    def _format_lrc_timestamp(self, seconds: float) -> str:
        """Format timestamp for MidiCo LRC format (MM:SS.mmm)."""
        minutes = int(seconds // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        return f"{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"

    def generate_ass(self, transcription_data: CorrectionResult, output_prefix: str) -> str:
        """Generate ASS format subtitles file."""
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "ass")

        try:
            # Create screens from segments
            initial_screens = self._create_screens(transcription_data.corrected_segments)

            # Get song duration from last segment's end time
            song_duration = int(transcription_data.corrected_segments[-1].end_time)

            # Process screens using subtitles library
            screens = subtitles.set_segment_end_times(initial_screens, song_duration)
            screens = subtitles.set_screen_start_times(screens)

            # Generate ASS file using subtitles library
            lyric_subtitles_ass = subtitles.create_styled_subtitles(screens, self.video_resolution_num, self.font_size)
            lyric_subtitles_ass.write(output_path)

            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}")
            raise

    def _create_screens(self, segments: List[LyricsSegment]) -> List[subtitles.LyricsScreen]:
        """Create LyricsScreen objects from segments.

        Args:
            segments: List of LyricsSegment objects containing lyrics and timing data
        """
        self.logger.debug("Creating screens from segments")
        screens: List[subtitles.LyricsScreen] = []
        screen: Optional[subtitles.LyricsScreen] = None

        max_lines_per_screen = 4
        max_line_length = 36

        for segment in segments:
            # Create new screen if needed
            if screen is None or len(screen.lines) >= max_lines_per_screen:
                screen = subtitles.LyricsScreen(video_size=self.video_resolution_num, line_height=self.line_height, logger=self.logger)
                screens.append(screen)
                self.logger.debug(f"Created new screen. Total screens: {len(screens)}")

            # Create line from segment
            line = subtitles.LyricsLine()
            lyric_segment = subtitles.LyricSegment(
                text=segment.text, ts=timedelta(seconds=segment.start_time), end_ts=timedelta(seconds=segment.end_time)
            )
            line.segments.append(lyric_segment)
            screen.lines.append(line)

        return screens

    def generate_video(self, ass_path: str, audio_path: str, output_prefix: str) -> str:
        """Generate MP4 video with lyrics overlay."""
        self.logger.info("Generating video with lyrics overlay")
        output_path = self._get_output_path(output_prefix, "mkv")

        try:
            cmd = self._build_ffmpeg_command(ass_path, audio_path, output_path)
            self._run_ffmpeg_command(cmd)
            self.logger.info(f"Video generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate video: {str(e)}")
            raise

    def _build_ffmpeg_command(self, ass_path: str, audio_path: str, output_path: str) -> list:
        """Build FFmpeg command for video generation with optimized settings."""
        width, height = self.video_resolution_num

        # fmt: off
        cmd = [
            "ffmpeg",
            "-r", "30",  # Set frame rate to 30 fps
        ]

        # Input source (background)
        if self.config.video_background_image:
            self.logger.debug(
                f"Using background image: {self.config.video_background_image}, "
                f"with resolution: {width}x{height}"
            )
            cmd.extend([
                "-loop", "1",  # Loop the image
                "-i", self.config.video_background_image,
            ])
        else:
            self.logger.debug(
                f"Using solid {self.config.video_background_color} background "
                f"with resolution: {width}x{height}"
            )
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c={self.config.video_background_color}:s={width}x{height}:r=30"
            ])

        # Check for hardware acceleration support
        video_codec = self._get_video_codec()
        
        # Add audio input and subtitle overlay
        cmd.extend([
            "-i", audio_path,
            "-c:a", "flac",  # Re-encode audio as FLAC
            "-vf", f"ass={ass_path}",  # Add subtitles
            "-c:v", video_codec,
            # Video quality settings
            "-preset", "slow",  # Better compression efficiency
            "-b:v", "5000k",  # Base video bitrate
            "-minrate", "5000k",  # Minimum bitrate
            "-maxrate", "20000k",  # Maximum bitrate
            "-bufsize", "10000k",  # Buffer size (2x base rate)
            "-shortest",  # End encoding after shortest stream
            "-y",  # Overwrite output without asking
        ])
        # fmt: on

        # Add output path
        cmd.append(output_path)

        return cmd

    def _get_video_codec(self) -> str:
        """Determine the best available video codec."""
        try:
            ffmpeg_codes = subprocess.getoutput("ffmpeg -codecs")
            if "h264_videotoolbox" in ffmpeg_codes:
                self.logger.info("Using hardware accelerated h264_videotoolbox")
                return "h264_videotoolbox"
        except Exception as e:
            self.logger.warning(f"Error checking for hardware acceleration: {e}")

        return "libx264"

    def _run_ffmpeg_command(self, cmd: list) -> None:
        """Execute FFmpeg command with output handling."""
        self.logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        try:
            # Use check_output to capture the output
            output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)  # Redirect stderr to stdout
            self.logger.debug(f"FFmpeg output: {output}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {e.output}")
            raise

    def _get_video_params(self, resolution: str) -> tuple:
        """Get video parameters based on resolution setting."""
        match resolution:
            case "4k":
                return (3840, 2160), 250, 250
            case "1080p":
                return (1920, 1080), 120, 120
            case "720p":
                return (1280, 720), 100, 100
            case "360p":
                return (640, 360), 50, 50
            case _:
                raise ValueError("Invalid video_resolution value. Must be one of: 4k, 1080p, 720p, 360p")

    def write_plain_lyrics(self, lyrics_data: LyricsData, output_prefix: str) -> str:
        """Write plain text lyrics file."""
        self.logger.info("Writing plain lyrics file")
        output_path = self._get_output_path(output_prefix, "txt")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(lyrics_data.lyrics)
            self.logger.info(f"Plain lyrics file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to write plain lyrics file: {str(e)}")
            raise

    def write_plain_lyrics_from_correction(self, correction_result: CorrectionResult, output_prefix: str) -> str:
        """Write corrected lyrics as plain text file."""
        self.logger.info("Writing corrected lyrics file")
        output_path = self._get_output_path(output_prefix, "txt")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(correction_result.corrected_text)
            self.logger.info(f"Corrected lyrics file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to write corrected lyrics file: {str(e)}")
            raise

    def write_original_transcription(self, correction_result: CorrectionResult, output_prefix: str) -> str:
        """Write original (uncorrected) transcription as plain text."""
        self.logger.info("Writing original transcription file")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Uncorrected)", "txt")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(correction_result.transcribed_text)
            self.logger.info(f"Original transcription file generated: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to write original transcription file: {str(e)}")
            raise

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
