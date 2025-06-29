"""Test helper utilities for creating test data with the new ID-based API system."""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from lyrics_transcriber.types import (
    Word, 
    LyricsSegment, 
    GapSequence, 
    AnchorSequence,
    LyricsData,
    LyricsMetadata,
    TranscriptionData,
    TranscriptionResult,
    WordCorrection
)
from lyrics_transcriber.core.config import OutputConfig
import tempfile
import json
import os
from lyrics_transcriber.utils.word_utils import WordUtils


def create_test_word(
    word_id: Optional[str] = None,
    text: str = "test",
    start_time: float = 0.0,
    end_time: float = 1.0,
    confidence: Optional[float] = None,
    created_during_correction: bool = False
) -> Word:
    """Create a test Word object with the new API structure."""
    return Word(
        id=word_id or WordUtils.generate_id(),
        text=text,
        start_time=start_time,
        end_time=end_time,
        confidence=confidence,
        created_during_correction=created_during_correction
    )


def create_test_segment(
    segment_id: Optional[str] = None,
    text: str = "test segment",
    words: Optional[List[Word]] = None,
    start_time: float = 0.0,
    end_time: float = 2.0
) -> LyricsSegment:
    """Create a test LyricsSegment object."""
    if words is None:
        words = [create_test_word(text=word) for word in text.split()]
    
    return LyricsSegment(
        id=segment_id or WordUtils.generate_id(),
        text=text,
        words=words,
        start_time=start_time,
        end_time=end_time
    )


def create_word_map(words: List[Word]) -> Dict[str, Word]:
    """Create a word map from a list of Word objects for ID resolution."""
    return {word.id: word for word in words}


def create_test_gap_sequence(
    gap_id: Optional[str] = None,
    word_texts: List[str] = None,
    reference_words: Optional[Dict[str, List[str]]] = None,
    transcription_position: int = 0,
    preceding_anchor_id: Optional[str] = None,
    following_anchor_id: Optional[str] = None
) -> Tuple[GapSequence, Dict[str, Word]]:
    """
    Create a test GapSequence with proper ID-based structure.
    
    Returns:
        Tuple of (GapSequence, word_map) where word_map contains the actual Word objects
    """
    if word_texts is None:
        word_texts = ["hello", "world"]
    
    if reference_words is None:
        reference_words = {"genius": word_texts.copy()}
        
    # Create transcribed words
    transcribed_words = []
    for i, text in enumerate(word_texts):
        word = create_test_word(
            text=text,
            start_time=float(i),
            end_time=float(i + 1)
        )
        transcribed_words.append(word)
    
    # Create a text-to-word mapping to ensure same text gets same word ID
    text_to_word = {}
    all_words = transcribed_words.copy()
    
    # First pass: collect all unique text values
    for ref_texts in reference_words.values():
        for text in ref_texts:
            if text not in text_to_word:
                ref_word = create_test_word(text=text)
                text_to_word[text] = ref_word
                all_words.append(ref_word)
    
    # Create reference words for each source using shared word objects
    reference_word_ids = {}
    for source, ref_texts in reference_words.items():
        ref_word_ids = []
        for text in ref_texts:
            ref_word_ids.append(text_to_word[text].id)
        reference_word_ids[source] = ref_word_ids
    
    # Create word map
    word_map = create_word_map(all_words)
    
    # Create GapSequence
    gap = GapSequence(
        id=gap_id or WordUtils.generate_id(),
        transcribed_word_ids=[w.id for w in transcribed_words],
        transcription_position=transcription_position,
        preceding_anchor_id=preceding_anchor_id,
        following_anchor_id=following_anchor_id,
        reference_word_ids=reference_word_ids
    )
    
    return gap, word_map


def create_test_anchor_sequence(
    anchor_id: Optional[str] = None,
    word_texts: List[str] = None,
    reference_positions: Optional[Dict[str, int]] = None,
    reference_words: Optional[Dict[str, List[str]]] = None,
    transcription_position: int = 0,
    confidence: float = 1.0
) -> Tuple[AnchorSequence, Dict[str, Word]]:
    """
    Create a test AnchorSequence with proper ID-based structure.
    
    Returns:
        Tuple of (AnchorSequence, word_map) where word_map contains the actual Word objects
    """
    if word_texts is None:
        word_texts = ["anchor", "words"]
        
    if reference_positions is None:
        reference_positions = {"genius": 0, "spotify": 0}
        
    if reference_words is None:
        reference_words = {"genius": word_texts.copy(), "spotify": word_texts.copy()}
    
    # Create transcribed words
    transcribed_words = []
    for i, text in enumerate(word_texts):
        word = create_test_word(
            text=text,
            start_time=float(i),
            end_time=float(i + 1)
        )
        transcribed_words.append(word)
    
    # Create reference words for each source
    reference_word_ids = {}
    all_words = transcribed_words.copy()
    
    for source, ref_texts in reference_words.items():
        ref_word_ids = []
        for text in ref_texts:
            ref_word = create_test_word(text=text)
            ref_word_ids.append(ref_word.id)
            all_words.append(ref_word)
        reference_word_ids[source] = ref_word_ids
    
    # Create word map
    word_map = create_word_map(all_words)
    
    # Create AnchorSequence
    anchor = AnchorSequence(
        id=anchor_id or WordUtils.generate_id(),
        transcribed_word_ids=[w.id for w in transcribed_words],
        transcription_position=transcription_position,
        reference_positions=reference_positions,
        reference_word_ids=reference_word_ids,
        confidence=confidence
    )
    
    return anchor, word_map


def create_test_lyrics_data(
    segments: Optional[List[LyricsSegment]] = None,
    source: str = "test",
    track_name: str = "Test Track",
    artist_names: str = "Test Artist"
) -> LyricsData:
    """Create test LyricsData object."""
    if segments is None:
        segments = [
            create_test_segment("Hello world", start_time=0.0, end_time=2.0),
            create_test_segment("This is a test", start_time=2.0, end_time=4.0)
        ]
    
    metadata = LyricsMetadata(
        source=source,
        track_name=track_name,
        artist_names=artist_names,
        is_synced=True
    )
    
    return LyricsData(
        segments=segments,
        metadata=metadata,
        source=source
    )


def create_test_transcription_data(
    segments: Optional[List[LyricsSegment]] = None,
    source: str = "test_transcriber",
    text: Optional[str] = None
) -> TranscriptionData:
    """Create test TranscriptionData object."""
    if segments is None:
        segments = [
            create_test_segment("Hello world", start_time=0.0, end_time=2.0),
            create_test_segment("This is a test", start_time=2.0, end_time=4.0)
        ]
    
    # Extract all words from segments
    all_words = []
    for segment in segments:
        all_words.extend(segment.words)
    
    if text is None:
        text = " ".join(segment.text for segment in segments)
    
    return TranscriptionData(
        segments=segments,
        words=all_words,
        text=text,
        source=source
    )


def create_test_transcription_result(
    name: str = "test_transcriber",
    priority: int = 1,
    transcription_data: Optional[TranscriptionData] = None
) -> TranscriptionResult:
    """Create test TranscriptionResult object."""
    if transcription_data is None:
        transcription_data = create_test_transcription_data(source=name)
    
    return TranscriptionResult(
        name=name,
        priority=priority,
        result=transcription_data
    )


def create_test_correction(
    original_word: str = "test",
    corrected_word: str = "corrected",
    original_position: int = 0,
    source: str = "test",
    reason: str = "test correction",
    confidence: float = 1.0,
    word_id: Optional[str] = None,
    corrected_word_id: Optional[str] = None
) -> WordCorrection:
    """Create test WordCorrection object."""
    return WordCorrection(
        original_word=original_word,
        corrected_word=corrected_word,
        original_position=original_position,
        source=source,
        reason=reason,
        confidence=confidence,
        word_id=word_id,
        corrected_word_id=corrected_word_id
    )


def create_handler_test_data(
    gap_word_texts: List[str] = None, 
    reference_words: Optional[Dict[str, List[str]]] = None
) -> Tuple[GapSequence, Dict[str, Word], Dict[str, Any]]:
    """
    Create test data for correction handlers.
    
    Returns:
        Tuple of (gap_sequence, word_map, handler_data) ready for handler testing
    """
    gap, word_map = create_test_gap_sequence(
        word_texts=gap_word_texts,
        reference_words=reference_words
    )
    
    # Create handler data structure that handlers expect
    handler_data = {
        "word_map": word_map
    }
    
    return gap, word_map, handler_data


def create_test_output_config(
    output_dir: Optional[str] = None,
    cache_dir: Optional[str] = None,
    output_styles_json: Optional[str] = None,
    render_video: bool = False,
    generate_cdg: bool = False,
    enable_review: bool = False
) -> OutputConfig:
    """
    Create a test OutputConfig with temporary directories and styles file.
    
    Returns:
        OutputConfig instance ready for testing
    """
    # Create temporary directories if not provided
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="test_output_")
    
    if cache_dir is None:
        cache_dir = tempfile.mkdtemp(prefix="test_cache_")
    
    # Create temporary styles file if not provided
    if output_styles_json is None:
        temp_styles = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # Create minimal styles JSON for testing
        test_styles = {
            "karaoke": {
                "font_size": 40,
                "font_family": "Arial"
            },
            "cdg": {
                "background_color": "#000000",
                "text_color": "#FFFFFF"
            }
        }
        
        json.dump(test_styles, temp_styles)
        temp_styles.close()
        output_styles_json = temp_styles.name
    
    return OutputConfig(
        output_styles_json=output_styles_json,
        output_dir=output_dir,
        cache_dir=cache_dir,
        max_line_length=36,
        video_resolution="360p",
        render_video=render_video,
        generate_cdg=generate_cdg,
        enable_review=enable_review
    )


def create_test_lyrics_data_from_text(
    text: str,
    source: str = "test",
    track_name: str = "Test Track",
    artist_names: str = "Test Artist"
) -> LyricsData:
    """Create test LyricsData object from a plain text string, handling line breaks as separate segments."""
    lines = text.split('\n')
    segments = []
    current_time = 0.0
    
    for i, line in enumerate(lines):
        if line.strip():  # Skip empty lines
            words = []
            word_texts = line.strip().split()
            segment_duration = 2.0  # 2 seconds per segment
            word_duration = segment_duration / len(word_texts) if word_texts else segment_duration
            
            for j, word_text in enumerate(word_texts):
                word_start = current_time + (j * word_duration)
                word_end = current_time + ((j + 1) * word_duration)
                word = create_test_word(
                    text=word_text,
                    start_time=word_start,
                    end_time=word_end
                )
                words.append(word)
            
            segment = create_test_segment(
                text=line.strip(),
                words=words,
                start_time=current_time,
                end_time=current_time + segment_duration
            )
            segments.append(segment)
            current_time += segment_duration
    
    metadata = LyricsMetadata(
        source=source,
        track_name=track_name,
        artist_names=artist_names,
        is_synced=True
    )
    
    return LyricsData(
        segments=segments,
        metadata=metadata,
        source=source
    )


def create_test_transcription_result_from_text(
    text: str,
    name: str = "test_transcriber"
) -> TranscriptionResult:
    """Create test TranscriptionResult object from a plain text string."""
    lines = text.split('\n')
    segments = []
    all_words = []
    current_time = 0.0
    
    for i, line in enumerate(lines):
        if line.strip():  # Skip empty lines
            words = []
            word_texts = line.strip().split()
            segment_duration = 2.0  # 2 seconds per segment
            word_duration = segment_duration / len(word_texts) if word_texts else segment_duration
            
            for j, word_text in enumerate(word_texts):
                word_start = current_time + (j * word_duration)
                word_end = current_time + ((j + 1) * word_duration)
                word = create_test_word(
                    text=word_text,
                    start_time=word_start,
                    end_time=word_end
                )
                words.append(word)
                all_words.append(word)
            
            segment = create_test_segment(
                text=line.strip(),
                words=words,
                start_time=current_time,
                end_time=current_time + segment_duration
            )
            segments.append(segment)
            current_time += segment_duration
    
    transcription_data = TranscriptionData(
        segments=segments,
        words=all_words,
        text=text,
        source=name
    )
    
    return TranscriptionResult(
        name=name,
        priority=1,
        result=transcription_data
    )


def convert_references_to_lyrics_data(references: Dict[str, str]) -> Dict[str, LyricsData]:
    """Convert a dictionary of source->text references to source->LyricsData objects."""
    return {
        source: create_test_lyrics_data_from_text(text, source=source)
        for source, text in references.items()
    } 