# Human Feedback Loop Documentation

## Overview

The Agentic Correction System includes a comprehensive human feedback loop that enables continuous improvement through learning from manual corrections. This guide explains how to use the system, analyze collected data, and improve AI accuracy over time.

## Table of Contents

1. [Making Corrections in the UI](#making-corrections-in-the-ui)
2. [Annotation Collection Process](#annotation-collection-process)
3. [Analyzing Collected Data](#analyzing-collected-data)
4. [Improving the Classifier](#improving-the-classifier)
5. [Evaluating Improvement](#evaluating-improvement)
6. [Future: Fine-Tuning & RLHF](#future-fine-tuning--rlhf)

---

## Making Corrections in the UI

### Step 1: Process a Song

```bash
python -m lyrics_transcriber.cli.cli_main your-song.mp3 \
  --artist "Artist Name" --title "Song Title"
```

This will:
1. Transcribe the audio
2. Fetch reference lyrics
3. Identify anchor sequences and gaps
4. Run agentic AI correction (if `USE_AGENTIC_AI=1`)
5. Launch the review UI in your browser

### Step 2: Review and Correct in UI

When you make edits in the UI:
- Edit a word's text
- Delete a word
- Merge/split words
- Adjust timing

**An annotation modal will appear** (if annotations are enabled).

### Step 3: Fill in Annotation Details

The modal asks for:

1. **Correction Type** (dropdown)
   - Sound-Alike Error
   - Background Vocals
   - Extra Filler Words
   - Punctuation/Style Only
   - Repeated Section
   - Complex Multi-Error
   - Ambiguous
   - No Error
   - Manual Edit

2. **Confidence** (1-5 slider)
   - 1: Very Uncertain
   - 2: Somewhat Uncertain
   - 3: Neutral
   - 4: Fairly Confident
   - 5: Very Confident

3. **Reasoning** (text area, minimum 10 characters)
   - Explain WHY this correction is needed
   - Reference what you heard in the audio
   - Mention if reference lyrics helped

### Step 4: Save or Skip

- **Save & Continue**: Stores the annotation for analysis
- **Skip**: Applies the correction without annotation (not recommended)

### Step 5: Complete Review

When you click "Finish Review":
- All corrections are applied
- All annotations are submitted to the backend
- Data is saved to `cache/correction_annotations.jsonl`

---

## Annotation Collection Process

### Storage Format

Annotations are stored in **JSONL** (JSON Lines) format:
- File: `cache/correction_annotations.jsonl`
- One annotation per line
- Easy to append, version control friendly
- Can be parsed line-by-line for large datasets

### Example Annotation

```json
{
  "annotation_id": "550e8400-e29b-41d4-a716-446655440000",
  "audio_hash": "abc123",
  "gap_id": "gap_1",
  "annotation_type": "SOUND_ALIKE",
  "action_taken": "REPLACE",
  "original_text": "out I'm starting over",
  "corrected_text": "now I'm starting over",
  "confidence": 5.0,
  "reasoning": "The word 'out' sounds like 'now' but the reference lyrics and context make it clear it should be 'now'",
  "word_ids_affected": ["word_123"],
  "agentic_proposal": {"action": "ReplaceWord", "replacement_text": "now"},
  "agentic_category": "SOUND_ALIKE",
  "agentic_agreed": true,
  "reference_sources_consulted": ["genius", "spotify"],
  "artist": "Rancid",
  "title": "Time Bomb",
  "session_id": "lyrics-correction-abc123",
  "timestamp": "2025-10-27T12:00:00"
}
```

### What Gets Tracked

For each correction, we collect:
- **What changed**: Original → Corrected text
- **Why it changed**: Human reasoning
- **How confident**: 1-5 scale
- **What AI suggested**: For comparison
- **Agreement**: Did human agree with AI?
- **Context**: Song, artist, reference sources used

---

## Analyzing Collected Data

### Running the Analysis Script

```bash
python scripts/analyze_annotations.py
```

**Options:**
- `--cache-dir cache`: Where to find annotations
- `--output CORRECTION_ANALYSIS.md`: Where to save report

### What the Report Includes

1. **Overview Statistics**
   - Total annotations collected
   - Number of unique songs/artists
   - Date range
   - Average confidence
   - High-confidence percentage

2. **Breakdown by Type**
   - How many of each error category
   - Percentage distribution

3. **Actions Taken**
   - REPLACE, DELETE, NO_ACTION, etc.
   - Which actions are most common

4. **AI Performance**
   - Overall agreement rate
   - Agreement rate by category
   - Which categories AI is good/bad at

5. **Common Error Patterns**
   - Top 20 most frequent corrections
   - "word A → word B" patterns
   - Examples from real songs

6. **Frequently Misheard Words**
   - Sound-alike errors that occur multiple times
   - e.g., "out" → "now", "said" → "set"

7. **Reference Source Usage**
   - Which sources are consulted most often
   - Helps identify most reliable sources

8. **Recommendations**
   - Categories needing improvement
   - When to regenerate few-shot examples
   - When you have enough data for fine-tuning

### Example Output

```markdown
## Most Common Error Patterns

### 1. `out → now` (15 occurrences)
- **Type:** SOUND_ALIKE
- **Average Confidence:** 4.8/5.0
- **Examples:**
  - Rancid - Time Bomb: "Classic homophone error..."
  - ...

## Agentic AI Performance

- **Overall Agreement Rate:** 65.3%

### Agreement by Category
- **SOUND_ALIKE:** 78.5% (23 samples)
- **BACKGROUND_VOCALS:** 92.1% (12 samples)
- **EXTRA_WORDS:** 45.2% (8 samples) ⚠️ Needs improvement
```

---

## Improving the Classifier

### Step 1: Collect Sufficient Data

**Minimum recommended:**
- 20+ high-confidence annotations (confidence >= 4)
- At least 3-5 examples per category
- Multiple different songs/artists

**Check if ready:**
```bash
python scripts/analyze_annotations.py
```

Look for: "Training Data Available" section in the report.

### Step 2: Generate Few-Shot Examples

```bash
python scripts/generate_few_shot_examples.py
```

**Options:**
- `--min-confidence 4.0`: Only use annotations rated 4 or 5
- `--max-per-category 5`: How many examples per category
- `--output path/to/examples.yaml`: Custom output location

**Output:** `lyrics_transcriber/correction/agentic/prompts/examples.yaml`

### Step 3: Verify Examples

Review the generated `examples.yaml`:

```yaml
metadata:
  generated_at: cache/correction_annotations.jsonl
  total_examples: 25
  categories: [sound_alike, background_vocals, extra_words, ...]

examples_by_category:
  sound_alike:
    - gap_text: "out I'm starting over"
      corrected_text: "now I'm starting over"
      action: REPLACE
      reasoning: "..."
      confidence: 5.0
      artist: "Rancid"
      title: "Time Bomb"
      agentic_agreed: true
```

### Step 4: Classifier Auto-Loads Examples

The classifier automatically checks for `examples.yaml` on startup:

```python
def load_few_shot_examples() -> Dict[str, List[Dict]]:
    examples_path = Path(__file__).parent / "examples.yaml"
    
    if not examples_path.exists():
        return get_hardcoded_examples()  # Uses defaults
    
    # Load from file
    with open(examples_path, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('examples_by_category', {})
```

**No code changes needed** - just regenerate the examples file!

### Step 5: Test Improved Classifier

```bash
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main test-song.mp3 \
  --artist "Test Artist" --title "Test Song"
```

Monitor:
- Classification accuracy (check Langfuse traces)
- Agreement rate in next batch of annotations
- Corrections that are automatically applied

---

## Evaluating Improvement

### Metrics to Track

Track these over time as you collect more data:

1. **AI Agreement Rate**
   - Target: > 70% overall
   - Track per category (some will be harder than others)

2. **Classification Accuracy**
   - What % of gaps are correctly categorized
   - Measured by human verification

3. **Auto-Correction Rate**
   - What % of gaps are automatically corrected (vs flagged)
   - Should increase over time

4. **High-Confidence Annotations**
   - What % of human corrections are rated 4-5
   - Higher = clearer patterns

### Continuous Improvement Cycle

```
1. Process songs with agentic AI
2. Human reviews and corrects in UI
3. Annotations collected
4. Analyze annotations (identify patterns)
5. Regenerate few-shot examples
6. Classifier improves
7. Repeat with next batch of songs
```

### Recommended Schedule

- **Weekly:** Run analysis script to monitor progress
- **Monthly:** Regenerate few-shot examples if you have +20 new high-confidence annotations
- **Quarterly:** Review agreement rates by category, adjust prompts if needed

### Warning Signs

⚠️ **Low agreement in specific category** (< 50%)
- Action: Review annotations for that category
- Check if prompt examples are misleading
- Consider adding more specific guidelines

⚠️ **Confidence scores declining**
- Might indicate more complex songs
- Or classifier is making less obvious mistakes

⚠️ **Same errors repeating**
- Check if few-shot examples cover this pattern
- May need to add explicit handling

---

## Future: Fine-Tuning & RLHF

### When You're Ready

Once you have **100-200+ high-confidence annotations**:

1. **Export Training Data**
   ```python
   from lyrics_transcriber.correction.feedback.store import FeedbackStore
   
   store = FeedbackStore("cache")
   training_file = store.export_to_training_data()
   print(f"Training data: {training_file}")
   ```

2. **Fine-Tune Small Model**
   - Use Llama 3.1-8B or similar open model
   - Fine-tune on classification task
   - Much faster and cheaper than GPT-4 for inference
   - Can run locally via Ollama

3. **Reinforcement Learning from Human Feedback (RLHF)**
   - Collect preference rankings (A vs B comparisons)
   - Fine-tune model to align with human preferences
   - More advanced but very powerful

### Resources for Fine-Tuning

- **Hugging Face Transformers**: Standard fine-tuning pipeline
- **Axolotl**: Easy fine-tuning for open models
- **LangFuse**: Can track model versions and performance
- **PEFT/LoRA**: Parameter-efficient fine-tuning (faster, cheaper)

### Cost-Benefit Analysis

**Pros of fine-tuning:**
- Faster inference (no external API calls)
- Lower long-term costs
- Complete control over model
- Can run offline

**Cons of fine-tuning:**
- Requires significant data (100+ examples)
- Initial setup time
- Need to manage model hosting
- May not match GPT-4 quality initially

**Recommendation:** Start with few-shot learning (what we've built), then consider fine-tuning once you have 200+ annotations.

---

## Best Practices

### Annotation Quality

✅ **Do:**
- Be specific in reasoning ("The word 'out' sounds like 'now' but context confirms 'now'")
- Reference what you heard in the audio
- Mention which reference source helped
- Use confidence 4-5 only when certain

❌ **Don't:**
- Generic reasoning ("it was wrong")
- Annotate if you're guessing
- Skip annotations to save time (reduces data quality)

### Data Collection

- **Aim for diversity**: Different artists, genres, decades
- **Prioritize quality over quantity**: Better to have 50 excellent annotations than 200 rushed ones
- **Regular reviews**: Process songs weekly to maintain consistent annotation quality

### System Maintenance

- **Backup annotations file**: `cache/correction_annotations.jsonl` is precious data
- **Version control**: Consider committing `examples.yaml` to track improvements
- **Monitor logs**: Check Langfuse for AI performance trends

---

## API Reference

### Backend Endpoints

**POST /api/v1/annotations**
- Save a correction annotation
- Body: `CorrectionAnnotation` object (without ID/timestamp)
- Returns: `{"status": "success", "annotation_id": "..."}`

**GET /api/v1/annotations/{audio_hash}**
- Get all annotations for a specific song
- Returns: `{"audio_hash": "...", "count": N, "annotations": [...]}`

**GET /api/v1/annotations/stats**
- Get aggregated statistics
- Returns: `AnnotationStatistics` object

### Frontend API Client

```typescript
// Submit annotations after review
await apiClient.submitAnnotations(annotations)

// Get statistics for dashboard
const stats = await apiClient.getAnnotationStats()
```

---

## Troubleshooting

### Annotations Not Saving

**Check:**
1. Is the modal appearing after edits?
2. Are you in read-only mode? (Annotations disabled in read-only)
3. Check browser console for errors
4. Verify `cache/correction_annotations.jsonl` exists and is writable

### Modal Not Appearing

**Check:**
1. Annotations enabled? (localStorage key: `annotationsEnabled`)
2. Did you actually change the text? (Modal only shows if original ≠ corrected)
3. Are you using live API mode (not file-only)?

### Analysis Script Errors

**Check:**
1. Does `cache/correction_annotations.jsonl` exist?
2. Is the file valid JSONL? (one JSON object per line)
3. Run with verbose logging: `python scripts/analyze_annotations.py --cache-dir cache`

### Few-Shot Generation Fails

**Check:**
1. Do you have any high-confidence annotations? (confidence >= 4)
2. Try lowering threshold: `--min-confidence 3.0`
3. Check YAML syntax in generated file

---

## File Locations

### Code
- `lyrics_transcriber/correction/feedback/schemas.py` - Annotation data models
- `lyrics_transcriber/correction/feedback/store.py` - Storage backend
- `lyrics_transcriber/frontend/src/components/CorrectionAnnotationModal.tsx` - UI modal
- `lyrics_transcriber/correction/agentic/prompts/classifier.py` - Classification prompt builder

### Data
- `cache/correction_annotations.jsonl` - All collected annotations (backup this!)
- `lyrics_transcriber/correction/agentic/prompts/examples.yaml` - Few-shot examples for classifier
- `cache/training_data.jsonl` - Exported high-confidence data for fine-tuning

### Scripts
- `scripts/analyze_annotations.py` - Generate analysis report
- `scripts/generate_few_shot_examples.py` - Update classifier examples

### Reports
- `CORRECTION_ANALYSIS.md` - Generated by analysis script
- `AGENTIC_IMPLEMENTATION_STATUS.md` - Implementation status and architecture

---

## Example Workflow

### Week 1: Initial Collection

```bash
# Process 5 songs with annotation collection
for song in song1.mp3 song2.mp3 song3.mp3 song4.mp3 song5.mp3; do
    python -m lyrics_transcriber.cli.cli_main "$song" --artist "..." --title "..."
    # Review in UI, make corrections, fill in annotations
done

# Check what you've collected
python scripts/analyze_annotations.py
```

**Expected:** 20-50 annotations

### Week 2: First Analysis

```bash
# Generate analysis report
python scripts/analyze_annotations.py

# Review CORRECTION_ANALYSIS.md
# Identify: Most common errors, AI agreement rate
```

### Week 4: First Improvement Cycle

```bash
# Check if ready for few-shot generation
python scripts/analyze_annotations.py
# Look for "Training Data Available" message

# Generate few-shot examples
python scripts/generate_few_shot_examples.py

# Verify examples.yaml was created
cat lyrics_transcriber/correction/agentic/prompts/examples.yaml
```

### Week 5+: Monitor Improvement

```bash
# Process new songs (classifier now uses your examples)
python -m lyrics_transcriber.cli.cli_main new-song.mp3 ...

# Compare agreement rates
python scripts/analyze_annotations.py
# Check if agreement rate increased
```

### Month 3: Consider Fine-Tuning

If you have 100-200+ high-confidence annotations:

```python
from lyrics_transcriber.correction.feedback.store import FeedbackStore

store = FeedbackStore("cache")
training_file = store.export_to_training_data()
print(f"Training data ready: {training_file}")
# Use this file for fine-tuning a small LLM
```

---

## Advanced Topics

### Custom Few-Shot Examples

You can manually edit `examples.yaml` to:
- Add hand-crafted examples
- Remove low-quality examples
- Adjust example ordering (first examples are most influential)

### A/B Testing Different Prompts

1. Save current `examples.yaml` as `examples_v1.yaml`
2. Generate new version with different parameters
3. Process same song with both versions
4. Compare results in Langfuse
5. Keep the better version

### Measuring ROI

Track time saved:
- **Before AI:** Average time to manually correct a song
- **After AI:** Average time with AI assistance
- **Time saved = (Before - After) × Songs processed**

Typical results:
- Without AI: 10-15 min/song (manual correction)
- With AI (50% accuracy): 5-8 min/song
- With AI (70% accuracy): 3-5 min/song
- With AI (90% accuracy): 1-2 min/song (just verification)

---

## FAQ

**Q: How many annotations do I need before it's useful?**
A: You'll start seeing improvement with 20-30 high-quality annotations. Real gains come at 50-100+.

**Q: Should I annotate every single correction?**
A: Yes, if possible. But if you're in a hurry, prioritize:
- Cases where you disagree with AI
- Complex/interesting error patterns
- High-confidence corrections (4-5 rating)

**Q: What if the AI gets worse after updating examples?**
A: Revert to previous `examples.yaml`, review the new annotations for quality issues, or increase `--min-confidence` threshold.

**Q: Can I disable annotation collection?**
A: Yes, toggle in UI (localStorage key: `annotationsEnabled`) or set to false in code.

**Q: How do I backup my annotations?**
A: Copy `cache/correction_annotations.jsonl` to a safe location. Consider version control.

**Q: What if annotation file gets corrupted?**
A: Each line is independent (JSONL format). Delete corrupted lines and re-run analysis.

---

## Next Steps

After implementing this feedback loop:

1. **Short term** (Weeks 1-4):
   - Collect diverse annotations
   - Run analysis weekly
   - Update few-shot examples monthly

2. **Medium term** (Months 2-6):
   - Achieve 70%+ AI agreement rate
   - Reduce manual review time by 50%
   - Build dataset of 100-200 annotations

3. **Long term** (Months 6-12):
   - Consider fine-tuning custom model
   - Implement RLHF for preference learning
   - Achieve 85%+ AI agreement rate
   - Reduce manual review time by 80%

---

## Contributing

If you discover patterns or improvements:
1. Document in your annotations
2. Share insights in `CORRECTION_ANALYSIS.md`
3. Consider contributing successful prompts/examples back to the project

---

## Support

For issues or questions:
- Check `AGENTIC_IMPLEMENTATION_STATUS.md` for known issues
- Review `QUICK_START_AGENTIC.md` for testing guidance
- Check Langfuse traces for AI behavior insights

