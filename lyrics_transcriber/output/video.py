import logging
import os
import json
import subprocess
from typing import List, Optional, Tuple


class VideoGenerator:
    """Handles generation of video files with lyrics overlay."""

    def __init__(
        self,
        output_dir: str,
        cache_dir: str,
        video_resolution: Tuple[int, int],
        background_image: Optional[str] = None,
        background_color: str = "black",
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize VideoGenerator.

        Args:
            output_dir: Directory where output files will be written
            cache_dir: Directory for temporary files
            video_resolution: Tuple of (width, height) for video resolution
            background_image: Optional path to background image
            background_color: Color to use when no background image (default: "black")
            logger: Optional logger instance
        """
        if not all(x > 0 for x in video_resolution):
            raise ValueError("Video resolution dimensions must be greater than 0")
        
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        self.video_resolution = video_resolution
        self.background_image = background_image
        self.background_color = background_color
        self.logger = logger or logging.getLogger(__name__)

        if background_image and not os.path.isfile(background_image):
            raise FileNotFoundError(f"Video background image not found: {background_image}")

    def generate_video(self, ass_path: str, audio_path: str, output_prefix: str) -> str:
        """Generate MP4 video with lyrics overlay.

        Args:
            ass_path: Path to ASS subtitles file
            audio_path: Path to audio file
            output_prefix: Prefix for output filename

        Returns:
            Path to generated video file
        """
        self.logger.info("Generating video with lyrics overlay")
        output_path = self._get_output_path(f"{output_prefix} (With Vocals)", "mkv")

        # Check input files exist before running FFmpeg
        if not os.path.isfile(ass_path):
            raise FileNotFoundError(f"Subtitles file not found: {ass_path}")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            cmd = self._build_ffmpeg_command(ass_path, audio_path, output_path)
            self._run_ffmpeg_command(cmd)
            self.logger.info(f"Video generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate video: {str(e)}")
            raise

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.output_dir, f"{output_prefix}.{extension}")

    def _resize_background_image(self, input_path: str) -> str:
        """Resize background image to match target resolution and save to temp file."""
        target_width, target_height = self.video_resolution

        # Get current image dimensions using ffprobe
        try:
            probe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                input_path,
            ]
            probe_output = subprocess.check_output(probe_cmd, universal_newlines=True)
            probe_data = json.loads(probe_output)
            current_width = probe_data["streams"][0]["width"]
            current_height = probe_data["streams"][0]["height"]

            # If dimensions already match, return original path
            if current_width == target_width and current_height == target_height:
                self.logger.debug("Background image already at target resolution")
                return input_path

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to get image dimensions: {e}")
            # Continue with resize attempt if probe fails

        temp_path = os.path.join(self.cache_dir, "resized_background.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
            temp_path,
        ]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return temp_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to resize background image: {e.output}")
            raise

    def _build_ffmpeg_command(self, ass_path: str, audio_path: str, output_path: str) -> List[str]:
        """Build FFmpeg command for video generation with optimized settings."""
        width, height = self.video_resolution

        # fmt: off
        cmd = [
            "ffmpeg",
            "-r", "30",  # Set frame rate to 30 fps
        ]

        # Input source (background)
        if self.background_image:
            # Resize background image first
            resized_bg = self._resize_background_image(self.background_image)
            self.logger.debug(f"Using resized background image: {resized_bg}")
            cmd.extend([
                "-loop", "1",  # Loop the image
                "-i", resized_bg,
            ])
        else:
            self.logger.debug(
                f"Using solid {self.background_color} background "
                f"with resolution: {width}x{height}"
            )
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c={self.background_color}:s={width}x{height}:r=30"
            ])

        # Add audio input and subtitle overlay
        cmd.extend([
            "-i", audio_path,
            "-c:a", "flac",  # Re-encode audio as FLAC
            "-vf", f"ass={ass_path}",  # Add subtitles
            "-c:v", self._get_video_codec(),
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

    def _run_ffmpeg_command(self, cmd: List[str]) -> None:
        """Execute FFmpeg command with output handling."""
        self.logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        try:
            output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)
            self.logger.debug(f"FFmpeg output: {output}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {e.output}")
            raise