import os
import logging
from typing import List, Optional, Tuple, Union
import subprocess
import json

from lyrics_transcriber.output.ass.section_screen import SectionScreen
from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass import LyricsScreen, LyricsLine
from lyrics_transcriber.output.ass.ass import ASS
from lyrics_transcriber.output.ass.style import Style
from lyrics_transcriber.output.ass.constants import ALIGN_TOP_CENTER
from lyrics_transcriber.output.ass import LyricsScreen
from lyrics_transcriber.output.ass.section_detector import SectionDetector


class SubtitlesGenerator:
    """Handles generation of subtitle files in various formats."""

    MAX_LINES_PER_SCREEN = 4  # Maximum number of lines to show on screen at once

    def __init__(
        self,
        output_dir: str,
        video_resolution: Tuple[int, int],
        font_size: int,
        line_height: int,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize SubtitleGenerator.

        Args:
            output_dir: Directory where output files will be written
            video_resolution: Tuple of (width, height) for video resolution
            font_size: Font size for subtitles
            line_height: Line height for subtitle positioning
            logger: Optional logger instance
        """
        self.output_dir = output_dir
        self.video_resolution = video_resolution
        self.font_size = font_size
        self.line_height = line_height
        self.logger = logger or logging.getLogger(__name__)

    def _get_output_path(self, output_prefix: str, extension: str) -> str:
        """Generate full output path for a file."""
        return os.path.join(self.output_dir, f"{output_prefix}.{extension}")

    def _get_audio_duration(self, audio_filepath: str, segments: Optional[List[LyricsSegment]] = None) -> float:
        """Get audio duration using ffprobe."""
        try:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", audio_filepath]
            probe_output = subprocess.check_output(probe_cmd, universal_newlines=True)
            probe_data = json.loads(probe_output)
            duration = float(probe_data["format"]["duration"])
            self.logger.debug(f"Detected audio duration: {duration:.2f}s")
            return duration
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to get audio duration: {e}")
            # Fallback to last segment end time plus buffer
            if segments:
                duration = segments[-1].end_time + 30.0
                self.logger.warning(f"Using fallback duration: {duration:.2f}s")
                return duration
            return 0.0

    def generate_ass(self, segments: List[LyricsSegment], output_prefix: str, audio_filepath: str) -> str:
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(f"{output_prefix} (Karaoke)", "ass")

        try:
            self.logger.debug(f"Processing {len(segments)} segments")
            song_duration = self._get_audio_duration(audio_filepath, segments)

            screens = self._create_screens(segments, song_duration)
            self.logger.debug(f"Created {len(screens)} initial screens")

            lyric_subtitles_ass = self._create_styled_subtitles(screens, self.video_resolution, self.font_size)
            self.logger.debug("Created styled subtitles")

            lyric_subtitles_ass.write(output_path)
            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}", exc_info=True)
            raise

    def _create_screens(self, segments: List[LyricsSegment], song_duration: float) -> List[LyricsScreen]:
        """Create screens from segments with detailed logging."""
        self.logger.debug("Creating screens from segments")

        # Create section screens and get instrumental boundaries
        section_screens = self._create_section_screens(segments, song_duration)
        instrumental_times = self._get_instrumental_times(section_screens)

        # Create regular lyric screens
        lyric_screens = self._create_lyric_screens(segments, instrumental_times)

        # Merge and process all screens
        all_screens = self._merge_and_process_screens(section_screens, lyric_screens)

        # Log final results
        self._log_final_screens(all_screens)

        return all_screens

    def _create_section_screens(self, segments: List[LyricsSegment], song_duration: float) -> List[SectionScreen]:
        """Create section screens using SectionDetector."""
        section_detector = SectionDetector(logger=self.logger)
        return section_detector.process_segments(segments, self.video_resolution, self.line_height, song_duration)

    def _get_instrumental_times(self, section_screens: List[SectionScreen]) -> List[Tuple[float, float]]:
        """Extract instrumental section time boundaries."""
        instrumental_times = [
            (s.start_time, s.end_time) for s in section_screens if isinstance(s, SectionScreen) and s.section_type == "INSTRUMENTAL"
        ]

        self.logger.debug(f"Found {len(instrumental_times)} instrumental sections:")
        for start, end in instrumental_times:
            self.logger.debug(f"  {start:.2f}s - {end:.2f}s")

        return instrumental_times

    def _create_lyric_screens(self, segments: List[LyricsSegment], instrumental_times: List[Tuple[float, float]]) -> List[LyricsScreen]:
        """Create regular lyric screens, handling instrumental boundaries."""
        screens: List[LyricsScreen] = []
        current_screen: Optional[LyricsScreen] = None

        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.start_time:.2f}s - {segment.end_time:.2f}s")

            # Skip segments in instrumental sections
            if self._is_in_instrumental_section(segment, instrumental_times):
                continue

            # Check if we need a new screen
            if self._should_start_new_screen(current_screen, segment, instrumental_times):
                current_screen = LyricsScreen(video_size=self.video_resolution, line_height=self.line_height, logger=self.logger)
                screens.append(current_screen)
                self.logger.debug("  Created new screen")

            # Add line to current screen
            line = LyricsLine(logger=self.logger, segment=segment)
            current_screen.lines.append(line)
            self.logger.debug(f"  Added line to screen (now has {len(current_screen.lines)} lines)")

        return screens

    def _is_in_instrumental_section(self, segment: LyricsSegment, instrumental_times: List[Tuple[float, float]]) -> bool:
        """Check if a segment falls within any instrumental section."""
        for inst_start, inst_end in instrumental_times:
            if segment.start_time >= inst_start and segment.start_time < inst_end:
                self.logger.debug(f"  Skipping segment - falls within instrumental {inst_start:.2f}s - {inst_end:.2f}s")
                return True
        return False

    def _should_start_new_screen(
        self, current_screen: Optional[LyricsScreen], segment: LyricsSegment, instrumental_times: List[Tuple[float, float]]
    ) -> bool:
        """Determine if a new screen should be started."""
        if current_screen is None:
            return True

        if len(current_screen.lines) >= self.MAX_LINES_PER_SCREEN:
            return True

        # Check if this segment is first after any instrumental section
        if current_screen.lines:
            prev_segment = current_screen.lines[-1].segment
            for inst_start, inst_end in instrumental_times:
                if prev_segment.end_time <= inst_start and segment.start_time >= inst_end:
                    self.logger.debug(f"  Forcing new screen - first segment after instrumental {inst_start:.2f}s - {inst_end:.2f}s")
                    return True

        return False

    def _merge_and_process_screens(
        self, section_screens: List[SectionScreen], lyric_screens: List[LyricsScreen]
    ) -> List[Union[SectionScreen, LyricsScreen]]:
        """Merge section and lyric screens, marking post-instrumental screens."""
        all_screens = sorted(section_screens + lyric_screens, key=lambda s: s.start_ts)

        for i in range(1, len(all_screens)):
            if isinstance(all_screens[i - 1], SectionScreen):
                all_screens[i].post_instrumental = True
                self.logger.debug(f"Marked screen {i+1} as post-instrumental")

        return all_screens

    def _log_final_screens(self, screens: List[Union[SectionScreen, LyricsScreen]]) -> None:
        """Log details of all final screens."""
        self.logger.debug("Final screens created:")
        for i, screen in enumerate(screens):
            self.logger.debug(f"Screen {i + 1}:")
            if isinstance(screen, SectionScreen):
                self.logger.debug(f"  Section: {screen.section_type}")
                self.logger.debug(f"  Text: {screen.text}")
                self.logger.debug(f"  Time: {screen.start_time:.2f}s - {screen.end_time:.2f}s")
            else:
                self.logger.debug(f"  Number of lines: {len(screen.lines)}")
                for j, line in enumerate(screen.lines):
                    self.logger.debug(f"    Line {j + 1} ({line.segment.start_time:.2f}s - {line.segment.end_time:.2f}s): {line}")

    def _create_styled_ass_instance(self, resolution, fontsize):
        a = ASS()
        a.set_resolution(resolution)

        a.styles_format = [
            "Name",  # The name of the Style. Case sensitive. Cannot include commas.
            "Fontname",  # The fontname as used by Windows. Case-sensitive.
            "Fontsize",  # Font size
            "PrimaryColour",  # This is the colour that a subtitle will normally appear in.
            "SecondaryColour",  # This colour may be used instead of the Primary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
            "OutlineColour",  # This colour may be used instead of the Primary or Secondary colour when a subtitle is automatically shifted to prevent an onscreen collsion, to distinguish the different subtitles.
            "BackColour",  # This is the colour of the subtitle outline or shadow, if these are used
            "Bold",  # This defines whether text is bold (true) or not (false). -1 is True, 0 is False
            "Italic",  # This defines whether text is italic (true) or not (false). -1 is True, 0 is False
            "Underline",  # [-1 or 0]
            "StrikeOut",  # [-1 or 0]
            "ScaleX",  # Modifies the width of the font. [percent]
            "ScaleY",  # Modifies the height of the font. [percent]
            "Spacing",  # Extra space between characters. [pixels]
            "Angle",  # The origin of the rotation is defined by the alignment. Can be a floating point number. [degrees]
            "BorderStyle",  # 1=Outline + drop shadow, 3=Opaque box
            "Outline",  # If BorderStyle is 1,  then this specifies the width of the outline around the text, in pixels. Values may be 0, 1, 2, 3 or 4.
            "Shadow",  # If BorderStyle is 1,  then this specifies the depth of the drop shadow behind the text, in pixels. Values may be 0, 1, 2, 3 or 4. Drop shadow is always used in addition to an outline - SSA will force an outline of 1 pixel if no outline width is given.
            "Alignment",  # This sets how text is "justified" within the Left/Right onscreen margins, and also the vertical placing. Values may be 1=Left, 2=Centered, 3=Right. Add 4 to the value for a "Toptitle". Add 8 to the value for a "Midtitle". eg. 5 = left-justified toptitle
            "MarginL",  # This defines the Left Margin in pixels. It is the distance from the left-hand edge of the screen.The three onscreen margins (MarginL, MarginR, MarginV) define areas in which the subtitle text will be displayed.
            "MarginR",  # This defines the Right Margin in pixels. It is the distance from the right-hand edge of the screen.
            "MarginV",  # MarginV. This defines the vertical Left Margin in pixels. For a subtitle, it is the distance from the bottom of the screen. For a toptitle, it is the distance from the top of the screen. For a midtitle, the value is ignored - the text will be vertically centred
            "Encoding",  #
        ]

        style = Style()
        style.type = "Style"
        style.Name = "Nomad"
        style.Fontname = "Avenir Next Bold"
        style.Fontsize = fontsize

        style.PrimaryColour = (112, 112, 247, 255)
        style.SecondaryColour = (255, 255, 255, 255)
        style.OutlineColour = (26, 58, 235, 255)
        style.BackColour = (0, 255, 0, 255)  # (26, 58, 235, 255)

        style.Bold = False
        style.Italic = False
        style.Underline = False
        style.StrikeOut = False

        style.ScaleX = 100
        style.ScaleY = 100
        style.Spacing = 0
        style.Angle = 0.0
        style.BorderStyle = 1
        style.Outline = 1
        style.Shadow = 0
        style.Alignment = ALIGN_TOP_CENTER
        style.MarginL = 0
        style.MarginR = 0
        style.MarginV = 0
        style.Encoding = 0

        a.add_style(style)

        a.events_format = ["Layer", "Style", "Start", "End", "MarginV", "Text"]
        return a, style

    def _create_styled_subtitles(
        self,
        screens: List[LyricsScreen],
        resolution,
        fontsize,
    ) -> ASS:
        """Create styled ASS subtitles."""
        a, style = self._create_styled_ass_instance(resolution, fontsize)

        active_lines = []
        for i, screen in enumerate(screens):
            next_screen_start = screens[i + 1].start_ts if i < len(screens) - 1 else None

            self.logger.debug(f"Processing screen {i+1}:")

            # Get events and updated active lines
            events, active_lines = screen.as_ass_events(style, next_screen_start, active_lines)
            for event in events:
                a.add(event)

            # Update active_lines for next screen
            active_lines = [(end, pos, text) for end, pos, text in active_lines if isinstance(end, float)]

        return a
