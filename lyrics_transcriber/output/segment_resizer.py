import logging
import re
from typing import List, Optional

from lyrics_transcriber.types import LyricsSegment, Word


class SegmentResizer:
    """Handles resizing of lyrics segments to ensure proper line lengths."""

    def __init__(self, max_line_length: int = 36, logger: Optional[logging.Logger] = None):
        """Initialize SegmentResizer.

        Args:
            max_line_length: Maximum characters per line
            logger: Optional logger instance
        """
        self.max_line_length = max_line_length
        self.logger = logger or logging.getLogger(__name__)

    def resize_segments(self, segments: List[LyricsSegment]) -> List[LyricsSegment]:
        """Resize segments to ensure no line exceeds maximum length while preserving timing.

        Args:
            segments: List of LyricsSegment objects to resize

        Returns:
            List of resized LyricsSegment objects
        """
        self.logger.info("Resizing segments to match maximum line length")
        resized_segments: List[LyricsSegment] = []

        for segment in segments:
            if len(segment.text) <= self.max_line_length:
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
                        text=line.strip(), words=line_words, start_time=line_words[0].start_time, end_time=line_words[-1].end_time
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
            if len(remaining_text) <= self.max_line_length:
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
                    if len(paren_content) > self.max_line_length:
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
        """Find the best split point in a line based on natural language breaks.

        Prioritizes:
        1. Sentence endings (. ! ?)
        2. Clause breaks (,)
        3. Natural phrase breaks (and, but, or, -, ;)
        4. Last space before max_line_length
        5. Hard break at max_line_length if no better option

        Args:
            line: Text line to analyze

        Returns:
            Index where line should be split
        """
        # Don't split very short lines
        if len(line) <= self.max_line_length:
            return len(line)

        # Check for natural break points near the middle
        mid_point = len(line) // 2

        # Look for sentence endings first
        for punct in [". ", "! ", "? "]:
            if punct in line:
                punct_indices = [i + len(punct) - 1 for i in range(len(line)) if line[i : i + len(punct)] == punct]
                for index in sorted(punct_indices, key=lambda x: abs(x - mid_point)):
                    if len(line[:index].strip()) <= self.max_line_length:
                        return index

        # Then look for clause breaks
        if ", " in line:
            comma_indices = [i + 1 for i in range(len(line)) if line[i : i + 2] == ", "]
            for index in sorted(comma_indices, key=lambda x: abs(x - mid_point)):
                if len(line[:index].strip()) <= self.max_line_length:
                    return index

        # Then try natural phrase breaks
        for phrase in [" and ", " but ", " or ", " - ", "; "]:
            if phrase in line:
                phrase_indices = [m.start() + len(phrase) for m in re.finditer(phrase, line)]
                for index in sorted(phrase_indices, key=lambda x: abs(x - mid_point)):
                    if len(line[:index].strip()) <= self.max_line_length:
                        return index

        # Fall back to splitting at the last space before max_line_length
        last_space = line.rfind(" ", 0, self.max_line_length)
        if last_space != -1:
            return last_space

        return self.max_line_length

    def _find_matching_paren(self, line: str, start_index: int) -> int:
        """Find the index of the matching closing parenthesis.

        Args:
            line: Text to search
            start_index: Index of opening parenthesis

        Returns:
            Index of matching closing parenthesis, or -1 if not found
        """
        stack = 0
        for i in range(start_index, len(line)):
            if line[i] == "(":
                stack += 1
            elif line[i] == ")":
                stack -= 1
                if stack == 0:
                    return i
        return -1

    def _split_line(self, line: str) -> List[str]:
        """Split a line into multiple lines if it exceeds the maximum length.

        Args:
            line: Text line to split

        Returns:
            List of split lines
        """
        if len(line) <= self.max_line_length:
            return [line]

        split_lines = []
        while len(line) > self.max_line_length:
            split_point = self._find_best_split_point(line)
            split_lines.append(line[:split_point].strip())
            line = line[split_point:].strip()

        if line:
            split_lines.append(line)

        return split_lines
