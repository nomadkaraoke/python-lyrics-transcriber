import logging
from typing import List

import pytest

from lyrics_transcriber.output.segment_resizer import SegmentResizer
from lyrics_transcriber.types import LyricsSegment, Word
from tests.test_helpers import create_test_word, create_test_segment


def create_word(text: str, start_time: float, end_time: float) -> Word:
    """Helper to create Word objects for testing."""
    return create_test_word(text=text, start_time=start_time, end_time=end_time)


def create_segment(text: str, words: List[Word]) -> LyricsSegment:
    """Helper to create LyricsSegment objects for testing."""
    return create_test_segment(
        text=text, words=words, start_time=words[0].start_time if words else 0, end_time=words[-1].end_time if words else 0
    )


class TestSegmentResizer:
    @pytest.fixture
    def resizer(self):
        return SegmentResizer(max_line_length=36, logger=logging.getLogger(__name__))

    def test_clean_text(self, resizer):
        """Test text cleaning functionality."""
        assert resizer._clean_text("Hello\nWorld") == "Hello World"
        assert resizer._clean_text("  Extra  Spaces  ") == "Extra Spaces"
        assert resizer._clean_text("Multiple\n\nNewlines") == "Multiple Newlines"
        assert resizer._clean_text("\nLeading\nTrailing\n") == "Leading Trailing"

    def test_create_cleaned_word(self, resizer):
        """Test word cleaning functionality."""
        word = create_word("Hello\n", 1.0, 1.5)
        cleaned = resizer._create_cleaned_word(word)

        assert cleaned.text == "Hello"
        assert cleaned.start_time == 1.0
        assert cleaned.end_time == 1.5

    def test_create_cleaned_segment(self, resizer):
        """Test segment cleaning functionality."""
        words = [create_word("Hello\n", 1.0, 1.5), create_word("World\n", 1.6, 2.0)]
        segment = create_segment("Hello\nWorld\n", words)

        cleaned = resizer._create_cleaned_segment(segment)

        assert cleaned.text == "Hello World"
        assert cleaned.start_time == 1.0
        assert cleaned.end_time == 2.0
        assert len(cleaned.words) == 2

    def test_find_break_points(self, resizer):
        """Test break point detection."""
        text = "First sentence. Second part, with a dash - and more!"
        break_points = resizer._find_break_points(text)

        # Get all break points in a flat list for easier testing
        all_points = [point for points in break_points for point in points]

        # Should find sentence breaks (after the period)
        assert 15 in all_points  # Position after "sentence" (before the space)
        # Should find comma breaks
        assert 28 in all_points  # Position after "part,"
        # Should find dash breaks
        assert 40 in all_points  # Position at the dash

    def test_find_best_split_point(self, resizer, caplog):
        """Test split point selection."""
        caplog.set_level(logging.DEBUG)

        # Test with sentence break
        text = "This is a longer sentence. And this is another one."
        split_point = resizer._find_best_split_point(text)

        # Print all captured logs
        print("\nLogs for find_best_split_point:")
        for record in caplog.records:
            print(f"{record.levelname}: {record.message}")

        # Should split at the first sentence break (including the period and space)
        assert split_point == 26  # Position after "sentence. "

        # Test with comma break in a long sentence
        text = "This is a much longer first part, and this is the second part of it"
        split_point = resizer._find_best_split_point(text)
        assert split_point == 33  # Position after "part, " (including comma and space)

        # Test with text shorter than max length
        text = "Short text"
        split_point = resizer._find_best_split_point(text)
        assert split_point == len(text)  # Should return full length if text is short enough

        # Test with very long text without natural breaks
        text = "ThisIsAVeryLongTextWithoutAnyNaturalBreakPointsInIt"
        split_point = resizer._find_best_split_point(text)
        assert split_point <= resizer.max_line_length  # Should force a break at or before max length

    def test_process_segment_text(self, resizer):
        """Test text splitting into lines."""
        text = "First sentence. Second part, third bit."
        lines = resizer._process_segment_text(text)

        assert len(lines) > 1
        assert lines[0].endswith("sentence.")
        assert all(len(line) <= resizer.max_line_length for line in lines)

    def test_find_words_for_line(self, resizer):
        """Test that _find_words_for_line correctly assigns words to lines."""
        # Create test data with exact matches
        words = [
            create_word("First", 1.0, 1.5),
            create_word("line", 1.5, 2.0),
            create_word("then", 2.0, 2.5),
            create_word("second", 2.5, 3.0),
        ]
        segment_text = "First line then second"

        # Test first line with exact text match
        line = "First line"
        line_words = resizer._find_words_for_line(
            line=line,
            line_pos=0,
            line_length=len(line),
            segment_text=segment_text,
            available_words=words.copy(),  # Use a copy to avoid modifying original
            current_pos=0,
        )

        assert len(line_words) == 2, f"Expected 2 words, got {len(line_words)}: {[w.text for w in line_words]}"
        assert [w.text for w in line_words] == ["First", "line"]
        assert line_words[0].start_time == 1.0
        assert line_words[1].end_time == 2.0

        # Test second line
        line = "then second"
        line_words = resizer._find_words_for_line(
            line=line,
            line_pos=segment_text.find(line),
            line_length=len(line),
            segment_text=segment_text,
            available_words=words[2:],  # Only pass remaining words
            current_pos=segment_text.find(line),
        )

        assert len(line_words) == 2, f"Expected 2 words, got {len(line_words)}: {[w.text for w in line_words]}"
        assert [w.text for w in line_words] == ["then", "second"]

    def test_create_line_segment(self, resizer):
        """Test creation of segments from lines."""
        words = [create_word("First", 1.0, 1.5), create_word("line", 1.6, 2.0)]
        segment = resizer._create_line_segment(0, "First line", "First line here", words, 0)

        assert segment is not None
        assert segment.text == "First line"
        assert len(segment.words) == 2
        assert segment.start_time == 1.0
        assert segment.end_time == 2.0

    def test_create_segments_from_lines(self, resizer):
        """Test creation of multiple segments from lines."""
        words = [
            create_word("First", 1.0, 1.5),
            create_word("line.", 1.6, 2.0),
            create_word("Second", 2.1, 2.5),
            create_word("line.", 2.6, 3.0),
        ]
        lines = ["First line.", "Second line."]
        segments = resizer._create_segments_from_lines("First line. Second line.", lines, words)

        assert len(segments) == 2
        assert segments[0].text == "First line."
        assert segments[1].text == "Second line."

    def test_short_segment_unchanged(self, resizer):
        """Test that segments under max length are not modified."""
        words = [create_word("Short", 1.0, 1.5), create_word("segment", 1.6, 2.0)]
        segment = create_segment("Short segment", words)

        result = resizer.resize_segments([segment])

        assert len(result) == 1
        assert result[0].text == "Short segment"
        assert len(result[0].words) == 2

    def test_long_segment_split(self, resizer):
        """Test splitting a long segment at natural break points."""
        words = [
            create_word("This", 1.0, 1.5),
            create_word("is", 1.6, 1.8),
            create_word("a", 1.9, 2.0),
            create_word("very", 2.1, 2.5),
            create_word("long", 2.6, 3.0),
            create_word("segment", 3.1, 3.5),
            create_word("that", 3.6, 3.8),
            create_word("needs", 3.9, 4.2),
            create_word("splitting", 4.3, 4.8),
        ]
        segment = create_segment("This is a very long segment that needs splitting", words)

        result = resizer.resize_segments([segment])

        assert len(result) > 1
        assert all(len(seg.text) <= resizer.max_line_length for seg in result)
        assert sum(len(seg.words) for seg in result) == len(words)

    def test_segment_with_newlines(self, resizer):
        """Test handling segments containing newline characters."""
        words = [create_word("Line\n", 1.0, 1.5), create_word("with\n", 1.6, 2.0), create_word("newlines\n", 2.1, 2.5)]
        # Note: Create segment with raw text, newlines will be stripped during processing
        segment = create_segment("Line\nwith\nnewlines\n", words)

        result = resizer.resize_segments([segment])

        assert len(result) == 1
        # The text should have newlines replaced with spaces and be stripped
        assert result[0].text == "Line with newlines"
        assert len(result[0].words) == 3
        # Verify word order is preserved
        assert [w.text.strip() for w in result[0].words] == ["Line", "with", "newlines"]

    def test_segment_with_parentheses(self, resizer):
        """Test handling segments with parenthetical content."""
        words = [
            create_word("Text", 1.0, 1.5),
            create_word("with", 1.6, 2.0),
            create_word("(parenthetical", 2.1, 2.5),
            create_word("content)", 2.6, 3.0),
        ]
        segment = create_segment("Text with (parenthetical content)", words)

        result = resizer.resize_segments([segment])

        assert any("(parenthetical content)" in seg.text for seg in result)
        assert all(len(seg.text) <= resizer.max_line_length for seg in result)

    def test_multiple_segments(self, resizer):
        """Test processing multiple segments together."""
        segments = [
            create_segment("First segment", [create_word("First", 1.0, 1.5), create_word("segment", 1.6, 2.0)]),
            create_segment(
                "Second very long segment that needs splitting",
                [
                    create_word("Second", 2.1, 2.5),
                    create_word("very", 2.6, 3.0),
                    create_word("long", 3.1, 3.5),
                    create_word("segment", 3.6, 4.0),
                    create_word("that", 4.1, 4.5),
                    create_word("needs", 4.6, 5.0),
                    create_word("splitting", 5.1, 5.5),
                ],
            ),
        ]

        result = resizer.resize_segments(segments)

        assert len(result) > len(segments)
        assert all(len(seg.text) <= resizer.max_line_length for seg in result)

    def test_natural_break_points(self, resizer):
        """Test that segments are split at natural break points."""
        words = [
            create_word("First", 1.0, 1.5),
            create_word("sentence.", 1.6, 2.0),
            create_word("Second", 2.1, 2.5),
            create_word("part,", 2.6, 3.0),
            create_word("with", 3.1, 3.5),
            create_word("comma.", 3.6, 4.0),
        ]
        segment = create_segment("First sentence. Second part, with comma.", words)

        result = resizer.resize_segments([segment])

        # Verify we get at least two segments
        assert len(result) >= 2

        # Get all segment texts
        segment_texts = [seg.text for seg in result]

        # Check that at least one segment ends with a sentence break
        assert any(text.endswith("sentence.") for text in segment_texts), f"No segment ends with 'sentence.' in {segment_texts}"

        # Check that segments maintain proper word grouping
        first_segment = next(seg for seg in result if "First" in seg.text)
        assert "First sentence" in first_segment.text

        # Verify word timing preservation
        assert all(seg.start_time == seg.words[0].start_time for seg in result)
        assert all(seg.end_time == seg.words[-1].end_time for seg in result)

    def test_word_timing_preservation(self, resizer):
        """Test that word timing information is preserved after splitting."""
        words = [
            create_word("Word1", 1.0, 1.5),
            create_word("Word2", 2.0, 2.5),
            create_word("Word3", 3.0, 3.5),
            create_word("Word4", 4.0, 4.5),
        ]
        segment = create_segment("Word1 Word2 Word3 Word4", words)

        result = resizer.resize_segments([segment])

        for seg in result:
            assert seg.start_time == seg.words[0].start_time
            assert seg.end_time == seg.words[-1].end_time

        # Check that all original words are present
        result_words = [w for seg in result for w in seg.words]
        assert len(result_words) == len(words)
        assert all(w1.start_time == w2.start_time for w1, w2 in zip(result_words, words))

    def test_empty_segment(self, resizer):
        """Test handling of empty segments."""
        segment = create_segment("", [])

        result = resizer.resize_segments([segment])

        assert len(result) == 1
        assert result[0].text == ""
        assert len(result[0].words) == 0

    def test_segment_with_punctuation(self, resizer):
        """Test handling segments with various punctuation marks."""
        words = [
            create_word("Hello,", 1.0, 1.5),
            create_word("world!", 1.6, 2.0),
            create_word("How", 2.1, 2.5),
            create_word("are", 2.6, 3.0),
            create_word("you?", 3.1, 3.5),
        ]
        segment = create_segment("Hello, world! How are you?", words)

        result = resizer.resize_segments([segment])

        assert all(len(seg.text) <= resizer.max_line_length for seg in result)
        assert sum(len(seg.words) for seg in result) == len(words)

    def test_real_world_abba_lyrics(self, resizer, caplog):
        """Test handling of real-world ABBA lyrics segments."""
        # caplog.set_level(logging.DEBUG)  # Enable debug logging

        # First segment: "My, my, at Waterloo, Napoleon did surrender"
        words1 = [
            create_word("My,", 6.52, 6.76),
            create_word("my,", 6.82, 7.24),
            create_word("at", 8.20, 8.44),
            create_word("Waterloo,", 8.44, 9.32),
            create_word("Napoleon", 9.32, 10.20),
            create_word("did", 10.20, 10.84),
            create_word("surrender", 10.84, 12.60),
        ]
        segment1 = create_segment("My, my, at Waterloo, Napoleon did surrender", words1)

        # Second segment: "Oh yeah, and I have met my destiny in quite a similar way"
        words2 = [
            create_word("Oh", 13.08, 13.48),
            create_word("yeah,", 13.48, 13.92),
            create_word("and", 14.76, 14.92),
            create_word("I", 14.92, 15.00),
            create_word("have", 15.00, 15.24),
            create_word("met", 15.24, 15.48),
            create_word("my", 15.48, 15.72),
            create_word("destiny", 15.72, 16.44),
            create_word("in", 16.44, 16.68),
            create_word("quite", 16.68, 17.16),
            create_word("a", 18.76, 18.92),
            create_word("similar", 18.92, 19.64),
            create_word("way", 19.64, 20.28),
        ]
        segment2 = create_segment("Oh yeah, and I have met my destiny in quite a similar way", words2)

        result = resizer.resize_segments([segment1, segment2])

        # Expected output segments
        expected_segments = [
            "My, my, at Waterloo,",  # 20 chars
            "Napoleon did surrender",  # 22 chars
            "Oh yeah,",  # 8 chars
            "and I have met my destiny",  # 25 chars
            "in quite a similar way",  # 22 chars
        ]

        # # Log the actual results in an easy to read format
        # print("\nActual output segments:")
        # for i, seg in enumerate(result):
        #     print(f"{i + 1}. '{seg.text}' ({len(seg.text)} chars)")
        #     print(f"   Words: {[w.text for w in seg.words]}")
        #     print(f"   Time: {seg.start_time:.2f}-{seg.end_time:.2f}")

        # print("\nExpected output segments:")
        # for i, text in enumerate(expected_segments):
        #     print(f"{i + 1}. '{text}' ({len(text)} chars)")

        # print("\nDebug logs:")
        # for record in caplog.records:
        #     print(f"{record.levelname}: {record.message}")

        # Compare input and output words
        all_input_words = words1 + words2
        result_words = [w for seg in result for w in seg.words]

        # print("\nInput words:")
        # for i, word in enumerate(all_input_words):
        #     print(f"{i + 1}. '{word.text}' ({word.start_time:.2f}-{word.end_time:.2f})")

        # print("\nOutput words:")
        # for i, word in enumerate(result_words):
        #     print(f"{i + 1}. '{word.text}' ({word.start_time:.2f}-{word.end_time:.2f})")

        # Original assertions
        assert len(result) == len(expected_segments), f"Expected {len(expected_segments)} segments, got {len(result)}"

        for i, expected_text in enumerate(expected_segments):
            assert result[i].text == expected_text, f"Segment {i} text mismatch:\nExpected: '{expected_text}'\nGot: '{result[i].text}'"
            assert (
                len(result[i].text) <= resizer.max_line_length
            ), f"Segment {i} exceeds max length: {len(result[i].text)} > {resizer.max_line_length}"

        assert len(result_words) == len(all_input_words), "Some words were lost in the splitting process"
        assert all(
            w1.start_time == w2.start_time for w1, w2 in zip(result_words, all_input_words)
        ), "Word timing information was not preserved"

        for seg in result:
            assert seg.start_time == seg.words[0].start_time, "Segment start time should match its first word"
            assert seg.end_time == seg.words[-1].end_time, "Segment end time should match its last word"

    def test_create_segments_from_lines_complex(self, resizer):
        """Test _create_segments_from_lines with complex cases."""
        # Test case with repeated words and punctuation
        words = [
            create_word("The", 1.0, 1.2),
            create_word("cat", 1.2, 1.5),
            create_word("and", 1.5, 1.7),
            create_word("the", 1.7, 1.9),  # Note: "the" appears twice
            create_word("dog", 1.9, 2.1),
            create_word("are", 2.1, 2.3),
            create_word("friends", 2.3, 2.6),
        ]
        segment_text = "The cat and the dog are friends"
        split_lines = ["The cat and", "the dog are friends"]

        segments = resizer._create_segments_from_lines(segment_text, split_lines, words)

        assert len(segments) == 2
        assert segments[0].text == "The cat and"
        assert segments[1].text == "the dog are friends"
        assert [w.text for w in segments[0].words] == ["The", "cat", "and"]
        assert [w.text for w in segments[1].words] == ["the", "dog", "are", "friends"]

        # Verify timing information is preserved
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 1.7
        assert segments[1].start_time == 1.7
        assert segments[1].end_time == 2.6

    def test_create_segments_from_lines_edge_cases(self, resizer):
        """Test edge cases for _create_segments_from_lines."""
        # Test case with words that could fit in multiple lines
        words = [
            create_word("A", 1.0, 1.1),
            create_word("test", 1.1, 1.3),
            create_word("with", 1.3, 1.5),
            create_word("a", 1.5, 1.6),  # Note: "a" appears twice
            create_word("repeated", 1.6, 1.8),
            create_word("word", 1.8, 2.0),
        ]
        segment_text = "A test with a repeated word"
        split_lines = ["A test", "with a repeated word"]

        segments = resizer._create_segments_from_lines(segment_text, split_lines, words)

        assert len(segments) == 2
        assert [w.text for w in segments[0].words] == ["A", "test"]
        assert [w.text for w in segments[1].words] == ["with", "a", "repeated", "word"]

        # Test that words maintain chronological order
        for segment in segments:
            word_times = [(w.start_time, w.end_time) for w in segment.words]
            assert word_times == sorted(word_times)  # Times should be in ascending order

    def test_word_preservation_in_segments(self, resizer):
        """Test that all words are preserved when creating segments, particularly at line boundaries."""
        words = [
            create_word("My,", 6.520263204756731, 6.760272893275383),
            create_word("my,", 6.820275315405047, 7.240292270312689),
            create_word("at", 8.2003310243873, 8.400339098152843),
            create_word("Waterloo,", 8.460341520282507, 9.640389155499214),
            create_word("Napoleon", 9.680390770252323, 10.860438405469033),
            create_word("did", 10.880439212845587, 11.340457782506338),
            create_word("surrender\n", 11.420461012012556, 12.600508647229265),  # Note the newline
        ]
        segment = create_segment("My, my, at Waterloo, Napoleon did surrender\n", words)
        
        result = resizer.resize_segments([segment])
        
        # Get all words from all result segments
        result_words = [word.text for seg in result for word in seg.words]
        input_words = [word.text for word in words]
        
        # Check that no words are lost
        assert result_words == input_words, f"""
        Words were lost or altered in the segmentation process.
        Expected: {input_words}
        Got: {result_words}
        
        Segments produced:
        {[f"'{seg.text}' -> {[w.text for w in seg.words]}" for seg in result]}
        """
        
        # Check that each segment's text contains all its words
        for seg in result:
            seg_words = [w.text for w in seg.words]
            for word in seg_words:
                # Strip newlines when checking containment since the segment text will have them removed
                word_clean = word.strip()
                assert word_clean in seg.text, f"""
                Word '{word_clean}' from segment's word list not found in segment text '{seg.text}'
                Segment words: {seg_words}
                """
