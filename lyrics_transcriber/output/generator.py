from dataclasses import dataclass
import os
import logging
import re
from typing import List, Optional
import subprocess
from datetime import timedelta
import json

from lyrics_transcriber.types import LyricsData, LyricsSegment, Word
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
    max_line_length: int = 36

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
    corrected_txt: Optional[str] = None
    corrections_json: Optional[str] = None


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
                self.write_plain_lyrics(lyrics_data, output_prefix)

            # Write original (uncorrected) transcription
            outputs.original_txt = self.write_original_transcription(transcription_corrected, output_prefix)

            # Resize corrected segments to ensure none are longer than max_line_length
            resized_segments = self._resize_segments(transcription_corrected.corrected_segments)
            transcription_corrected.resized_segments = resized_segments
            outputs.corrections_json = self.write_corrections_data(transcription_corrected, output_prefix)

            # Write corrected lyrics as plain text
            outputs.corrected_txt = self.write_plain_lyrics_from_correction(resized_segments, output_prefix)

            # Generate LRC
            outputs.lrc = self.generate_lrc(resized_segments, output_prefix)

            # Generate ASS
            outputs.ass = self.generate_ass(resized_segments, output_prefix)

            # Generate video if requested
            if render_video and outputs.ass:
                outputs.video = self.generate_video(outputs.ass, audio_filepath, output_prefix)

            return outputs

        except Exception as e:
            self.logger.error(f"Failed to generate outputs: {str(e)}")
            raise

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.config.output_dir or self.config.cache_dir, f"{output_prefix}.{extension}")

    def process(self):
        self.logger.info(f"Processing input lyrics from {self.input_filename}")

        lyrics_lines = self.input_lyrics_lines
        processed_lyrics_text = ""
        iteration_count = 0
        max_iterations = 100  # Failsafe limit

        all_processed = False
        while not all_processed:
            if iteration_count > max_iterations:
                self.logger.error("Maximum iterations exceeded while processing lyrics.")
                break

            all_processed = True
            new_lyrics = []
            for line in lyrics_lines:
                line = line.strip()
                processed = self.process_line(line)
                new_lyrics.extend(processed)
                if any(len(l) > self.max_line_length for l in processed):
                    all_processed = False

            lyrics_lines = new_lyrics

            iteration_count += 1

        processed_lyrics_text = "\n".join(lyrics_lines)

        self.processed_lyrics_text = processed_lyrics_text

    def process_line(self, line):
        """
        Process a single line to ensure it's within the maximum length,
        handle parentheses, and replace non-printable spaces.
        """
        processed_lines = []
        iteration_count = 0
        max_iterations = 100  # Failsafe limit

        while len(line) > self.max_line_length and iteration_count < max_iterations:
            # Check if the line contains parentheses
            if "(" in line and ")" in line:
                start_paren = line.find("(")
                end_paren = self.find_matching_paren(line, start_paren)
                if end_paren < len(line) and line[end_paren] == ",":
                    end_paren += 1

                # Process text before parentheses if it exists
                if start_paren > 0:
                    before_paren = line[:start_paren].strip()
                    processed_lines.extend(self.split_line(before_paren))

                # Process text within parentheses
                paren_content = line[start_paren : end_paren + 1].strip()
                if len(paren_content) > self.max_line_length:
                    # Split the content within parentheses if it's too long
                    split_paren_content = self.split_line(paren_content)
                    processed_lines.extend(split_paren_content)
                else:
                    processed_lines.append(paren_content)

                line = line[end_paren + 1 :].strip()
            else:
                split_point = self.find_best_split_point(line)
                processed_lines.append(line[:split_point].strip())
                line = line[split_point:].strip()

            iteration_count += 1

        if line:  # Add any remaining part
            processed_lines.extend(self.split_line(line))

        if iteration_count >= max_iterations:
            self.logger.error(f"Maximum iterations exceeded in process_line for line: {line}")

        return processed_lines

    def find_best_split_point(self, line):
        """
        Find the best split point in a line based on the specified criteria.
        """

        self.logger.debug(f"Finding best_split_point for line: {line}")
        words = line.split()
        mid_word_index = len(words) // 2
        self.logger.debug(f"words: {words} mid_word_index: {mid_word_index}")

        # Check for a comma within one or two words of the middle word
        if "," in line:
            mid_point = len(" ".join(words[:mid_word_index]))
            comma_indices = [i for i, char in enumerate(line) if char == ","]

            for index in comma_indices:
                if abs(mid_point - index) < 20 and len(line[: index + 1].strip()) <= self.config.max_line_length:
                    self.logger.debug(
                        f"Found comma at index {index} which is within 20 characters of mid_point {mid_point} and results in a suitable line length, accepting as split point"
                    )
                    return index + 1  # Include the comma in the first line

        # Check for 'and'
        if " and " in line:
            mid_point = len(line) // 2
            and_indices = [m.start() for m in re.finditer(" and ", line)]
            for index in sorted(and_indices, key=lambda x: abs(x - mid_point)):
                if len(line[: index + len(" and ")].strip()) <= self.config.max_line_length:
                    self.logger.debug(f"Found 'and' at index {index} which results in a suitable line length, accepting as split point")
                    return index + len(" and ")

        # If no better split point is found, try splitting at the middle word
        if len(words) > 2 and mid_word_index > 0:
            split_at_middle = len(" ".join(words[:mid_word_index]))
            if split_at_middle <= self.config.max_line_length:
                self.logger.debug(f"Splitting at middle word index: {mid_word_index}")
                return split_at_middle

        # If the line is still too long, find the last space before max_line_length
        if len(line) > self.config.max_line_length:
            last_space = line.rfind(" ", 0, self.config.max_line_length)
            if last_space != -1:
                self.logger.debug(f"Splitting at last space before max_line_length: {last_space}")
                return last_space
            else:
                # If no space is found, split at max_line_length
                self.logger.debug(f"No space found, forcibly splitting at max_line_length: {self.config.max_line_length}")
                return self.config.max_line_length

        # If the line is shorter than max_line_length, return its length
        return len(line)

    def find_matching_paren(self, line, start_index):
        """
        Find the index of the matching closing parenthesis for the opening parenthesis at start_index.
        """
        stack = 0
        for i in range(start_index, len(line)):
            if line[i] == "(":
                stack += 1
            elif line[i] == ")":
                stack -= 1
                if stack == 0:
                    return i
        return -1  # No matching parenthesis found

    def split_line(self, line):
        """
        Split a line into multiple lines if it exceeds the maximum length.
        """
        if len(line) <= self.config.max_line_length:
            return [line]

        split_lines = []
        while len(line) > self.config.max_line_length:
            split_point = self.find_best_split_point(line)
            split_lines.append(line[:split_point].strip())
            line = line[split_point:].strip()

        if line:
            split_lines.append(line)

        return split_lines

    def generate_lrc(self, segments: List[LyricsSegment], output_prefix: str) -> str:
        """Generate LRC format lyrics file."""
        self.logger.info("Generating LRC format lyrics")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "lrc")

        try:
            self._write_lrc_file(output_path, segments)
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

    def generate_ass(self, segments: List[LyricsSegment], output_prefix: str) -> str:
        """Generate ASS format subtitles file."""
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "ass")

        try:
            # Create screens from segments
            initial_screens = self._create_screens(segments)

            # Get song duration from last segment's end time
            song_duration = int(segments[-1].end_time)

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
        output_path = self._get_output_path(f"{output_prefix} (With Vocals)", "mkv")

        try:
            cmd = self._build_ffmpeg_command(ass_path, audio_path, output_path)
            self._run_ffmpeg_command(cmd)
            self.logger.info(f"Video generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate video: {str(e)}")
            raise

    def _resize_background_image(self, input_path: str) -> str:
        """Resize background image to match target resolution and save to temp file."""
        target_width, target_height = self.video_resolution_num

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

        temp_path = os.path.join(self.config.cache_dir, "resized_background.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
            temp_path,
        ]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return temp_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to resize background image: {e.output}")
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
            # Resize background image first
            resized_bg = self._resize_background_image(self.config.video_background_image)
            self.logger.debug(f"Using resized background image: {resized_bg}")
            cmd.extend([
                "-loop", "1",  # Loop the image
                "-i", resized_bg,
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
        provider_name = lyrics_data.metadata.source.title()
        output_path = self._get_output_path(f"{output_prefix} (Lyrics {provider_name})", "txt")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(lyrics_data.lyrics)
            self.logger.info(f"Plain lyrics file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to write plain lyrics file: {str(e)}")
            raise

    def write_plain_lyrics_from_correction(self, segments: List[LyricsSegment], output_prefix: str) -> str:
        """Write corrected lyrics as plain text file."""
        self.logger.info("Writing corrected lyrics file")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "txt")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in segments:
                    f.write(f"{segment.text}\n")
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

    def _resize_segments(self, segments: List[LyricsSegment]) -> List[LyricsSegment]:
        """Resize segments to ensure no line exceeds maximum length while preserving timing."""
        self.logger.info("Resizing segments to match maximum line length")
        resized_segments: List[LyricsSegment] = []

        for segment in segments:
            if len(segment.text) <= self.config.max_line_length:
                resized_segments.append(segment)
                continue

            # Process the segment text to determine split points
            split_lines = self._process_segment_text(segment.text)
            
            # Track current position in the text for word matching
            current_pos = 0
            segment_text = segment.text
            
            for line in split_lines:
                # Find the position of this line in the original text
                line_pos = segment_text.find(line, current_pos)
                if line_pos == -1:
                    self.logger.warning(f"Could not find line '{line}' in segment text")
                    continue
                    
                # Find words that fall within this line's boundaries
                line_words = []
                line_end = line_pos + len(line)
                
                for word in segment.words:
                    # Find word position in original text
                    word_pos = segment_text.find(word.text, current_pos)
                    if word_pos >= line_pos and word_pos + len(word.text) <= line_end:
                        line_words.append(word)
                
                if line_words:
                    new_segment = LyricsSegment(
                        text=line.strip(),
                        words=line_words,
                        start_time=line_words[0].start_time,
                        end_time=line_words[-1].end_time
                    )
                    resized_segments.append(new_segment)
                
                current_pos = line_end

        return resized_segments

    def _process_segment_text(self, text: str) -> List[str]:
        """Process segment text to determine optimal split points.

        Args:
            text: Segment text to process

        Returns:
            List of split lines
        """
        processed_lines: List[str] = []
        remaining_text = text.strip()

        while remaining_text:
            if len(remaining_text) <= self.config.max_line_length:
                processed_lines.append(remaining_text)
                break

            # Find best split point
            if "(" in remaining_text and ")" in remaining_text:
                # Handle parenthetical content
                start_paren = remaining_text.find("(")
                end_paren = self._find_matching_paren(remaining_text, start_paren)

                if end_paren > 0:
                    # Process text before parentheses if it exists
                    if start_paren > 0:
                        before_paren = remaining_text[:start_paren].strip()
                        if before_paren:
                            processed_lines.extend(self._split_line(before_paren))

                    # Process parenthetical content
                    paren_content = remaining_text[start_paren : end_paren + 1].strip()
                    if len(paren_content) > self.config.max_line_length:
                        processed_lines.extend(self._split_line(paren_content))
                    else:
                        processed_lines.append(paren_content)

                    remaining_text = remaining_text[end_paren + 1 :].strip()
                    continue

            # Find split point for normal text
            split_point = self._find_best_split_point(remaining_text)
            processed_lines.append(remaining_text[:split_point].strip())
            remaining_text = remaining_text[split_point:].strip()

        return processed_lines

    def _find_best_split_point(self, line: str) -> int:
        """Find the best split point in a line based on the specified criteria."""
        words = line.split()
        mid_word_index = len(words) // 2
        
        # Don't split very short lines
        if len(words) <= 3 or len(line) <= self.config.max_line_length:
            return len(line)

        # Check for natural break points near the middle
        mid_point = len(line) // 2
        
        # Look for sentence endings first
        for punct in [". ", "! ", "? "]:
            if punct in line:
                punct_indices = [i + len(punct) - 1 for i in range(len(line)) if line[i:i+len(punct)] == punct]
                for index in sorted(punct_indices, key=lambda x: abs(x - mid_point)):
                    if len(line[:index].strip()) <= self.config.max_line_length:
                        return index

        # Then look for clause breaks
        if ", " in line:
            comma_indices = [i + 1 for i in range(len(line)) if line[i:i+2] == ", "]
            for index in sorted(comma_indices, key=lambda x: abs(x - mid_point)):
                if len(line[:index].strip()) <= self.config.max_line_length:
                    return index

        # Then try natural phrase breaks
        for phrase in [" and ", " but ", " or ", " - ", "; "]:
            if phrase in line:
                phrase_indices = [m.start() + len(phrase) for m in re.finditer(phrase, line)]
                for index in sorted(phrase_indices, key=lambda x: abs(x - mid_point)):
                    if len(line[:index].strip()) <= self.config.max_line_length:
                        return index

        # Fall back to splitting at the last space before max_line_length
        last_space = line.rfind(" ", 0, self.config.max_line_length)
        if last_space != -1:
            return last_space

        return self.config.max_line_length

    def _find_matching_paren(self, line: str, start_index: int) -> int:
        """Find the index of the matching closing parenthesis for the opening parenthesis at start_index."""
        stack = 0
        for i in range(start_index, len(line)):
            if line[i] == "(":
                stack += 1
            elif line[i] == ")":
                stack -= 1
                if stack == 0:
                    return i
        return -1  # No matching parenthesis found

    def _split_line(self, line: str) -> List[str]:
        """Split a line into multiple lines if it exceeds the maximum length."""
        if len(line) <= self.config.max_line_length:
            return [line]

        split_lines = []
        while len(line) > self.config.max_line_length:
            split_point = self._find_best_split_point(line)
            split_lines.append(line[:split_point].strip())
            line = line[split_point:].strip()

        if line:
            split_lines.append(line)

        return split_lines
