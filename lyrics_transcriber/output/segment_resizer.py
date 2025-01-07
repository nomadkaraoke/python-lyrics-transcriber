import logging
import re
from typing import List, Optional, Tuple

from lyrics_transcriber.types import LyricsSegment, Word


class SegmentResizer:
    """Handles resizing of lyrics segments to ensure proper line lengths."""

    def __init__(self, max_line_length: int = 36, logger: Optional[logging.Logger] = None):
        self.max_line_length = max_line_length
        self.logger = logger or logging.getLogger(__name__)

    def resize_segments(self, segments: List[LyricsSegment]) -> List[LyricsSegment]:
        """Main entry point for resizing segments."""
        self._log_input_segments(segments)
        resized_segments: List[LyricsSegment] = []

        for segment_idx, segment in enumerate(segments):
            cleaned_segment = self._create_cleaned_segment(segment)

            # Only split if the segment is longer than max_line_length
            if len(cleaned_segment.text) <= self.max_line_length:
                resized_segments.append(cleaned_segment)
                continue

            # Process oversized segments
            resized_segments.extend(self._split_oversized_segment(segment_idx, segment))

        self._log_output_segments(resized_segments)
        return resized_segments

    def _clean_text(self, text: str) -> str:
        """Clean text by removing newlines and extra whitespace."""
        # First replace newlines with spaces, then normalize all whitespace
        return " ".join(text.replace("\n", " ").split())

    def _create_cleaned_segment(self, segment: LyricsSegment) -> LyricsSegment:
        """Create a new segment with cleaned text."""
        cleaned_text = self._clean_text(segment.text)
        return LyricsSegment(text=cleaned_text, words=segment.words, start_time=segment.start_time, end_time=segment.end_time)

    def _create_cleaned_word(self, word: Word) -> Word:
        """Create a new word with cleaned text."""
        cleaned_text = self._clean_text(word.text)
        return Word(
            text=cleaned_text,
            start_time=word.start_time,
            end_time=word.end_time,
            confidence=word.confidence if hasattr(word, "confidence") else None,
        )

    def _split_oversized_segment(self, segment_idx: int, segment: LyricsSegment) -> List[LyricsSegment]:
        """Split an oversized segment into multiple segments."""
        self.logger.info(f"Processing oversized segment {segment_idx}: '{segment.text}'")
        segment_text = self._clean_text(segment.text)
        split_lines = self._process_segment_text(segment_text)
        self.logger.debug(f"Split into {len(split_lines)} lines: {split_lines}")

        return self._create_segments_from_lines(segment_text, split_lines, segment.words)

    def _create_segments_from_lines(self, segment_text: str, split_lines: List[str], words: List[Word]) -> List[LyricsSegment]:
        """Create segments from split lines while preserving word timing."""
        segments: List[LyricsSegment] = []
        words_to_process = words.copy()

        for line in split_lines:
            # Get all words that belong to this line
            line_words = []

            # Keep processing words until we find one that doesn't belong to this line
            while words_to_process:
                word = words_to_process[0]  # Look at the next word

                # Check if this word appears in the line
                if word.text in line:
                    # Only use the word if it's the next occurrence in the text
                    word_in_line_pos = line.find(word.text)
                    if word_in_line_pos != -1:
                        line_words.append(words_to_process.pop(0))
                        continue

                # If we get here, the word doesn't belong to this line
                break

            if line_words:
                segments.append(self._create_segment_from_words(line, line_words))

        return segments

    def _create_line_segment(
        self, line_idx: int, line: str, segment_text: str, available_words: List[Word], current_pos: int
    ) -> Optional[LyricsSegment]:
        """Create a single segment from a line of text."""
        line_pos = segment_text.find(line, current_pos)
        if line_pos == -1:
            self.logger.error(f"Failed to find line '{line}' in segment text '{segment_text}' " f"starting from position {current_pos}")
            return None

        line_words = self._find_words_for_line(line, line_pos, len(line), segment_text, available_words, current_pos)

        if line_words:
            return self._create_segment_from_words(line, line_words)
        else:
            self.logger.warning(f"No words found for line '{line}'")
            return None

    def _find_words_for_line(
        self, line: str, line_pos: int, line_length: int, segment_text: str, available_words: List[Word], current_pos: int
    ) -> List[Word]:
        """Find words that belong to a specific line."""
        line_words = []
        line_text = line.strip()
        remaining_text = line_text
        
        for word in available_words:
            # Skip if word isn't in remaining text
            if word.text not in remaining_text:
                continue
            
            # Find position of word in line
            word_pos = remaining_text.find(word.text)
            if word_pos != -1:
                line_words.append(word)
                # Remove processed text up to and including this word
                remaining_text = remaining_text[word_pos + len(word.text):].strip()
            
            if not remaining_text:  # All words found
                break
            
        return line_words

    def _create_segment_from_words(self, line: str, words: List[Word]) -> LyricsSegment:
        """Create a new segment from a list of words."""
        cleaned_text = self._clean_text(line)
        return LyricsSegment(text=cleaned_text, words=words, start_time=words[0].start_time, end_time=words[-1].end_time)

    def _process_segment_text(self, text: str) -> List[str]:
        """Process segment text to determine optimal split points."""
        self.logger.debug(f"Processing segment text: '{text}'")
        processed_lines: List[str] = []
        remaining_text = text.strip()

        while remaining_text:
            self.logger.debug(f"Remaining text to process: '{remaining_text}'")

            # If remaining text is within limit, add it and we're done
            if len(remaining_text) <= self.max_line_length:
                processed_lines.append(remaining_text)
                break

            # Find best split point
            split_point = self._find_best_split_point(remaining_text)
            first_part = remaining_text[:split_point].strip()
            second_part = remaining_text[split_point:].strip()

            # Only split if:
            # 1. We found a valid split point
            # 2. First part isn't too long
            # 3. Both parts are non-empty
            if split_point < len(remaining_text) and len(first_part) <= self.max_line_length and first_part and second_part:

                processed_lines.append(first_part)
                remaining_text = second_part
            else:
                # If we can't find a good split, keep the whole text
                processed_lines.append(remaining_text)
                break

        return processed_lines

    def _find_best_split_point(self, line: str) -> int:
        """Find the best split point that creates natural, well-balanced segments."""
        self.logger.debug(f"Finding best split point for line: '{line}' (length: {len(line)})")

        # If line is within max length, don't split
        if len(line) <= self.max_line_length:
            return len(line)

        break_points = self._find_break_points(line)
        best_point = None
        best_score = float("-inf")

        # Try each break point and score it
        for priority, points in enumerate(break_points):
            for point in sorted(points):  # Sort points to prefer earlier ones in same priority
                if point <= 0 or point >= len(line):
                    continue

                first_part = line[:point].strip()

                # Skip if first part is too long
                if len(first_part) > self.max_line_length:
                    continue

                # Score this break point
                score = self._score_break_point(line, point, priority)
                if score > best_score:
                    best_score = score
                    best_point = point

        # If no good break points found, fall back to last space before max_length
        if best_point is None:
            last_space = line.rfind(" ", 0, self.max_line_length)
            if last_space != -1:
                return last_space

        return best_point if best_point is not None else self.max_line_length

    def _score_break_point(self, line: str, point: int, priority: int) -> float:
        """Score a potential break point based on multiple factors."""
        first_segment = line[:point].strip()
        second_segment = line[point:].strip()

        # Base score starts with priority (higher priority = better score)
        score = 100 - (priority * 20)  # Priorities 0-4 give scores 100,80,60,40,20

        # Penalize if segments are very unbalanced (prefer more even splits)
        length_ratio = min(len(first_segment), len(second_segment)) / max(len(first_segment), len(second_segment))
        score += length_ratio * 10  # 0-10 points for balance

        # Bonus for splits that create segments closer to target length
        target_length = self.max_line_length * 0.7  # Prefer segments around 70% of max
        first_length_score = 1 - abs(len(first_segment) - target_length) / self.max_line_length
        score += first_length_score * 5  # 0-5 points for good length

        return score

    def _find_break_points(self, line: str) -> List[List[int]]:
        """Find potential break points in order of preference.
        Returns a list of lists, where each inner list contains break points of the same priority.
        Break points are the indices where the text should be split (after the punctuation/phrase).
        """
        break_points = []

        # Priority 1: Sentence endings
        sentence_breaks = []
        for punct in [".", "!", "?"]:
            for match in re.finditer(rf"\{punct}\s+", line):
                sentence_breaks.append(match.start() + 1)  # Position after the punctuation
        break_points.append(sentence_breaks)

        # Priority 2: Major clause breaks (semicolons, dashes)
        major_breaks = []
        for punct in [";", " - "]:
            for match in re.finditer(re.escape(punct), line):
                major_breaks.append(match.start())  # Position before the punctuation
        break_points.append(major_breaks)

        # Priority 3: Comma breaks, typically marking natural pauses
        comma_breaks = []
        for match in re.finditer(r",\s+", line):
            comma_breaks.append(match.start() + 1)  # Position after the comma
        break_points.append(comma_breaks)

        # Priority 4: Coordinating conjunctions with surrounding spaces
        conjunction_breaks = []
        for conj in [" and ", " but ", " or "]:
            for match in re.finditer(re.escape(conj), line):
                conjunction_breaks.append(match.start())  # Position before the conjunction
        break_points.append(conjunction_breaks)

        # Priority 5: Prepositions or articles with surrounding spaces (last resort)
        minor_breaks = []
        for prep in [" in ", " at ", " the ", " a "]:
            for match in re.finditer(re.escape(prep), line):
                minor_breaks.append(match.start())  # Position before the preposition
        break_points.append(minor_breaks)

        return break_points

    def _log_input_segments(self, segments: List[LyricsSegment]) -> None:
        """Log input segment information."""
        self.logger.info(f"Starting segment resize. Input: {len(segments)} segments")
        for idx, segment in enumerate(segments):
            self.logger.debug(
                f"Input segment {idx}: text='{segment.text}', "
                f"words={len(segment.words)} words, "
                f"time={segment.start_time:.2f}-{segment.end_time:.2f}"
            )

    def _log_output_segments(self, segments: List[LyricsSegment]) -> None:
        """Log output segment information."""
        self.logger.info(f"Finished resizing. Output: {len(segments)} segments")
        for idx, segment in enumerate(segments):
            self.logger.debug(
                f"Output segment {idx}: text='{segment.text}', "
                f"words={len(segment.words)} words, "
                f"time={segment.start_time:.2f}-{segment.end_time:.2f}"
            )
