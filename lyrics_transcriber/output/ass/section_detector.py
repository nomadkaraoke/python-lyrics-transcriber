from typing import List, Optional, Tuple
import logging

from lyrics_transcriber.types import LyricsSegment
from lyrics_transcriber.output.ass.lyrics_models import LyricsScreen, SectionScreen


class SectionDetector:
    """Detects and creates section screens between lyrics."""

    def __init__(self, gap_threshold: float = 10.0, logger: Optional[logging.Logger] = None):
        self.gap_threshold = gap_threshold
        self.logger = logger or logging.getLogger(__name__)

    def process_segments(
        self, segments: List[LyricsSegment], video_size: Tuple[int, int], line_height: int, song_duration: float
    ) -> List[LyricsScreen]:
        """Process segments and insert section screens where appropriate.

        Args:
            segments: List of lyric segments
            video_size: Tuple of (width, height) for video resolution
            line_height: Height of each line in pixels
            song_duration: Total duration of the song in seconds
        """
        if not segments:
            return []

        screens: List[LyricsScreen] = []

        # Check for intro
        if segments[0].start_time >= self.gap_threshold:
            self.logger.debug(f"Detected intro section: 0.0 - {segments[0].start_time:.2f}s")
            screens.append(
                SectionScreen(
                    section_type="INTRO",
                    start_time=0.0,
                    end_time=segments[0].start_time,
                    video_size=video_size,
                    line_height=line_height,
                    logger=self.logger,
                )
            )

        # Check for instrumental sections between segments
        for i in range(len(segments) - 1):
            gap = segments[i + 1].start_time - segments[i].end_time
            if gap >= self.gap_threshold:
                self.logger.debug(f"Detected instrumental section: {segments[i].end_time:.2f} - {segments[i + 1].start_time:.2f}s")
                screens.append(
                    SectionScreen(
                        section_type="INSTRUMENTAL",
                        start_time=segments[i].end_time,
                        end_time=segments[i + 1].start_time,
                        video_size=video_size,
                        line_height=line_height,
                        logger=self.logger,
                    )
                )

        # Check for outro
        if segments:  # Only add outro if there are segments
            last_segment = segments[-1]
            outro_duration = song_duration - last_segment.end_time
            if outro_duration >= self.gap_threshold:
                self.logger.debug(f"Detected outro section: {last_segment.end_time:.2f}s - {song_duration:.2f}s")
                screens.append(
                    SectionScreen(
                        section_type="OUTRO",
                        start_time=last_segment.end_time,
                        end_time=song_duration,
                        video_size=video_size,
                        line_height=line_height,
                        logger=self.logger,
                    )
                )

        return screens
