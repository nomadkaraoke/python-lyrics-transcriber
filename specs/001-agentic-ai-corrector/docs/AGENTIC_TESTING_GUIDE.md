# Agentic AI Correction - Testing & Debugging Guide

## Changes Made (Latest)

### 1. **Fixed Prompt Schema** ✅
- Added explicit JSON schema to the prompt so the LLM knows what format to return
- Includes required fields: `action`, `replacement_text`, `confidence`, `reason`
- Added example in prompt

### 2. **Added Request/Response Logging** ✅  
- Bridge now logs first 200 chars of prompt and first 500 chars of response
- Use `--log_level DEBUG` to see full details

### 3. **Integrated Langfuse Tracing** ✅
- LiteLLM now automatically sends traces to Langfuse when keys are present
- Check your Langfuse dashboard at: https://us.cloud.langfuse.com

---

## How to Test

### Basic Test Command
```bash
cd /Users/andrew/Projects/karaoke-gen/lyrics_transcriber_local
lyrics-transcriber --log_level DEBUG \
  --cache_dir ./cache \
  --artist "The Format" \
  --title "Time Bomb" \
  Time-Bomb.flac 2>&1 | tee agentic-test.log
```

### What to Look For

#### ✅ **Success Indicators:**
```
🤖 AGENTIC MODE: ENABLED
🤖 Agentic modules imported successfully - running in AGENTIC-ONLY mode
🤖 [LiteLLM] Sending prompt to ollama/gpt-oss:latest: ...
🤖 [LiteLLM] Got response from ollama/gpt-oss:latest: [{"action": "ReplaceWord", ...
🤖 Agent returned 2 proposals
🤖 Adapter returned 2 corrections
🤖 Applying 2 agentic corrections for gap 1
Made correction: 'I'm' -> 'I'm' (confidence: 0.90, reason: Apostrophe correction)
```

#### ❌ **Failure Indicators:**
```
🤖 Provider returned error: {'error': 'provider_error', 'message': '...timeout...'}
🤖 Failed to validate proposal: ... Field required [type=missing ...]
🤖 Agent returned 0 proposals
circuit_open (circuit breaker tripped after failures)
```

---

## Debugging Steps

### 1. Check Ollama is Running
```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"gpt-oss:latest","prompt":"test","stream":false}' \
  --max-time 10
```

### 2. View Full Prompt/Response
Look for these log lines with `--log_level DEBUG`:
```
🤖 [LiteLLM] Sending prompt to ollama/gpt-oss:latest: You are correcting transcription errors...
🤖 [LiteLLM] Got response from ollama/gpt-oss:latest: [{"action": "ReplaceWord"...
```

### 3. Check Langfuse Dashboard
- URL: https://us.cloud.langfuse.com
- Look for traces tagged: `agentic-correction`, `model:ollama/gpt-oss:latest`
- View full prompts, responses, latency, token usage

### 4. If Timeouts Continue
Increase timeout in `.env`:
```bash
AGENTIC_TIMEOUT_SECONDS=60
```

Or disable circuit breaker temporarily:
```bash
AGENTIC_CIRCUIT_THRESHOLD=999
```

### 5. If Schema Validation Fails
Check the error for which fields are missing:
```
Field required [type=missing, input_value={...}, input_type=dict]
action
  Field required
```

The LLM might need a better example in the prompt, or the model might not follow instructions well.

---

## Environment Variables Reference

```bash
# Required for agentic mode
USE_AGENTIC_AI=1
AGENTIC_AI_MODEL=ollama/gpt-oss:latest

# Required for Langfuse observability (OTEL integration)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_OTEL_HOST=https://us.cloud.langfuse.com  # US region (default)
# LANGFUSE_OTEL_HOST=https://cloud.langfuse.com   # EU region

# Optional for privacy mode (uses only local models)
PRIVACY_MODE=1

# Optional tuning
AGENTIC_TIMEOUT_SECONDS=30           # Default: 30
AGENTIC_MAX_RETRIES=2                # Default: 2
AGENTIC_CIRCUIT_THRESHOLD=3          # Failures before circuit opens
AGENTIC_CIRCUIT_OPEN_SECONDS=60      # How long circuit stays open
```

---

## Known Issues

### Issue 1: First Call Timeout
**Symptom:** Gap 1 takes 30+ seconds, then circuit breaker opens

**Cause:** Ollama loads model into memory on first call

**Solution:** 
- Increase `AGENTIC_TIMEOUT_SECONDS=60`
- Or pre-warm Ollama: `curl http://localhost:11434/api/generate -d '{"model":"gpt-oss:latest","prompt":"test"}'`

### Issue 2: Schema Validation Fails
**Symptom:** `Field required` errors in logs

**Cause:** LLM doesn't follow the JSON schema exactly

**Solution:**
- Try a different model (e.g., Claude, GPT-4)
- Improve the prompt with more explicit examples
- Use Instructor mode (set `USE_INSTRUCTOR=1`)

### Issue 3: No Traces in Langfuse
**Symptom:** Langfuse dashboard is empty

**Causes:**
- Keys not set correctly in `.env`
- Missing OTEL dependencies
- Traces buffered (wait 30s-1min)
- Wrong endpoint (US vs EU region)

**Solution:**
- Verify keys: `env | grep LANGFUSE`
- Check version: `pip show langfuse` (should be 3.x for OTEL)
- Install OTEL deps: `pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp`
- Check logs for "🤖 Langfuse OTEL callbacks enabled"
- Verify endpoint: `LANGFUSE_OTEL_HOST` matches your region

---

## Next Steps

1. **Test with the new prompt** - It should now return properly formatted JSON
2. **Monitor Langfuse** - You should see traces appearing within 1-2 minutes
3. **Tune the model** - If responses are poor, try:
   - Different model (e.g., `gpt-4o`, `claude-3.5-sonnet`)
   - Better prompt engineering
   - Few-shot examples in the prompt
4. **Measure accuracy** - Compare agentic vs rule-based corrections

