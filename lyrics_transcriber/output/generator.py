import os
import logging
from typing import Dict, Any, Optional
import subprocess
from datetime import timedelta
from .subtitles import create_styled_subtitles, LyricsScreen, LyricsLine, LyricSegment


class OutputGenerator:
    """Handles generation of various lyrics output formats."""

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        output_dir: Optional[str] = None,
        cache_dir: str = "/tmp/lyrics-transcriber-cache/",
        video_resolution: str = "360p",
        video_background_image: Optional[str] = None,
        video_background_color: str = "black",
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.output_dir = output_dir
        self.cache_dir = cache_dir

        # Video settings
        self.video_resolution = video_resolution
        self.video_background_image = video_background_image
        self.video_background_color = video_background_color

        # Set video resolution parameters
        self.video_resolution_num, self.font_size, self.line_height = self._get_video_params(video_resolution)

        # Validate video background if provided
        if self.video_background_image and not os.path.isfile(self.video_background_image):
            raise FileNotFoundError(f"Video background image not found: {self.video_background_image}")

    def generate_outputs(
        self, transcription_data: Dict[str, Any], output_prefix: str, audio_filepath: str, render_video: bool = False
    ) -> Dict[str, str]:
        """
        Generate all requested output formats.

        Args:
            transcription_data: Dictionary containing transcription segments with timing
            output_prefix: Prefix for output filenames
            audio_filepath: Path to the source audio file
            render_video: Whether to generate video output

        Returns:
            Dictionary of output paths for each format
        """
        outputs = {}

        try:
            # Generate LRC
            lrc_path = self.generate_lrc(transcription_data, output_prefix)
            outputs["lrc"] = lrc_path

            # Generate ASS
            ass_path = self.generate_ass(transcription_data, output_prefix)
            outputs["ass"] = ass_path

            # Generate video if requested
            if render_video:
                video_path = self.generate_video(ass_path, audio_filepath, output_prefix)
                outputs["video"] = video_path

        except Exception as e:
            self.logger.error(f"Error generating outputs: {str(e)}")
            raise

        return outputs

    def generate_lrc(self, transcription_data: Dict[str, Any], output_prefix: str) -> str:
        """Generate LRC format lyrics file."""
        self.logger.info("Generating LRC format lyrics")

        output_path = os.path.join(self.output_dir or self.cache_dir, f"{output_prefix}.lrc")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in transcription_data["segments"]:
                    start_time = self._format_lrc_timestamp(segment["start"])
                    line = f"[{start_time}]{segment['text']}\n"
                    f.write(line)

            self.logger.info(f"LRC file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate LRC file: {str(e)}")
            raise

    def generate_ass(self, transcription_data: Dict[str, Any], output_prefix: str) -> str:
        """Generate ASS format subtitles file."""
        self.logger.info("Generating ASS format subtitles")

        output_path = os.path.join(self.output_dir or self.cache_dir, f"{output_prefix}.ass")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Write ASS header
                f.write(self._get_ass_header())

                # Write events
                for segment in transcription_data["segments"]:
                    start_time = self._format_ass_timestamp(segment["start"])
                    end_time = self._format_ass_timestamp(segment["end"])
                    line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{segment['text']}\n"
                    f.write(line)

            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}")
            raise

    def generate_video(self, ass_path: str, audio_path: str, output_prefix: str) -> str:
        """Generate MP4 video with lyrics overlay."""
        self.logger.info("Generating video with lyrics overlay")

        output_path = os.path.join(self.output_dir or self.cache_dir, f"{output_prefix}.mp4")
        width, height = self.video_resolution_num

        try:
            # Prepare FFmpeg command
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={self.video_background_color}:s={width}x{height}",
                "-i",
                audio_path,
                "-vf",
                f"ass={ass_path}",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-shortest",
                output_path,
            ]

            # If background image provided, use it instead of solid color
            if self.video_background_image:
                cmd[3:6] = ["-i", self.video_background_image]

            self.logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

            self.logger.info(f"Video generated: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to generate video: {str(e)}")
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
