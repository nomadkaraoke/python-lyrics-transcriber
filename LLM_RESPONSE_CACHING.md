# LLM Response Caching

## Overview

The Agentic Correction System now includes intelligent response caching to avoid redundant LLM API calls. This is especially useful when iterating on frontend changes or testing the same song multiple times.

## How It Works

### Automatic Caching

When the LangChainBridge makes an LLM call:

1. **Before calling LLM:** Check if response for this prompt+model is cached
2. **If cached:** Return cached response instantly (no LLM call!)
3. **If not cached:** Make LLM call, then cache the response
4. **Save to disk:** Cache persists across runs

### Cache Key

Responses are cached by SHA256 hash of:
```
hash(model_identifier + "::" + full_prompt_text)
```

This means:
- ✅ Same song, same prompts → **Cache HIT** (instant)
- ✅ Same song, changed prompts → **Cache MISS** (fresh call)
- ✅ Different song → **Cache MISS** (fresh call)
- ✅ Different model → **Cache MISS** (fresh call)

### Storage

**File:** `<cache_dir>/llm_response_cache.json`

By default, this is:
- `~/lyrics-transcriber-cache/llm_response_cache.json` (same directory as other cache files)
- Can be customized via `LYRICS_TRANSCRIBER_CACHE_DIR` environment variable

**Format:**
```json
{
  "abc123def456...": {
    "prompt": "You are an expert at analyzing...",
    "response": "{\"gap_id\": \"gap_1\", \"category\": \"SOUND_ALIKE\", ...}",
    "timestamp": "2025-10-27T12:00:00",
    "model": "ollama/gpt-oss:latest",
    "metadata": {
      "session_id": "lyrics-correction-xyz"
    }
  }
}
```

---

## Configuration

### Enable/Disable

**Default:** Enabled

```bash
# Caching is enabled by default (recommended for development)

# Disable caching (force fresh LLM calls every time)
export DISABLE_LLM_CACHE=1

# Re-enable
unset DISABLE_LLM_CACHE
```

### When to Disable

Disable caching when:
- Testing prompt changes (want to see fresh responses)
- Debugging LLM behavior
- Comparing different model responses
- Production runs (though caching is safe for production too)

### When to Keep Enabled

Keep caching enabled when:
- ✅ **Iterating on frontend UI** (your use case!)
- ✅ **Testing annotation workflows**
- ✅ **Developing new features**
- ✅ **Running same song multiple times**
- ✅ **Debugging non-LLM code**

---

## Managing the Cache

### View Statistics

```bash
python scripts/manage_llm_cache.py stats
```

**Output:**
```
📊 LLM Response Cache Statistics
==================================================
Cache file: cache/llm_response_cache.json
Status: Enabled
Total entries: 46

By model:
  - ollama/gpt-oss:latest: 46 responses

Date range:
  - Oldest: 2025-10-27T12:00:00
  - Newest: 2025-10-27T14:30:00
```

### Clear Entire Cache

```bash
python scripts/manage_llm_cache.py clear
```

When to clear:
- After updating prompts significantly
- When switching between different models
- If cache file gets large (>10MB)
- Before important production runs

### Prune Old Entries

```bash
# Remove entries older than 30 days (default)
python scripts/manage_llm_cache.py prune

# Custom threshold
python scripts/manage_llm_cache.py prune --days 7
```

---

## Usage Examples

### Scenario 1: Frontend Development

```bash
# First run (23 gaps × 30 seconds = ~11.5 minutes)
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
# All LLM calls made, responses cached

# Second run (instant! ~5 seconds)
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
# All responses from cache, UI launches immediately
```

**Time saved:** ~11 minutes per re-run!

### Scenario 2: Prompt Iteration

```bash
# Run 1: Original prompts
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main song.mp3 ...
# Responses cached

# Edit prompts/classifier.py to improve classification
# ...

# Run 2: Updated prompts
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main song.mp3 ...
# Cache MISS (prompt changed), fresh LLM calls made
# New responses cached
```

### Scenario 3: Testing Multiple Songs

```bash
# Process Song A
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main song-a.mp3 ...
# Song A responses cached

# Process Song B
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main song-b.mp3 ...
# Song B responses cached (different prompts due to different lyrics)

# Re-process Song A
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main song-a.mp3 ...
# Song A responses from cache (instant!)
```

---

## Cache Behavior

### What Triggers Cache HIT

✅ Exact same:
- Prompt text
- Model identifier
- (Song metadata doesn't affect hash, only prompt content does)

### What Triggers Cache MISS

❌ Changed:
- Any part of the prompt
- Model identifier
- Reference lyrics fetched differently
- Gap detection changed
- Prompt template modified

### Intelligent Invalidation

The cache automatically invalidates when:
- Prompts are updated (hash changes)
- Classification examples changed (prompt content changes)
- You use a different model

No manual invalidation needed!

---

## Performance Impact

### Without Cache

For a song with 23 gaps:
- **Time:** 23 gaps × 30 seconds = ~11.5 minutes
- **GPU:** Continuous inference load
- **API costs:** 46 LLM calls (classification + handling)

### With Cache (Second Run)

- **Time:** ~5 seconds (just loading from disk)
- **GPU:** Idle
- **API costs:** $0.00

### Development Workflow

Typical iteration cycle:
1. **First run:** 11 minutes (LLM calls)
2. **Make UI change**
3. **Second run:** 5 seconds (cached)
4. **Make another UI change**
5. **Third run:** 5 seconds (cached)
6. **Update prompts**
7. **Fourth run:** 11 minutes (fresh LLM calls, re-cached)

**Without cache:** Every run takes 11 minutes
**With cache:** Only first run and prompt changes take 11 minutes

---

## Cache Management

### Monitoring

```python
from lyrics_transcriber.correction.agentic.providers.response_cache import ResponseCache

cache = ResponseCache("cache")
stats = cache.get_stats()

print(f"Cached responses: {stats['total_entries']}")
print(f"Models: {list(stats['by_model'].keys())}")
```

### Selective Clearing

Currently, cache is all-or-nothing. For selective clearing:

```python
# Manual approach: edit cache/llm_response_cache.json
# Remove specific entries by hash key
```

Future enhancement: Add selective clearing by model or date range

### Backup

The cache file is valuable during development:

```bash
# Backup cache before major changes
cp cache/llm_response_cache.json cache/llm_response_cache.backup.json

# Restore if needed
cp cache/llm_response_cache.backup.json cache/llm_response_cache.json
```

---

## Troubleshooting

### Cache Not Working

**Check:**
1. Is `DISABLE_LLM_CACHE=1` set? (Unset it)
2. Does `cache/llm_response_cache.json` exist and is writable?
3. Check logs for "Cache HIT" vs "Cache MISS" messages

**Logs to look for:**
```
🎯 Cache HIT for ollama/gpt-oss:latest (hash: abc12345...)
   Cached at: 2025-10-27T12:00:00
```

### Unexpected Cache Hits

If you expect fresh LLM calls but getting cache hits:
- Verify you actually changed the prompt
- Check that classification examples didn't just reorder
- Clear cache and re-run

### Cache File Corruption

If cache file becomes corrupted:
```bash
# Delete and recreate
rm cache/llm_response_cache.json
# Will be recreated automatically on next run
```

### Large Cache File

If cache grows too large:
```bash
# Check size
ls -lh cache/llm_response_cache.json

# Prune old entries
python scripts/manage_llm_cache.py prune --days 7

# Or clear entirely
python scripts/manage_llm_cache.py clear
```

---

## Best Practices

### During Development

✅ **Keep caching enabled** - Speeds up iteration dramatically
✅ **Clear cache** after major prompt changes
✅ **Backup cache** before big refactors
✅ **Monitor cache stats** weekly

### Before Production

- ✅ **Clear cache** to ensure fresh responses
- ✅ **Disable caching** for first production run (optional)
- ✅ **Re-enable caching** after initial run (safe for production)

### Cache Maintenance

- **Weekly:** Check stats, prune if >100 entries
- **Monthly:** Consider clearing and rebuilding
- **After prompt updates:** Clear related entries or entire cache

---

## Technical Details

### Hash Collision Risk

**SHA256 hash:** Collision probability is negligible (< 1 in 2^256)

For context:
- 1,000 cached prompts: Collision risk ≈ 0%
- 1,000,000 cached prompts: Collision risk ≈ 0.00000001%

### Disk I/O

- **Write:** On every cache SET (after successful LLM call)
- **Read:** On cache initialization (once per run)
- **Performance:** Negligible compared to LLM inference time

### Memory Usage

- Cache loaded entirely into memory on initialization
- ~1-2 KB per entry
- 100 entries ≈ 100-200 KB in memory
- Not a concern for typical usage

---

## Future Enhancements

Potential improvements:

1. **TTL (Time To Live):** Auto-expire entries after N days
2. **Size limits:** Max cache size with LRU eviction
3. **Selective clearing:** Clear by model, date range, or pattern
4. **Cache compression:** Gzip responses to save disk space
5. **Cache statistics dashboard:** Visual monitoring in UI

---

## Summary

**LLM response caching is now enabled by default**, saving you significant time when:
- Re-running the same song (instant vs 11+ minutes)
- Iterating on UI/frontend changes
- Testing annotation workflows
- Developing new features

**For your Time Bomb example (23 gaps):**
- **First run:** ~11.5 minutes (LLM inference)
- **Subsequent runs:** ~5 seconds (cached responses)
- **Time saved:** ~11 minutes per iteration! 🚀

Simply run your song again, and the cache will automatically speed things up!

