import logging
import os
from typing import List, Optional, Tuple
from datetime import timedelta
from datetime import timedelta
from typing import List, Optional, Tuple
import itertools
import logging

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen, LyricsLine
from lyrics_transcriber.output.ass.screens_to_ass import create_styled_subtitles


class SubtitlesGenerator:
    """Handles generation of subtitle files in various formats."""

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

    def generate_ass(self, segments: List[LyricsSegment], output_prefix: str) -> str:
        self.logger.info("Generating ASS format subtitles")
        output_path = self._get_output_path(f"{output_prefix} (Lyrics Corrected)", "ass")

        try:
            self.logger.debug(f"Processing {len(segments)} segments")
            for i, segment in enumerate(segments):
                self.logger.debug(f"\nSegment {i}:")
                self.logger.debug(f"  Text: {segment.text}")
                self.logger.debug(f"  Timing: {segment.start_time:.3f}s - {segment.end_time:.3f}s")
                self.logger.debug(f"  Words ({len(segment.words)}):")
                for j, word in enumerate(segment.words):
                    self.logger.debug(f"    Word {j}: '{word.text}' ({word.start_time:.3f}s - {word.end_time:.3f}s)")
                    if word.confidence is not None:
                        self.logger.debug(f"      Confidence: {word.confidence:.3f}")

            initial_screens = self._create_screens(segments)
            self.logger.debug(f"Created {len(initial_screens)} initial screens")

            song_duration = int(segments[-1].end_time)
            self.logger.debug(f"Song duration: {song_duration} seconds")

            screens = self.set_segment_end_times(initial_screens, song_duration)
            self.logger.debug("Set segment end times")

            screens = self.set_screen_start_times(screens)
            self.logger.debug("Set screen start times")

            lyric_subtitles_ass = create_styled_subtitles(screens, self.video_resolution, self.font_size)
            self.logger.debug("Created styled subtitles")

            lyric_subtitles_ass.write(output_path)
            self.logger.info(f"ASS file generated: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate ASS file: {str(e)}", exc_info=True)
            raise

    def _create_screens(self, segments: List[LyricsSegment]) -> List[LyricsScreen]:
        self.logger.debug("Creating screens from segments")
        screens: List[LyricsScreen] = []
        screen: Optional[LyricsScreen] = None

        max_lines_per_screen = 4

        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.text}")

            if screen is None or len(screen.lines) >= max_lines_per_screen:
                screen = LyricsScreen(video_size=self.video_resolution, line_height=self.line_height, logger=self.logger)
                screens.append(screen)
                self.logger.debug(f"Created new screen. Total screens: {len(screens)}")

            line = LyricsLine(logger=self.logger)
            line.segments.append(segment)
            screen.lines.append(line)
            self.logger.debug(f"Added line to screen: {line}")

        return screens

    def set_segment_end_times(self, screens: List[LyricsScreen], song_duration_seconds: int) -> List[LyricsScreen]:
        self.logger.debug("Setting segment end times")
        segments = list(itertools.chain.from_iterable([l.segments for s in screens for l in s.lines]))

        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.text}")
            if not segment.end_time:
                if i == len(segments) - 1:
                    self.logger.debug(f"Setting last segment end time to song duration: {song_duration_seconds}")
                    segment.end_time = song_duration_seconds
                else:
                    next_segment = segments[i + 1]
                    self.logger.debug(f"Setting segment end time to next segment start time: {next_segment.start_time}")
                    segment.end_time = next_segment.start_time

        return screens

    def set_screen_start_times(self, screens: List[LyricsScreen]) -> List[LyricsScreen]:
        """Set screen timings based on actual content."""
        self.logger.debug("Setting screen start times")

        for screen in screens:
            # Each screen's timing is based on its content
            screen.start_ts = timedelta(seconds=min(line.ts for line in screen.lines))
            screen.end_ts = timedelta(seconds=max(line.end_ts for line in screen.lines))

        return screens
