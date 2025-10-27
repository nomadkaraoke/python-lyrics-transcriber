#!/usr/bin/env python3
"""
Dump gaps from Time-Bomb.flac for manual review.

This is a quick-and-dirty script that runs the correction workflow
up to the point where gaps are identified, then dumps them to a file.

Usage:
    python scripts/dump_gaps.py
"""

import sys
import os
from pathlib import Path

# Ensure we can import from parent
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from lyrics_transcriber.cli.cli_main import main as cli_main

# Monkey-patch to intercept gaps
_gaps_data = []

def dump_gaps_and_exit():
    """Called by the monkey-patch to dump gaps."""
    output_file = Path("gaps_review.yaml")
    print(f"\n📝 Writing {len(_gaps_data)} gaps to: {output_file}")
    
    with open(output_file, 'w') as f:
        f.write("# Gap Review for Time-Bomb.flac\n")
        f.write(f"# Total gaps: {len(_gaps_data)}\n")
        f.write("#\n")
        f.write("# For each gap, fill in the annotations section with your decision.\n")
        f.write("#\n")
        f.write("# Action types:\n")
        f.write("#   NO_ACTION - Gap is fine, no correction needed\n")
        f.write("#   REPLACE - Replace specific word(s) with new text\n")
        f.write("#   DELETE - Remove word(s)\n")
        f.write("#   INSERT - Add missing word(s) after a position\n")
        f.write("#   MERGE - Combine multiple words into one\n")
        f.write("#   SPLIT - Split one word into multiple\n")
        f.write("#\n\n")
        
        yaml.dump(
            {"gaps": _gaps_data},
            f,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
            sort_keys=False
        )
    
    print(f"✅ Done! Review the file and annotate each gap.")
    sys.exit(0)

# Install the monkey-patch
from lyrics_transcriber.correction import corrector as corrector_module

_original_correct_gaps = corrector_module.LyricsCorrector._correct_gaps_two_pass

def _intercepting_correct_gaps(self, gap_sequences, segments, metadata=None):
    """Intercept and dump gaps."""
    global _gaps_data
    
    # Build word map
    word_map = {w.id: w for s in segments for w in s.words}
    for source, lyrics_data in self.reference_lyrics.items():
        if lyrics_data:
            for segment in lyrics_data.segments:
                for word in segment.words:
                    if word.id not in word_map:
                        word_map[word.id] = word
    
    # Extract gaps
    for i, gap in enumerate(gap_sequences, 1):
        gap_words = []
        for word_id in gap.transcribed_word_ids:
            if word_id in word_map:
                word = word_map[word_id]
                gap_words.append({
                    "id": word_id,
                    "text": word.text,
                    "start_time": round(getattr(word, 'start_time', 0), 3),
                    "end_time": round(getattr(word, 'end_time', 0), 3)
                })
        
        # Get reference context
        ref_context = ""
        for source, lyrics_data in self.reference_lyrics.items():
            if lyrics_data and lyrics_data.segments:
                ref_words = []
                for seg in lyrics_data.segments[:20]:
                    ref_words.extend([w.text for w in seg.words])
                ref_context = " ".join(ref_words[:150])
                break
        
        gap_text = " ".join([w["text"] for w in gap_words])
        
        _gaps_data.append({
            "gap_id": i,
            "position": gap.transcription_position,
            "gap_text": gap_text,
            "transcribed_words": gap_words,
            "reference_context": ref_context,
            "word_count": len(gap_words),
            "duration_seconds": round(
                gap_words[-1]["end_time"] - gap_words[0]["start_time"], 2
            ) if len(gap_words) > 1 else 0,
            "annotations": {
                "your_decision": "# Describe what should happen",
                "action_type": "# NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT",
                "target_word_ids": "# e.g., ['w7', 'w8']",
                "replacement_text": "# New text if applicable",
                "notes": "# Any additional context"
            }
        })
    
    dump_gaps_and_exit()

corrector_module.LyricsCorrector._correct_gaps_two_pass = _intercepting_correct_gaps

# Run the CLI with Time-Bomb.flac
print("🎯 Extracting gaps from Time-Bomb.flac...")
print("   (Running correction workflow up to gap identification)")
print()

os.environ["USE_AGENTIC_AI"] = "0"  # Disable agentic to avoid actual corrections

sys.argv = [
    "lyrics-transcriber",
    "Time-Bomb.flac",
    "--output-format", "lrc"  # Minimal output
]

try:
    cli_main()
except SystemExit:
    pass  # Expected from our dump_gaps_and_exit()

