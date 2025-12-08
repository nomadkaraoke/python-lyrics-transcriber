# Quick Start: Testing the Agentic Correction System

## What's Been Implemented

The classification-first agentic correction system is now functional with:

✅ **8 gap categories** automatically detected by LLM
✅ **8 specialized handlers** for each category
✅ **Two-step workflow:** Classify gap → Route to handler → Generate proposals
✅ **Backend annotation system** ready to collect human feedback

## Testing the System

### Run Classification Workflow

```bash
cd /Users/andrew/Projects/karaoke-gen/lyrics_transcriber_local

USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
```

### What Happens

For each gap in the transcription:

1. **Classification Step:** LLM analyzes the gap and classifies it into one of 8 categories:
   - `SOUND_ALIKE`: Homophones like "out" vs "now"
   - `BACKGROUND_VOCALS`: Parenthesized backing vocals
   - `EXTRA_WORDS`: Filler words like "And", "But"
   - `PUNCTUATION_ONLY`: Just styling differences
   - `NO_ERROR`: Matches at least one reference source
   - `REPEATED_SECTION`: Chorus/verse repetitions
   - `COMPLEX_MULTI_ERROR`: Multiple error types
   - `AMBIGUOUS`: Needs human review

2. **Handler Step:** Appropriate handler processes the gap:
   - **Deterministic handlers** (no LLM needed): `PunctuationHandler`, `NoErrorHandler`, `BackgroundVocalsHandler`, `ExtraWordsHandler`
   - **LLM-assisted handlers**: `SoundAlikeHandler` (extracts replacement from references)
   - **Human review handlers**: `RepeatedSectionHandler`, `ComplexMultiErrorHandler`, `AmbiguousHandler`

3. **Proposal Generation:** Handler returns correction proposals with:
   - Action type (ReplaceWord, DeleteWord, NoAction, Flag)
   - Confidence score
   - Reasoning
   - Metadata (category, artist, title)

### Expected Output

You should see log messages like:

```
🤖 Classified gap gap_1 as SOUND_ALIKE (confidence: 0.95)
🤖 Agent returned 1 proposals
🤖 Adapter returned 1 corrections
🤖 Applying 1 agentic corrections for gap 1
Made correction: 'out' -> 'now' (confidence: 0.75, reason: Sound-alike error...)
```

### Recent Fix

**Issue:** Classification was failing with enum validation errors

**Solution:** Updated enum values to match LLM output format (uppercase like `"SOUND_ALIKE"` instead of lowercase `"sound_alike"`)

**Status:** ✅ Fixed and tested

## Monitoring with Langfuse

If you have Langfuse configured, you can view:
- Each classification LLM call
- Handler processing
- All grouped under session ID: `lyrics-correction-{uuid}`

Check your Langfuse dashboard at: https://cloud.langfuse.com

## What's NOT Yet Implemented

❌ **Frontend UI for human feedback collection**
- Annotation modal component
- Edit workflow integration
- Unable to collect human corrections yet

❌ **Analysis scripts**
- Can't generate reports from annotations
- Can't update few-shot examples automatically

❌ **Comprehensive tests**
- Unit tests for handlers
- Integration tests for full workflow

## Next Steps

1. **Test the classification workflow** with your Time-Bomb.flac file
2. **Review the corrections** it proposes
3. **Check Langfuse traces** to see how LLM classifies each gap
4. **Provide feedback** on classification accuracy

Once you're satisfied with the classification accuracy, the next priority is implementing the frontend annotation modal so you can start collecting human feedback to improve the system over time.

## Troubleshooting

### "Classification failed" errors
- **Check:** Model is running (Ollama, OpenAI, etc.)
- **Check:** API keys are set if using cloud providers
- **Check:** Langfuse keys if observability needed

### "No agentic corrections needed"
- This is normal for:
  - `PUNCTUATION_ONLY` gaps (no changes needed)
  - `NO_ERROR` gaps (transcription is correct)
  - Gaps flagged for human review
- **Not an error** - system is working as designed

### Slow processing
- Each gap requires 1-2 LLM calls (classification + optional handler)
- Consider using faster models (GPT-4-turbo, Claude Instant)
- Local models (Ollama) will be slower but free

## Files to Review

**Core Logic:**
- `lyrics_transcriber/correction/agentic/agent.py` - Main orchestrator
- `lyrics_transcriber/correction/agentic/handlers/` - Category handlers
- `lyrics_transcriber/correction/agentic/prompts/classifier.py` - Classification prompt

**Storage:**
- `lyrics_transcriber/correction/feedback/store.py` - Annotation storage
- `cache/correction_annotations.jsonl` - Where annotations will be saved

**Documentation:**
- `AGENTIC_IMPLEMENTATION_STATUS.md` - Full status and architecture
- `.cursor/plans/agentic-correction-system-*.plan.md` - Original plan

