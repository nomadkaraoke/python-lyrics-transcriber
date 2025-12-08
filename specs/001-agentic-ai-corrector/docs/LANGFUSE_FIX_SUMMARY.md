# Langfuse Integration Fix Summary

## Problem
Despite `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` being set, no traces were appearing in the Langfuse dashboard. LiteLLM was showing this warning:

```
LiteLLM:WARNING: opentelemetry.py:184 - Proxy Server is not installed. Skipping OpenTelemetry initialization.
```

## Root Cause
The callback configuration was incorrect. I was using:
```python
litellm.success_callback = ["langfuse_otel"]
litellm.failure_callback = ["langfuse_otel"]
```

But according to the [official LiteLLM Langfuse OTEL docs](https://docs.litellm.ai/docs/observability/langfuse_otel_integration), the correct way is:
```python
litellm.callbacks = ["langfuse_otel"]
```

## Changes Made

### 1. Fixed Callback Configuration
**File**: `lyrics_transcriber/correction/agentic/providers/bridge.py`

**Before**:
```python
litellm.success_callback = ["langfuse_otel"]
litellm.failure_callback = ["langfuse_otel"]
```

**After**:
```python
# Set required environment variables for Langfuse OTEL integration
os.environ.setdefault("LANGFUSE_OTEL_HOST", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))

# Configure LiteLLM to use langfuse_otel callback
# This is the correct way for Langfuse v3 with OpenTelemetry
litellm.callbacks = ["langfuse_otel"]
```

### 2. Added LANGFUSE_OTEL_HOST
The OTEL integration requires the `LANGFUSE_OTEL_HOST` environment variable to be set. This is now automatically set from `LANGFUSE_HOST` if not explicitly provided.

### 3. Fixed Logger Bug
Fixed an `UnboundLocalError` where `logger` was being used before it was defined.

## Required Environment Variables

```bash
# Required
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."

# Optional (will default to https://cloud.langfuse.com if not set)
export LANGFUSE_HOST="https://us.cloud.langfuse.com"  # US region
export LANGFUSE_OTEL_HOST="https://us.cloud.langfuse.com"  # Usually same as LANGFUSE_HOST
```

## How to Test

1. **Ensure environment variables are set** in your `.env` file or shell
2. **Run your test again**:
   ```bash
   lyrics-transcriber --log_level DEBUG \
     --cache_dir ./cache \
     --artist "The Format" \
     --title "Time Bomb" \
     Time-Bomb.flac 2>&1 | tee langfuse-test.log
   ```

3. **Check the logs** for this message:
   ```
   🤖 Langfuse OTEL callbacks enabled (host: https://us.cloud.langfuse.com)
   ```

4. **Check your Langfuse dashboard** after ~30-60 seconds (traces are buffered):
   - Visit https://us.cloud.langfuse.com (or your region)
   - Look for traces with:
     - Model name (e.g., `ollama/gpt-oss:latest`)
     - Full prompts and responses
     - Token counts
     - Latency metrics
     - Tags: `agentic-correction`, `model:ollama/gpt-oss:latest`

## Expected Log Output

You should see:
```
2025-10-21 00:xx:xx - DEBUG - bridge - 🤖 Langfuse OTEL callbacks enabled (host: https://us.cloud.langfuse.com)
2025-10-21 00:xx:xx - DEBUG - bridge - 🤖 [LiteLLM] Sending prompt to ollama/gpt-oss:latest: You are correcting transcription errors...
2025-10-21 00:xx:xx - INFO - bridge - 🤖 [LiteLLM] Got response from ollama/gpt-oss:latest: [{"action": "ReplaceWord", ...
```

And **NO** warning about "Proxy Server is not installed".

## Troubleshooting

If traces still don't appear:

1. **Verify keys are set**:
   ```bash
   env | grep LANGFUSE
   ```

2. **Check Langfuse version**:
   ```bash
   pip show langfuse
   # Should show: Version: 3.8.0 (or higher)
   ```

3. **Check OpenTelemetry libraries are installed**:
   ```bash
   pip show opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
   ```

4. **Wait 30-60 seconds** - traces are buffered and sent in batches

5. **Check the correct region**:
   - US: https://us.cloud.langfuse.com
   - EU: https://cloud.langfuse.com

## References

- [LiteLLM Langfuse OTEL Integration Docs](https://docs.litellm.ai/docs/observability/langfuse_otel_integration)
- [Langfuse OpenTelemetry Get Started](https://langfuse.com/docs/opentelemetry/get-started)
- Full migration details: See `LANGFUSE_OTEL_MIGRATION.md`

