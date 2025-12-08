"""Tests for the countdown processor module."""

import logging
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from copy import deepcopy

from lyrics_transcriber.output.countdown_processor import CountdownProcessor
from lyrics_transcriber.types import CorrectionResult, LyricsSegment, Word, LyricsData
from tests.test_helpers import create_test_word, create_test_segment, create_test_lyrics_data


class TestCountdownProcessor:
    """Test suite for CountdownProcessor class."""

    @pytest.fixture
    def cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_countdown_cache_")
        yield temp_dir
        # Cleanup is handled by OS tmpdir cleanup

    @pytest.fixture
    def processor(self, cache_dir):
        """Create a CountdownProcessor instance for testing."""
        return CountdownProcessor(
            cache_dir=cache_dir,
            logger=logging.getLogger(__name__)
        )

    @pytest.fixture
    def early_start_correction_result(self):
        """
        Create a CorrectionResult with first word starting within 3 seconds.
        This should trigger countdown processing.
        """
        # Create segments where first word starts at 1.5 seconds
        segment1 = create_test_segment(
            text="Hello world",
            words=[
                create_test_word(text="Hello", start_time=1.5, end_time=2.0),
                create_test_word(text="world", start_time=2.1, end_time=2.5),
            ],
            start_time=1.5,
            end_time=2.5,
        )
        
        segment2 = create_test_segment(
            text="This is a test",
            words=[
                create_test_word(text="This", start_time=3.0, end_time=3.5),
                create_test_word(text="is", start_time=3.6, end_time=3.8),
                create_test_word(text="a", start_time=3.9, end_time=4.0),
                create_test_word(text="test", start_time=4.1, end_time=4.5),
            ],
            start_time=3.0,
            end_time=4.5,
        )

        return CorrectionResult(
            original_segments=[segment1, segment2],
            corrected_segments=[segment1, segment2],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )

    @pytest.fixture
    def late_start_correction_result(self):
        """
        Create a CorrectionResult with first word starting after 3 seconds.
        This should NOT trigger countdown processing.
        """
        # Create segments where first word starts at 5.0 seconds
        segment1 = create_test_segment(
            text="Hello world",
            words=[
                create_test_word(text="Hello", start_time=5.0, end_time=5.5),
                create_test_word(text="world", start_time=5.6, end_time=6.0),
            ],
            start_time=5.0,
            end_time=6.0,
        )

        return CorrectionResult(
            original_segments=[segment1],
            corrected_segments=[segment1],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )

    def test_needs_countdown_with_early_start(self, processor, early_start_correction_result):
        """Test that countdown is needed when first word starts early."""
        assert processor._needs_countdown(early_start_correction_result) is True

    def test_needs_countdown_with_late_start(self, processor, late_start_correction_result):
        """Test that countdown is not needed when first word starts late."""
        assert processor._needs_countdown(late_start_correction_result) is False

    def test_needs_countdown_with_empty_segments(self, processor):
        """Test that countdown is not needed with empty segments."""
        correction_result = CorrectionResult(
            original_segments=[],
            corrected_segments=[],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )
        assert processor._needs_countdown(correction_result) is False

    def test_needs_countdown_with_segments_without_words(self, processor):
        """Test that countdown is not needed when segments have no words."""
        segment_no_words = create_test_segment(
            text="",
            words=[],
            start_time=0.0,
            end_time=0.0,
        )
        
        correction_result = CorrectionResult(
            original_segments=[segment_no_words],
            corrected_segments=[segment_no_words],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )
        assert processor._needs_countdown(correction_result) is False

    def test_needs_countdown_at_threshold(self, processor):
        """Test countdown behavior at exactly the threshold (3.0 seconds)."""
        # First word at exactly 3.0 seconds should NOT trigger countdown
        segment_at_threshold = create_test_segment(
            text="Test",
            words=[
                create_test_word(text="Test", start_time=3.0, end_time=3.5),
            ],
            start_time=3.0,
            end_time=3.5,
        )
        
        correction_result = CorrectionResult(
            original_segments=[segment_at_threshold],
            corrected_segments=[segment_at_threshold],
            corrections=[],
            corrections_made=0,
            confidence=1.0,
            reference_lyrics={},
            anchor_sequences=[],
            gap_sequences=[],
            resized_segments=[],
            metadata={},
            correction_steps=[],
            word_id_map={},
            segment_id_map={},
        )
        assert processor._needs_countdown(correction_result) is False

        # First word just before 3.0 seconds should trigger countdown
        segment_before_threshold = create_test_segment(
            text="Test",
            words=[
                create_test_word(text="Test", start_time=2.99, end_time=3.5),
            ],
            start_time=2.99,
            end_time=3.5,
        )
        
        correction_result.corrected_segments = [segment_before_threshold]
        assert processor._needs_countdown(correction_result) is True

    @patch('subprocess.check_output')
    def test_create_padded_audio_success(self, mock_subprocess, processor, tmpdir):
        """Test successful creation of padded audio file."""
        # Create a test audio file
        test_audio = tmpdir.join("test_audio.flac")
        test_audio.write("fake audio content")
        
        # Mock subprocess to simulate successful ffmpeg execution
        mock_subprocess.return_value = ""
        
        # Create the expected output file (simulating ffmpeg's work)
        expected_output = os.path.join(processor.cache_dir, "test_audio_padded.flac")
        with open(expected_output, 'w') as f:
            f.write("padded audio content")
        
        padded_path = processor._create_padded_audio(str(test_audio))
        
        assert os.path.exists(padded_path)
        assert padded_path == expected_output
        assert mock_subprocess.called

    def test_create_padded_audio_file_not_found(self, processor):
        """Test that appropriate error is raised when audio file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            processor._create_padded_audio("/nonexistent/audio.flac")

    @patch('subprocess.check_output')
    def test_create_padded_audio_ffmpeg_failure(self, mock_subprocess, processor, tmpdir):
        """Test handling of ffmpeg failure."""
        test_audio = tmpdir.join("test_audio.flac")
        test_audio.write("fake audio content")
        
        # Mock subprocess to simulate ffmpeg failure
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", output="ffmpeg error"
        )
        
        with pytest.raises(RuntimeError, match="ffmpeg command failed"):
            processor._create_padded_audio(str(test_audio))

    def test_shift_segments_timestamps(self, processor):
        """Test that timestamps are correctly shifted in segments."""
        segments = [
            create_test_segment(
                text="First segment",
                words=[
                    create_test_word(text="First", start_time=1.0, end_time=1.5),
                    create_test_word(text="segment", start_time=1.6, end_time=2.0),
                ],
                start_time=1.0,
                end_time=2.0,
            ),
            create_test_segment(
                text="Second segment",
                words=[
                    create_test_word(text="Second", start_time=2.1, end_time=2.5),
                    create_test_word(text="segment", start_time=2.6, end_time=3.0),
                ],
                start_time=2.1,
                end_time=3.0,
            ),
        ]
        
        offset = 3.0
        processor._shift_segments_timestamps(segments, offset)
        
        # Check that all timestamps were shifted correctly
        assert segments[0].start_time == 4.0
        assert segments[0].end_time == 5.0
        assert segments[0].words[0].start_time == 4.0
        assert segments[0].words[0].end_time == 4.5
        assert segments[0].words[1].start_time == 4.6
        assert segments[0].words[1].end_time == 5.0
        
        assert segments[1].start_time == 5.1
        assert segments[1].end_time == 6.0
        assert segments[1].words[0].start_time == 5.1
        assert segments[1].words[0].end_time == 5.5

    def test_create_countdown_segment(self, processor):
        """Test creation of countdown segment."""
        countdown_segment = processor._create_countdown_segment()
        
        assert countdown_segment.text == "3... 2... 1..."
        assert countdown_segment.start_time == 0.1
        assert countdown_segment.end_time == 2.9
        assert len(countdown_segment.words) == 1
        assert countdown_segment.words[0].text == "3... 2... 1..."
        assert countdown_segment.words[0].start_time == 0.1
        assert countdown_segment.words[0].end_time == 2.9
        assert countdown_segment.words[0].created_during_correction is True

    def test_add_countdown_to_result(self, processor, early_start_correction_result):
        """Test adding countdown to correction result."""
        original_first_word_start = early_start_correction_result.corrected_segments[0].words[0].start_time
        
        modified_result = processor._add_countdown_to_result(early_start_correction_result)
        
        # Check that countdown segment was added at the beginning
        assert len(modified_result.corrected_segments) == len(early_start_correction_result.corrected_segments) + 1
        assert modified_result.corrected_segments[0].text == "3... 2... 1..."
        
        # Check that timestamps were shifted by 3 seconds
        new_first_sung_word_start = modified_result.corrected_segments[1].words[0].start_time
        assert new_first_sung_word_start == original_first_word_start + 3.0
        
        # Check that the countdown segment is at the beginning with correct timings
        countdown_seg = modified_result.corrected_segments[0]
        assert countdown_seg.start_time == 0.1
        assert countdown_seg.end_time == 2.9

    def test_add_countdown_to_result_with_resized_segments(self, processor, early_start_correction_result):
        """Test that countdown is also added to resized_segments if present."""
        # Add resized_segments to the correction result
        early_start_correction_result.resized_segments = deepcopy(early_start_correction_result.corrected_segments)
        
        modified_result = processor._add_countdown_to_result(early_start_correction_result)
        
        # Check that countdown was added to both corrected_segments and resized_segments
        assert len(modified_result.corrected_segments) == len(early_start_correction_result.corrected_segments) + 1
        assert len(modified_result.resized_segments) == len(early_start_correction_result.resized_segments) + 1
        assert modified_result.corrected_segments[0].text == "3... 2... 1..."
        assert modified_result.resized_segments[0].text == "3... 2... 1..."

    def test_add_countdown_preserves_original(self, processor, early_start_correction_result):
        """Test that adding countdown doesn't modify the original result."""
        original_segment_count = len(early_start_correction_result.corrected_segments)
        original_first_start = early_start_correction_result.corrected_segments[0].start_time
        
        # Process the result
        modified_result = processor._add_countdown_to_result(early_start_correction_result)
        
        # Original should be unchanged (due to deepcopy)
        assert len(early_start_correction_result.corrected_segments) == original_segment_count
        assert early_start_correction_result.corrected_segments[0].start_time == original_first_start
        
        # Modified should have changes
        assert len(modified_result.corrected_segments) == original_segment_count + 1
        assert modified_result.corrected_segments[1].start_time == original_first_start + 3.0

    @patch.object(CountdownProcessor, '_create_padded_audio')
    @patch.object(CountdownProcessor, '_needs_countdown')
    def test_process_with_countdown_needed(
        self, mock_needs_countdown, mock_create_padded_audio, processor, early_start_correction_result, tmpdir
    ):
        """Test full process method when countdown is needed."""
        # Setup mocks
        mock_needs_countdown.return_value = True
        test_audio = tmpdir.join("test_audio.flac")
        test_audio.write("fake audio")
        padded_audio = tmpdir.join("test_audio_padded.flac")
        padded_audio.write("padded audio")
        mock_create_padded_audio.return_value = str(padded_audio)
        
        original_first_start = early_start_correction_result.corrected_segments[0].start_time
        
        # Process
        result_data, result_audio, padding_added, padding_seconds = processor.process(
            correction_result=early_start_correction_result,
            audio_filepath=str(test_audio)
        )
        
        # Verify countdown was added
        assert result_data.corrected_segments[0].text == "3... 2... 1..."
        assert result_data.corrected_segments[1].start_time == original_first_start + 3.0
        assert result_audio == str(padded_audio)
        assert padding_added is True
        assert padding_seconds == 3.0
        
        # Verify mocks were called
        assert mock_needs_countdown.called
        assert mock_create_padded_audio.called

    @patch.object(CountdownProcessor, '_needs_countdown')
    def test_process_without_countdown_needed(
        self, mock_needs_countdown, processor, late_start_correction_result, tmpdir
    ):
        """Test full process method when countdown is not needed."""
        # Setup mocks
        mock_needs_countdown.return_value = False
        test_audio = tmpdir.join("test_audio.flac")
        test_audio.write("fake audio")
        
        original_segment_count = len(late_start_correction_result.corrected_segments)
        original_first_start = late_start_correction_result.corrected_segments[0].start_time
        
        # Process
        result_data, result_audio, padding_added, padding_seconds = processor.process(
            correction_result=late_start_correction_result,
            audio_filepath=str(test_audio)
        )
        
        # Verify nothing was changed
        assert len(result_data.corrected_segments) == original_segment_count
        assert result_data.corrected_segments[0].start_time == original_first_start
        assert result_audio == str(test_audio)
        assert padding_added is False
        assert padding_seconds == 0.0
        
        # Verify mock was called
        assert mock_needs_countdown.called

    def test_countdown_configuration_constants(self, processor):
        """Test that configuration constants are set correctly."""
        assert processor.COUNTDOWN_THRESHOLD_SECONDS == 3.0
        assert processor.COUNTDOWN_PADDING_SECONDS == 3.0
        assert processor.COUNTDOWN_START_TIME == 0.1
        assert processor.COUNTDOWN_END_TIME == 2.9
        assert processor.COUNTDOWN_TEXT == "3... 2... 1..."

    def test_cache_dir_creation(self, tmpdir):
        """Test that cache directory is created if it doesn't exist."""
        nonexistent_cache = os.path.join(str(tmpdir), "nonexistent_cache")
        assert not os.path.exists(nonexistent_cache)
        
        processor = CountdownProcessor(
            cache_dir=nonexistent_cache,
            logger=logging.getLogger(__name__)
        )
        
        assert os.path.exists(nonexistent_cache)

