# Gap Extraction Guide

## Problem
We need to extract gap data from the correction process to manually review and annotate how each gap should be handled.

## Quick Solution

Run your normal correction command, but add this Python code at the start of `corrector.py`'s gap processing loop:

### Step 1: Add Gap Dumping Code

In `/Users/andrew/Projects/karaoke-gen/lyrics_transcriber_local/lyrics_transcriber/correction/corrector.py`, find the line:

```python
        for i, gap in enumerate(gap_sequences, 1):
            self.logger.info(f"Processing gap {i}/{len(gap_sequences)} at position {gap.transcription_position}")
```

And **before the loop**, add this code:

```python
        # === GAP EXTRACTION CODE (TEMPORARY) ===
        import yaml
        if os.getenv("DUMP_GAPS") == "1":
            gaps_data = []
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
                
                ref_context = ""
                for source, lyrics_data in self.reference_lyrics.items():
                    if lyrics_data and lyrics_data.segments:
                        ref_words = []
                        for seg in lyrics_data.segments[:20]:
                            ref_words.extend([w.text for w in seg.words])
                        ref_context = " ".join(ref_words[:150])
                        break
                
                gap_text = " ".join([w["text"] for w in gap_words])
                
                gaps_data.append({
                    "gap_id": i,
                    "position": gap.transcription_position,
                    "gap_text": gap_text,
                    "transcribed_words": gap_words,
                    "reference_context": ref_context[:300],
                    "word_count": len(gap_words),
                    "annotations": {
                        "your_decision": "",
                        "action_type": "# NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT",
                        "target_word_ids": [],
                        "replacement_text": "",
                        "notes": ""
                    }
                })
            
            with open("gaps_review.yaml", 'w') as f:
                f.write("# Gap Review Data\n")
                f.write(f"# Total gaps: {len(gaps_data)}\n\n")
                yaml.dump({"gaps": gaps_data}, f, default_flow_style=False, allow_unicode=True, width=120, sort_keys=False)
            
            self.logger.info(f"📝 Dumped {len(gaps_data)} gaps to gaps_review.yaml")
            import sys
            sys.exit(0)
        # === END GAP EXTRACTION CODE ===
```

### Step 2: Run with the Flag

```bash
DUMP_GAPS=1 USE_AGENTIC_AI=0 poetry run lyrics-transcriber Time-Bomb.flac
```

This will:
1. Find all gaps
2. Write them to `gaps_review.yaml`
3. Exit before processing

### Step 3: Review the Output

Open `gaps_review.yaml` and for each gap, fill in:
- `your_decision`: Brief description of what should happen
- `action_type`: NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT
- `target_word_ids`: Which word IDs to operate on (from `transcribed_words`)
- `replacement_text`: The corrected text
- `notes`: Any additional context

### Example Annotation

```yaml
- gap_id: 1
  position: 7
  gap_text: "out, I'm starting over I'm"
  transcribed_words:
    - {id: w7, text: "out,", start_time: 10.5, end_time: 10.8}
    - {id: w8, text: "I'm", start_time: 10.9, end_time: 11.1}
    # ... more words
  reference_context: "Starting now I'm starting over I'm gonna sleep..."
  annotations:
    your_decision: "Replace 'out,' with 'now' - transcription error"
    action_type: "REPLACE"
    target_word_ids: ["w7"]
    replacement_text: "now"
    notes: "Reference lyrics clearly say 'now' not 'out'"
```

### Step 4: Remove the Temporary Code

After extracting gaps, remove the `=== GAP EXTRACTION CODE ===` block from `corrector.py`.

## Why This Approach?

The monkey-patching scripts were failing because:
1. Method names weren't what we expected
2. The correction logic is inline, not in a separate method
3. Easier to just add temporary code directly

This direct approach is simpler and more reliable for a one-time extraction.

