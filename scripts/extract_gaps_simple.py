#!/usr/bin/env python3
"""
Simple gap extraction script that intercepts the correction process.

This modifies the corrector temporarily to dump gap data before processing.

Usage:
    python scripts/extract_gaps_simple.py
    
This will run your most recent correction command and dump gaps to gaps_review.yaml
"""

import sys
import os
from pathlib import Path
import json

# Set environment to enable agentic but with our interceptor
os.environ["USE_AGENTIC_AI"] = "1"
os.environ["EXTRACT_GAPS_MODE"] = "1"  # Flag for our modifications

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Monkey-patch the corrector to dump gaps before processing
from lyrics_transcriber.correction import corrector as corrector_module

_original_correct_gaps = corrector_module.LyricsCorrector._correct_gaps_two_pass

gaps_collected = []

def _intercepting_correct_gaps(self, gap_sequences, segments, metadata=None):
    """Intercept gaps and dump them before processing."""
    import yaml
    
    print(f"\n🔍 INTERCEPTING {len(gap_sequences)} gaps for extraction...")
    
    # Build word map
    word_map = {w.id: w for s in segments for w in s.words}
    for source, lyrics_data in self.reference_lyrics.items():
        if lyrics_data:
            for segment in lyrics_data.segments:
                for word in segment.words:
                    if word.id not in word_map:
                        word_map[word.id] = word
    
    # Extract gap data
    gaps_data = []
    for i, gap in enumerate(gap_sequences, 1):
        # Get gap words
        gap_words = []
        for word_id in gap.transcribed_word_ids:
            if word_id in word_map:
                word = word_map[word_id]
                gap_words.append({
                    "id": word_id,
                    "text": word.text,
                    "start_time": getattr(word, 'start_time', 0),
                    "end_time": getattr(word, 'end_time', 0)
                })
        
        # Get reference context
        ref_context = ""
        for source, lyrics_data in self.reference_lyrics.items():
            if lyrics_data and lyrics_data.segments:
                ref_words = []
                for seg in lyrics_data.segments[:15]:
                    ref_words.extend([w.text for w in seg.words])
                ref_context = " ".join(ref_words[:100])
                break
        
        gap_text = " ".join([w["text"] for w in gap_words])
        
        gap_data = {
            "gap_id": i,
            "position": gap.transcription_position,
            "transcribed_words": gap_words,
            "gap_text": gap_text,
            "reference_context": ref_context,
            "word_count": len(gap_words),
            "duration_seconds": round(
                gap_words[-1]["end_time"] - gap_words[0]["start_time"], 2
            ) if gap_words and len(gap_words) > 0 else 0,
            "annotations": {
                "your_decision": "",
                "notes": "",
                "action_type": "# Options: NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT",
                "target_word_ids": "# List word IDs to operate on",
                "replacement_text": "# New text if applicable"
            }
        }
        
        gaps_data.append(gap_data)
    
    # Write to YAML
    output_file = Path("gaps_review.yaml")
    print(f"📝 Writing gaps to: {output_file}")
    
    with open(output_file, 'w') as f:
        f.write("# Gap Review Data\n")
        f.write("# ================\n")
        f.write("#\n")
        f.write("# For each gap, please fill in the 'annotations' section:\n")
        f.write("#\n")
        f.write("# your_decision: Brief description of what should happen\n")
        f.write("# action_type: NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT\n")
        f.write("# target_word_ids: Which word(s) to operate on (use 'id' from transcribed_words)\n")
        f.write("# replacement_text: The corrected text (if applicable)\n")
        f.write("# notes: Any additional context or reasoning\n")
        f.write("#\n")
        f.write(f"# Total gaps found: {len(gaps_data)}\n")
        f.write("#\n\n")
        
        yaml.dump(
            {"gaps": gaps_data},
            f,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
            sort_keys=False
        )
    
    print(f"✅ Extracted {len(gaps_data)} gaps!")
    print(f"\n📋 Next steps:")
    print(f"   1. Open gaps_review.yaml in your editor")
    print(f"   2. Review each gap and fill in the annotations")
    print(f"   3. Share the annotated file for workflow refinement")
    print(f"\n🛑 Stopping here (not running actual corrections)")
    
    # Don't actually run corrections - just exit
    sys.exit(0)

# Apply the monkey-patch
corrector_module.LyricsCorrector._correct_gaps_two_pass = _intercepting_correct_gaps

print("🎯 Gap extraction interceptor installed!")
print("📂 Now run your lyrics-transcriber command with USE_AGENTIC_AI=1")
print("   Example: USE_AGENTIC_AI=1 poetry run lyrics-transcriber Time-Bomb.flac")
print("\nWaiting for correction process to start...")

