#!/usr/bin/env python3
"""
Extract gap data by inserting a hook into the correction flow.

This adds logging to capture gap data when lyrics-transcriber runs.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from lyrics_transcriber.correction import corrector

# Store gaps here
_captured_gaps = []

# Monkey-patch the logger to capture gap data
_original_process_corrections = corrector.LyricsCorrector.apply_corrections

def _capturing_apply_corrections(self, transcription_result, correction_config=None):
    """Intercept before corrections are applied."""
    global _captured_gaps
    
    # Get anchor sequences (already computed)
    if not hasattr(self, '_anchor_sequences') or not self._anchor_sequences:
        print("No anchor sequences found - running original method")
        return _original_process_corrections(self, transcription_result, correction_config)
    
    # Extract gap data from anchor sequences
    segments = transcription_result.segments
    word_map = {w.id: w for s in segments for w in s.words}
    
    # Add reference words
    for source, lyrics_data in self.reference_lyrics.items():
        if lyrics_data:
            for segment in lyrics_data.segments:
                for word in segment.words:
                    if word.id not in word_map:
                        word_map[word.id] = word
    
    # Get all gaps from all anchors
    all_gaps = []
    for anchor in self._anchor_sequences:
        if hasattr(anchor, 'gaps') and anchor.gaps:
            all_gaps.extend(anchor.gaps)
    
    if not all_gaps:
        print("No gaps found in anchor sequences")
        return _original_process_corrections(self, transcription_result, correction_config)
    
    print(f"\n🔍 Found {len(all_gaps)} gaps - extracting data...")
    
    # Extract gap details
    for i, gap in enumerate(all_gaps, 1):
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
        
        _captured_gaps.append({
            "gap_id": i,
            "position": gap.transcription_position if hasattr(gap, 'transcription_position') else i,
            "gap_text": gap_text,
            "transcribed_words": gap_words,
            "reference_context": ref_context[:300],  # Limit context length
            "word_count": len(gap_words),
            "annotations": {
                "your_decision": "",
                "action_type": "# NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT",
                "target_word_ids": [],
                "replacement_text": "",
                "notes": ""
            }
        })
    
    # Write to file
    output_file = Path("gaps_review.yaml")
    print(f"📝 Writing to: {output_file}")
    
    with open(output_file, 'w') as f:
        f.write("# Gap Review Data\n")
        f.write(f"# Total gaps: {len(_captured_gaps)}\n")
        f.write("#\n")
        f.write("# For each gap, fill in:\n")
        f.write("#   your_decision: What should happen?\n")
        f.write("#   action_type: NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT\n")
        f.write("#   target_word_ids: Which word IDs to operate on\n")
        f.write("#   replacement_text: Corrected text\n")
        f.write("#   notes: Additional context\n\n")
        
        yaml.dump(
            {"gaps": _captured_gaps},
            f,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
            sort_keys=False
        )
    
    print(f"✅ Extracted {len(_captured_gaps)} gaps!")
    print(f"\n📋 Next: Review gaps_review.yaml and annotate each gap")
    
    # Exit without running actual corrections
    sys.exit(0)

# Apply monkey-patch
corrector.LyricsCorrector.apply_corrections = _capturing_apply_corrections

# Now run the CLI
print("🎯 Gap Extractor v2")
print("=" * 50)
print()

os.environ["USE_AGENTIC_AI"] = "0"  # Don't run agentic corrections

sys.argv = ["lyrics-transcriber", "Time-Bomb.flac", "--output-format", "lrc"]

from lyrics_transcriber.cli.cli_main import main as cli_main

try:
    cli_main()
except SystemExit as e:
    if e.code == 0 and len(_captured_gaps) > 0:
        print("\n✅ Success!")
    else:
        print(f"\n⚠️  Exited with code: {e.code}")
        if len(_captured_gaps) == 0:
            print("   No gaps were captured - correction may not have run")

