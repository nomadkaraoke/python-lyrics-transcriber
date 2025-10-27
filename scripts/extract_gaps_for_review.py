#!/usr/bin/env python3
"""
Extract gap data from a lyrics correction session for manual review and annotation.

This script runs the correction process up to the point where gaps are identified,
then dumps all gap information to a YAML file for human review.

Usage:
    python scripts/extract_gaps_for_review.py <audio_file> [--output gaps_review.yaml]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lyrics_transcriber.correction.anchor_sequence import AnchorSequenceFinder
from lyrics_transcriber.correction.corrector import LyricsCorrector
from lyrics_transcriber.types import LyricsData, GapSequence, Word
from lyrics_transcriber.lyrics.genius import GeniusLyricsProvider
from lyrics_transcriber.lyrics.spotify import SpotifyLyricsProvider
from lyrics_transcriber.lyrics.lrclib import LRCLibLyricsProvider


def extract_gap_data(
    transcribed_segments: List[Any],
    gap_sequences: List[GapSequence],
    word_map: Dict[str, Word],
    reference_lyrics: Dict[str, LyricsData]
) -> List[Dict[str, Any]]:
    """Extract structured gap data for review."""
    gaps_data = []
    
    for i, gap in enumerate(gap_sequences, 1):
        # Get transcribed words in this gap
        gap_words = []
        for word_id in gap.transcribed_word_ids:
            if word_id in word_map:
                word = word_map[word_id]
                gap_words.append({
                    "id": word_id,
                    "text": word.text,
                    "start_time": word.start_time,
                    "end_time": word.end_time
                })
        
        # Get reference context (use first available source)
        ref_context = ""
        for source, lyrics_data in reference_lyrics.items():
            if lyrics_data and lyrics_data.segments:
                # Find nearby reference text
                ref_words = []
                for seg in lyrics_data.segments[:10]:  # First few segments for context
                    ref_words.extend([w.text for w in seg.words])
                ref_context = " ".join(ref_words[:50])  # First 50 words
                break
        
        # Extract the gap text
        gap_text = " ".join([w["text"] for w in gap_words])
        
        gap_data = {
            "gap_id": i,
            "position": gap.transcription_position,
            "transcribed_words": gap_words,
            "gap_text": gap_text,
            "reference_context": ref_context,
            "word_count": len(gap_words),
            "duration_seconds": gap_words[-1]["end_time"] - gap_words[0]["start_time"] if gap_words else 0,
            "your_decision": "# What should happen with this gap?\n# Options:\n#   NO_ACTION - gap is fine as-is\n#   REPLACE <word_id> '<old>' -> '<new>' - replace specific word\n#   DELETE <word_id> - remove word\n#   INSERT_AFTER <word_id> '<text>' - add missing word\n#   MERGE <word_id1> <word_id2> -> '<text>' - combine words\n#   SPLIT <word_id> -> '<text1>' '<text2>' - split word\n# Write your decision below:\n"
        }
        
        gaps_data.append(gap_data)
    
    return gaps_data


def main():
    parser = argparse.ArgumentParser(
        description="Extract gap data for manual review and annotation"
    )
    parser.add_argument(
        "audio_file",
        help="Path to audio file (must have corresponding .lrc file)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="gaps_review.yaml",
        help="Output YAML file (default: gaps_review.yaml)"
    )
    parser.add_argument(
        "--cache-dir",
        default="./cache",
        help="Cache directory for anchor sequences"
    )
    
    args = parser.parse_args()
    
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        return 1
    
    # Look for corresponding .lrc file
    lrc_path = audio_path.with_suffix(".lrc")
    if not lrc_path.exists():
        print(f"Error: No .lrc file found: {lrc_path}")
        print("Please run transcription first to generate the .lrc file")
        return 1
    
    print(f"Loading transcription from: {lrc_path}")
    
    # Parse the LRC file to get transcribed segments
    from lyrics_transcriber.output.lyrics_file import parse_lrc_file
    transcribed_segments = parse_lrc_file(lrc_path)
    
    print(f"Found {len(transcribed_segments)} transcribed segments")
    
    # Get reference lyrics from multiple sources
    print("Fetching reference lyrics...")
    reference_lyrics = {}
    
    # Try to extract song info from filename or path
    # This is a simple heuristic - adjust as needed
    filename = audio_path.stem
    parts = filename.replace("_", " ").replace("-", " ").split()
    
    # For Time-Bomb.flac, we'll need proper artist/title
    # You may need to adjust this or pass as arguments
    artist = "Rancid"  # Hardcoded for now
    title = filename.replace("_", " ").replace("-", " ")
    
    print(f"Searching for: {artist} - {title}")
    
    # Try LRCLib first (usually has good data)
    try:
        lrclib = LRCLibLyricsProvider()
        lrclib_data = lrclib.get_lyrics(title, artist, None)
        if lrclib_data:
            reference_lyrics["lrclib"] = lrclib_data
            print("✓ Found lyrics from LRCLib")
    except Exception as e:
        print(f"✗ LRCLib failed: {e}")
    
    # Try Genius
    try:
        genius = GeniusLyricsProvider()
        genius_data = genius.get_lyrics(title, artist, None)
        if genius_data:
            reference_lyrics["genius"] = genius_data
            print("✓ Found lyrics from Genius")
    except Exception as e:
        print(f"✗ Genius failed: {e}")
    
    if not reference_lyrics:
        print("Warning: No reference lyrics found. Output will have empty context.")
    
    # Find anchor sequences (this identifies the gaps)
    print("Finding anchor sequences and gaps...")
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(exist_ok=True)
    
    finder = AnchorSequenceFinder(cache_dir=cache_dir)
    
    # Create word map
    word_map = {w.id: w for s in transcribed_segments for w in s.words}
    
    # Add reference words
    for source, lyrics_data in reference_lyrics.items():
        if lyrics_data:
            for segment in lyrics_data.segments:
                for word in segment.words:
                    if word.id not in word_map:
                        word_map[word.id] = word
    
    # Build transcribed text for anchor finding
    transcribed_text = " ".join([w.text for s in transcribed_segments for w in s.words])
    
    # Find anchors and gaps
    anchor_sequences = finder.find_anchors(
        transcribed_segments=transcribed_segments,
        reference_lyrics=reference_lyrics
    )
    
    if not anchor_sequences:
        print("Error: No anchor sequences found. Cannot identify gaps.")
        return 1
    
    print(f"Found {len(anchor_sequences)} anchor sequences")
    
    # Extract gaps from anchor sequences
    from lyrics_transcriber.correction.corrector import LyricsCorrector
    
    # Get gaps (we'll use the corrector's logic but not run corrections)
    corrector = LyricsCorrector(
        cache_dir=cache_dir,
        anchor_finder=finder
    )
    corrector._anchor_sequences = anchor_sequences
    corrector.reference_lyrics = reference_lyrics
    
    # Build gap sequences from anchors
    gap_sequences = []
    for anchor in anchor_sequences:
        if hasattr(anchor, 'gap_sequences'):
            gap_sequences.extend(anchor.gap_sequences)
    
    print(f"Found {len(gap_sequences)} gaps")
    
    if not gap_sequences:
        print("No gaps found - lyrics may already be perfectly aligned!")
        return 0
    
    # Extract gap data
    gaps_data = extract_gap_data(
        transcribed_segments=transcribed_segments,
        gap_sequences=gap_sequences,
        word_map=word_map,
        reference_lyrics=reference_lyrics
    )
    
    # Write to YAML file
    output_path = Path(args.output)
    print(f"\nWriting {len(gaps_data)} gaps to: {output_path}")
    
    import yaml
    
    with open(output_path, 'w') as f:
        f.write(f"# Gap Review for: {audio_path.name}\n")
        f.write(f"# Total gaps: {len(gaps_data)}\n")
        f.write(f"# Please review each gap and provide your decision\n")
        f.write(f"#\n")
        f.write(f"# After reviewing, this file will be used to:\n")
        f.write(f"# 1. Refine the agentic AI prompt\n")
        f.write(f"# 2. Update the adapter to handle proper word IDs\n")
        f.write(f"# 3. Improve the correction workflow\n")
        f.write(f"\n")
        yaml.dump({"gaps": gaps_data}, f, default_flow_style=False, allow_unicode=True, width=120)
    
    print(f"✓ Done! Review the gaps in: {output_path}")
    print(f"\nNext steps:")
    print(f"1. Open {output_path} in your editor")
    print(f"2. For each gap, fill in the 'your_decision' field")
    print(f"3. Share the annotated file so we can refine the agentic workflow")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

