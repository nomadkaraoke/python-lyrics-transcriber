from dataclasses import dataclass
import os
import logging
from typing import Dict, Any, Optional, Tuple
import subprocess
from datetime import timedelta
from .subtitles import create_styled_subtitles, LyricsScreen, LyricsLine, LyricSegment


@dataclass
class OutputGeneratorConfig:
    """Configuration for output generation."""

    output_dir: Optional[str] = None
    cache_dir: str = "/tmp/lyrics-transcriber-cache/"
    video_resolution: str = "360p"
    video_background_image: Optional[str] = None
    video_background_color: str = "black"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.video_background_image and not os.path.isfile(self.video_background_image):
            raise FileNotFoundError(f"Video background image not found: {self.video_background_image}")


@dataclass
class OutputPaths:
    """Holds paths for generated output files."""

    lrc: Optional[str] = None
    ass: Optional[str] = None
    video: Optional[str] = None


class OutputGenerator:
    """Handles generation of various lyrics output formats."""

    def __init__(
        self,
        config: Optional[OutputGeneratorConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or OutputGeneratorConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Set video resolution parameters
        self.video_resolution_num, self.font_size, self.line_height = self._get_video_params(self.config.video_resolution)

    def generate_outputs(
        self, transcription_data: Dict[str, Any], output_prefix: str, audio_filepath: str, render_video: bool = False
    ) -> OutputPaths:
        """Generate all requested output formats."""
        outputs = OutputPaths()

        try:
            # Generate LRC
            outputs.lrc = self.generate_lrc(transcription_data, output_prefix)

            # Generate ASS
            outputs.ass = self.generate_ass(transcription_data, output_prefix)

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

    def generate_lrc(self, transcription_data: Dict[str, Any], output_prefix: str) -> str:
        """Generate LRC format lyrics file."""
        self.logger.info("Generating LRC format lyrics")
        output_path = self._get_output_path(output_prefix, "lrc")

        try:
            self._write_lrc_file(output_path, transcription_data["segments"])
            self.logger.info(f"LRC file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate LRC file: {str(e)}")
            raise

    def _write_lrc_file(self, output_path: str, segments: list) -> None:
        """Write LRC file content."""
        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                start_time = self._format_lrc_timestamp(segment["start"])
                line = f"[{start_time}]{segment['text']}\n"
                f.write(line)

    def generate_ass(self, transcription_data: Dict[str, Any], output_prefix: str) -> str:
        """Generate ASS format subtitles file."""
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(output_prefix, "ass")

        try:
            self._write_ass_file(output_path, transcription_data["segments"])
            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}")
            raise

    def _write_ass_file(self, output_path: str, segments: list) -> None:
        """Write ASS file content."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self._get_ass_header())
            for segment in segments:
                start_time = self._format_ass_timestamp(segment["start"])
                end_time = self._format_ass_timestamp(segment["end"])
                line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{segment['text']}\n"
                f.write(line)

    def generate_video(self, ass_path: str, audio_path: str, output_prefix: str) -> str:
        """Generate MP4 video with lyrics overlay."""
        self.logger.info("Generating video with lyrics overlay")
        output_path = self._get_output_path(output_prefix, "mp4")

        try:
            cmd = self._build_ffmpeg_command(ass_path, audio_path, output_path)
            self._run_ffmpeg_command(cmd)
            self.logger.info(f"Video generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate video: {str(e)}")
            raise

    def _build_ffmpeg_command(self, ass_path: str, audio_path: str, output_path: str) -> list:
        """Build FFmpeg command for video generation."""
        width, height = self.video_resolution_num
        cmd = ["ffmpeg", "-y"]

        # Input source (background)
        if self.config.video_background_image:
            cmd.extend(["-i", self.config.video_background_image])
        else:
            cmd.extend(["-f", "lavfi", "-i", f"color=c={self.config.video_background_color}:s={width}x{height}"])

        # Add audio and subtitle inputs
        cmd.extend(["-i", audio_path, "-vf", f"ass={ass_path}", "-c:v", "libx264", "-c:a", "aac", "-shortest", output_path])

        return cmd

    def _run_ffmpeg_command(self, cmd: list) -> None:
        """Execute FFmpeg command."""
        self.logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {str(e)}")
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

    def _format_lrc_timestamp(self, seconds: float) -> str:
        """Format timestamp for LRC format."""
        time = timedelta(seconds=seconds)
        minutes = int(time.total_seconds() / 60)
        seconds = time.total_seconds() % 60
        return f"{minutes:02d}:{seconds:05.2f}"

    def _format_ass_timestamp(self, seconds: float) -> str:
        """Format timestamp for ASS format."""
        time = timedelta(seconds=seconds)
        hours = int(time.total_seconds() / 3600)
        minutes = int((time.total_seconds() % 3600) / 60)
        seconds = time.total_seconds() % 60
        centiseconds = int((seconds % 1) * 100)
        seconds = int(seconds)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _get_ass_header(self) -> str:
        """Get ASS format header with style definitions."""
        width, height = self.video_resolution_num
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{self.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
