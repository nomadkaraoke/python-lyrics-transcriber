# Langfuse Sessions Implementation

## Overview

All traces from a single lyrics correction task are now grouped into a **Langfuse Session** for easier debugging and analysis.

## What Changed

### 1. Session ID Generation
- **Location**: `lyrics_transcriber/correction/corrector.py`
- **Format**: `lyrics-correction-{shortuuid}`
- **Scope**: One session per correction task (all gaps in one song)

```python
session_id = f"lyrics-correction-{shortuuid.uuid()}"
self.logger.info(f"Starting correction process with {len(gap_sequences)} gaps (session: {session_id})")
```

### 2. Session ID Propagation
The `session_id` flows through the entire stack:

```
corrector.py (generates session_id)
    ↓
AgenticCorrector.from_model(session_id=session_id)
    ↓
AgenticCorrector.__init__(session_id=session_id)
    ↓
agent.propose() → config["metadata"]["langfuse_session_id"]
    ↓
LangChainBridge.generate_correction_proposals(session_id=session_id)
    ↓
LangChain model.invoke(config={"metadata": {"langfuse_session_id": session_id}})
```

### 3. Metadata Format
Following Langfuse's documented format for LangChain integration:

```python
config = {
    "callbacks": [langfuse_handler],
    "metadata": {
        "langfuse_session_id": "lyrics-correction-AbCdEf123456"
    }
}
```

## Benefits

✅ **Single Session View**: All gap corrections for one song grouped together  
✅ **Easy Replay**: Click on a session to see the entire correction workflow  
✅ **Better Debugging**: Trace the flow from first gap to last gap  
✅ **Performance Analysis**: Compare session durations across different songs  
✅ **Cost Tracking**: See total tokens/cost per correction task  

## Usage

### In Logs
```
INFO - Starting correction process with 23 gaps (session: lyrics-correction-AbCdEf123456)
DEBUG - 🤖 Set Langfuse session_id in metadata: lyrics-correction-AbCdEf123456
DEBUG - 🤖 [LangChain] Invoking with session_id: lyrics-correction-AbCdEf123456
```

### In Langfuse Dashboard
1. Navigate to the **Sessions** tab
2. Find sessions prefixed with `lyrics-correction-`
3. Click to see all traces for that correction task
4. View session replay showing the entire workflow

## Testing

Integration test updated to pass `session_id` parameter:

```python
class MockProvider(BaseAIProvider):
    def generate_correction_proposals(self, prompt, schema, session_id=None):
        # ... mock implementation
```

All tests pass with the new session tracking! ✅

## References

- [Langfuse Sessions Documentation](https://langfuse.com/docs/tracing/sessions)
- [LangChain Integration](https://langfuse.com/docs/integrations/langchain)

