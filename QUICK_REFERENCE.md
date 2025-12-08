# Quick Reference: Agentic Correction System

## ⚡ Quick Start

### Process a Song

```bash
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main your-song.mp3 \
  --artist "Artist Name" --title "Song Title"
```

### Analyze Annotations

```bash
python scripts/analyze_annotations.py
# Output: CORRECTION_ANALYSIS.md
```

### Update Classifier

```bash
python scripts/generate_few_shot_examples.py
# Output: lyrics_transcriber/correction/agentic/prompts/examples.yaml
```

---

## 📂 Important Files

### Data
- `~/lyrics-transcriber-cache/correction_annotations.jsonl` - All human annotations (backup this!)
- `~/lyrics-transcriber-cache/llm_response_cache.json` - Cached LLM responses (speeds up re-runs)
- `lyrics_transcriber/correction/agentic/prompts/examples.yaml` - Few-shot examples

**Note:** Default cache directory is `~/lyrics-transcriber-cache/`. Customize with `LYRICS_TRANSCRIBER_CACHE_DIR` env var.

### Scripts
- `scripts/analyze_annotations.py` - Generate reports
- `scripts/generate_few_shot_examples.py` - Update classifier

### Docs
- `IMPLEMENTATION_COMPLETE.md` - Complete overview
- `HUMAN_FEEDBACK_LOOP.md` - Detailed feedback loop guide
- `QUICK_START_AGENTIC.md` - Testing and troubleshooting
- `AGENTIC_IMPLEMENTATION_STATUS.md` - Technical details

---

## 🔧 Configuration

### Enable/Disable Agentic AI

```bash
# Enable
export USE_AGENTIC_AI=1

# Disable
unset USE_AGENTIC_AI
```

### LLM Response Caching

**Default:** Enabled (saves time and compute!)

Caches LLM responses to avoid redundant calls when re-running the same song:

```bash
# Cache is enabled by default
# Responses stored in: ~/lyrics-transcriber-cache/llm_response_cache.json

# Disable caching (force fresh LLM calls)
export DISABLE_LLM_CACHE=1

# Clear the cache (easiest way)
python scripts/manage_llm_cache.py clear
```

**Benefits:**
- Re-run same song instantly (no 30sec per gap wait)
- Iterate on frontend/UI changes without LLM calls
- Save GPU power and API costs
- Cache persists across runs

**When cache is used:**
- Same song, same prompts → instant (cached)
- Same song, updated prompts → fresh LLM calls
- Different song → fresh LLM calls
- Different model → fresh LLM calls

### Enable/Disable Annotations

In UI: Stored in browser localStorage (`annotationsEnabled`)
- Default: Enabled
- Toggle will be added to UI settings in future update

### Langfuse Tracking

```bash
export LANGFUSE_PUBLIC_KEY="your_key"
export LANGFUSE_SECRET_KEY="your_secret"
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

---

## 📊 8 Gap Categories

1. **SOUND_ALIKE** - Homophones (auto-corrects)
2. **BACKGROUND_VOCALS** - Parentheses content (auto-deletes)
3. **EXTRA_WORDS** - "And", "But" fillers (auto-deletes)
4. **PUNCTUATION_ONLY** - Style differences (no action)
5. **NO_ERROR** - Matches reference (no action)
6. **REPEATED_SECTION** - Chorus repeats (flags for review)
7. **COMPLEX_MULTI_ERROR** - Multiple issues (flags for review)
8. **AMBIGUOUS** - Unclear (flags for review)

---

## 🎯 Expected Behavior

### Auto-Corrected
- Sound-alike errors with clear reference match
- Background vocals in parentheses
- Extra filler words at sentence start

### Flagged for Review
- Repeated sections (chorus/verse)
- Complex gaps with multiple errors
- Ambiguous cases needing audio verification
- Any case where handler is uncertain

### No Action
- Punctuation/style differences only
- Transcription matches at least one reference source

---

## 🔍 Monitoring

### Check Langfuse Dashboard

- All gaps are classified
- Handler decisions are logged
- Session grouped: `lyrics-correction-{uuid}`

### Check Logs

```bash
# Successful classification
🤖 Classified gap gap_1 as GapCategory.SOUND_ALIKE (confidence: 0.95)

# Correction applied
Made correction: 'out' -> 'now' (confidence: 0.75, reason: ...)

# Flagged for review
🤖 Agent returned 1 proposals [action: Flag, requires_human_review: True]
```

### Check Annotations

```bash
# View raw annotations
cat cache/correction_annotations.jsonl | jq

# Count annotations
wc -l cache/correction_annotations.jsonl

# Get statistics
python -c "from lyrics_transcriber.correction.feedback.store import FeedbackStore; print(FeedbackStore('cache').get_statistics())"
```

---

## 🐛 Troubleshooting

### "Classification failed" Errors

**Cause:** LLM response parsing issue or invalid JSON

**Fix:**
1. Check LLM is running (Ollama, OpenAI, etc.)
2. Check API keys if using cloud provider
3. Response parser will attempt JSON fixes automatically
4. Falls back to FLAG proposal gracefully

### "No agentic corrections needed"

**Not an error!** This means:
- Gap was classified as NO_ERROR or PUNCTUATION_ONLY
- Handler returned NoAction proposal
- Or gap was flagged for human review

### Annotation Modal Not Appearing

**Check:**
1. Are you in read-only mode? (Need live API connection)
2. Did text actually change? (Modal only shows if original ≠ corrected)
3. Check browser console for errors
4. Try toggling annotations on/off in localStorage

### Slow Processing

**Normal:** Each gap requires 1-2 LLM calls
- Classification: ~5-30 seconds (depends on model)
- Handler logic: Usually instant (deterministic)

**Speed up:**
- Use faster models (GPT-4-turbo instead of local Ollama)
- Process fewer songs at once
- Consider batching gaps (future enhancement)

---

## 💾 Backup Strategy

### Critical Files to Backup

1. `cache/correction_annotations.jsonl` - YOUR MOST VALUABLE DATA
2. `lyrics_transcriber/correction/agentic/prompts/examples.yaml` - Your trained prompts
3. `cache/*.json` - Cached anchor sequences and reference lyrics

### Recommended Backup Schedule

```bash
# Daily backup script
cp cache/correction_annotations.jsonl backups/annotations_$(date +%Y%m%d).jsonl

# Weekly backup
tar -czf backups/cache_$(date +%Y%m%d).tar.gz cache/

# Version control
git add lyrics_transcriber/correction/agentic/prompts/examples.yaml
git commit -m "Update few-shot examples from human annotations"
```

---

## 🎓 Learning More

### Understanding the Code

1. Start with: `lyrics_transcriber/correction/agentic/agent.py`
   - See `propose_for_gap()` method for main workflow

2. Then read: `lyrics_transcriber/correction/agentic/handlers/base.py`
   - Understand handler interface

3. Pick a handler: `handlers/sound_alike.py`
   - See how each category is processed

4. Review prompt: `prompts/classifier.py`
   - See how LLM is guided to classify

### Understanding the Data Flow

```
User processes song
    ↓
LyricsCorrector detects gaps
    ↓
AgenticCorrector.propose_for_gap()
    ↓
classify_gap() → LLM classifies
    ↓
HandlerRegistry.get_handler(category)
    ↓
Handler.handle() → generates proposals
    ↓
Proposals → Adapter → WordCorrections
    ↓
Applied to segments
    ↓
UI shows for review
    ↓
Human makes corrections
    ↓
Annotation modal appears
    ↓
Annotation saved to JSONL
    ↓
Periodic analysis → Update few-shot examples
    ↓
Classifier improves → Better classifications
```

---

## 📧 Questions?

Refer to the comprehensive guides:
- **Usage:** `HUMAN_FEEDBACK_LOOP.md`
- **Technical:** `AGENTIC_IMPLEMENTATION_STATUS.md`
- **Testing:** `QUICK_START_AGENTIC.md`
- **Overview:** `IMPLEMENTATION_COMPLETE.md`

---

**Last Updated:** 2025-10-27
**Version:** 1.0.0
**Status:** Production Ready ✅

