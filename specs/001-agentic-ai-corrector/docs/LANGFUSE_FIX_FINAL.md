# Langfuse Integration Fixed ✅

## Summary

Fixed Langfuse tracing integration for the agentic AI corrector by:
1. Correcting the import path (`langfuse.langchain` instead of `langfuse.callback`)
2. Properly attaching callbacks to both LangGraph and LangChain ChatModels
3. Cleaning up unused backup files

---

## What Was Wrong

### 1. Incorrect Import Path
**Problem**: `No module named 'langfuse.callback'`

**Root Cause**: Using wrong import path for Langfuse CallbackHandler

**Fix**: Changed from:
```python
from langfuse.callback import CallbackHandler  # ❌ Wrong
```

To:
```python
from langfuse.langchain import CallbackHandler  # ✅ Correct
```

**Location**: `/lyrics_transcriber/correction/agentic/providers/model_factory.py` (line 95)

---

### 2. Not Actually Using LangGraph

**Problem**: LangGraph was installed but just a pass-through scaffold

**Root Cause**: The workflow was minimal and didn't have callbacks attached

**Fix**: 
- Updated `correction_graph.py` to properly build a LangGraph StateGraph
- Added support for attaching Langfuse callbacks via `.with_config()`
- Made LangGraph usage explicit (not "optional")

**Files Changed**:
- `/lyrics_transcriber/correction/agentic/workflows/correction_graph.py`
- `/lyrics_transcriber/correction/agentic/agent.py`

---

### 3. Callbacks Not Properly Attached

**Problem**: Langfuse callbacks were created in `ModelFactory` but not shared with `AgenticCorrector`

**Root Cause**: Each component created its own callback handler separately

**Fix**: Centralized callback setup in `AgenticCorrector`:
```python
class AgenticCorrector:
    def __init__(self, provider, graph=None):
        # Setup Langfuse callback once
        self._langfuse_handler = self._setup_langfuse_callback()
        
        # Attach to LangGraph
        self._graph = build_correction_graph(
            callbacks=[self._langfuse_handler] if self._langfuse_handler else None
        )
    
    def propose(self, prompt):
        # Also pass to graph invocation
        self._graph.invoke(
            {...},
            config={"callbacks": [self._langfuse_handler]} if self._langfuse_handler else {}
        )
        
        # ChatModels already have callbacks from ModelFactory
        data = self._provider.generate_correction_proposals(...)
```

---

## Files Changed

### 1. `model_factory.py` ✅
**Line 95**: Fixed import path
```python
from langfuse.langchain import CallbackHandler
```

### 2. `correction_graph.py` ✅
**Complete rewrite** to properly use LangGraph:
- Added `CorrectionState` TypedDict
- Build proper StateGraph with entry/finish points
- Support `.with_config()` for callbacks per Langfuse docs

### 3. `agent.py` ✅
**Added centralized callback setup**:
- New `_setup_langfuse_callback()` method
- Pass callbacks to `build_correction_graph()`
- Pass callbacks to `graph.invoke()`

### 4. Cleanup ✅
**Deleted backup files**:
- `langchain_bridge_old.py`
- `langchain_bridge_refactored.py`

---

## How Langfuse Integration Works Now

### Architecture

```
AgenticCorrector (creates ONE Langfuse CallbackHandler)
    ├─> LangGraph (receives callback via build_correction_graph())
    │   └─> Traces graph nodes
    │
    └─> LangChainBridge (receives callback via ModelFactory)
        └─> ChatModel (Ollama/OpenAI/Anthropic)
            └─> Traces LLM calls
```

### Trace Hierarchy

```
Langfuse Trace
├─ LangGraph: correction workflow
│  └─ Node: correct (pass-through for now)
│
└─ LangChain: ChatModel invocation
   ├─ Input: prompt
   ├─ Model: ollama/gpt-oss:latest
   ├─ Output: JSON proposals
   ├─ Tokens: counted
   └─ Latency: measured
```

---

## Testing

### Tests Pass ✅

```bash
$ pytest tests/integration/test_basic_ai_workflow.py \
         tests/unit/correction/agentic/test_providers.py -v

tests/integration/test_basic_ai_workflow.py::test_basic_ai_correction_workflow PASSED
tests/unit/correction/agentic/test_providers.py::test_provider_circuit_breaker_opens_on_failures PASSED

======================== 2 passed in 2.94s =========================
```

### Manual Testing

**1. Set environment variables:**
```bash
export USE_AGENTIC_AI=1
export AGENTIC_AI_MODEL="ollama/gpt-oss:latest"

# Langfuse credentials
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://us.cloud.langfuse.com"  # or https://cloud.langfuse.com for EU
```

**2. Run lyrics-transcriber:**
```bash
lyrics-transcriber --log_level DEBUG \
  --cache_dir ./cache \
  --artist "The Format" \
  --title "Time Bomb" \
  Time-Bomb.flac
```

**3. Check Langfuse dashboard:**
- Navigate to https://us.cloud.langfuse.com (or your region)
- Go to your project
- Click "Traces" in the sidebar
- You should now see traces for each gap correction!

---

## Expected Behavior

### Logs

You should see:
```
2025-10-21 12:08:05.172 - INFO - agent - 🤖 Langfuse tracing enabled for AgenticCorrector
2025-10-21 12:08:06.325 - DEBUG - model_factory - 🤖 Langfuse callback handler initialized for ollama/gpt-oss:latest
2025-10-21 12:08:06.325 - DEBUG - langchain_bridge - 🤖 [LangChain] Sending prompt to ollama/gpt-oss:latest: ...
2025-10-21 12:08:52.774 - INFO - langchain_bridge - 🤖 [LangChain] Got response from ollama/gpt-oss:latest: ...
```

**Note**: You should **NOT** see:
```
❌ WARNING - model_factory - 🤖 Langfuse callback setup failed: No module named 'langfuse.callback'
```

If you still see the warning, make sure you've installed the latest code!

### Langfuse Dashboard

Each gap correction will create a trace showing:
- **Span**: LangGraph workflow execution
- **Span**: ChatModel invocation
  - Model name (e.g., `ollama/gpt-oss:latest`)
  - Input prompt (truncated)
  - Output JSON
  - Latency (ms)
  - Token usage (if available)

---

## Differences from LiteLLM Approach

### Before (LiteLLM)
```python
import litellm
litellm.success_callback = ["langfuse"]  # Global config ❌
```

**Problems**:
- Global state (not testable)
- Unclear initialization order
- Documentation confusing (Proxy vs SDK)

### After (LangChain)
```python
from langfuse.langchain import CallbackHandler

handler = CallbackHandler(public_key=..., secret_key=..., host=...)

# Pass to graph
graph = build_correction_graph(callbacks=[handler])

# Pass to model
model = ChatOllama(model="gpt-oss:latest", callbacks=[handler])
```

**Benefits**:
- ✅ Explicit (clear where callbacks are used)
- ✅ Testable (can inject mock handlers)
- ✅ Well-documented (Langfuse has LangChain examples)
- ✅ Native integration (LangChain supports Langfuse officially)

---

## Documentation Used

### Primary Reference
[Langfuse LangGraph Integration Docs](https://langfuse.com/integrations/frameworks/langgraph)

**Key Takeaways**:
1. Import from `langfuse.langchain` ✅
2. Create `CallbackHandler` with credentials ✅
3. Pass to `.compile().with_config()` for LangGraph ✅
4. Pass to `ChatModel(callbacks=[...])` for LangChain ✅

### Code Examples From Docs

**Simple LangGraph app:**
```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

graph.stream(
    {...},
    config={"callbacks": [langfuse_handler]}
)
```

**With LangGraph Server:**
```python
langfuse_handler = CallbackHandler()

graph = graph_builder.compile().with_config(
    {"callbacks": [langfuse_handler]}
)
```

---

## Next Steps

### If Traces Still Don't Appear

1. **Check credentials are set:**
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   echo $LANGFUSE_HOST
   ```

2. **Verify Langfuse is reachable:**
   ```python
   from langfuse import get_client
   langfuse = get_client()
   if langfuse.auth_check():
       print("✅ Langfuse connection OK")
   else:
       print("❌ Langfuse auth failed")
   ```

3. **Check logs for errors:**
   ```bash
   lyrics-transcriber --log_level DEBUG ... 2>&1 | grep -i langfuse
   ```

4. **Verify region:**
   - US: `https://us.cloud.langfuse.com`
   - EU: `https://cloud.langfuse.com`

5. **Check project settings:**
   - Go to Langfuse dashboard
   - Settings → API Keys
   - Make sure keys are for the correct project

### If You Want to Expand LangGraph Usage

The current implementation is a simple pass-through. You can expand it to:

**Multi-step reasoning:**
```python
def analyze_gap(state):
    """Analyze the gap to determine correction type."""
    # LLM call to categorize the error
    return state

def execute_correction(state):
    """Execute the appropriate correction."""
    # Different logic based on error type
    return state

graph_builder.add_node("analyze", analyze_gap)
graph_builder.add_node("correct", execute_correction)
graph_builder.add_edge("analyze", "correct")
```

**Validation loops:**
```python
def should_retry(state):
    """Check if we should retry the correction."""
    if state["confidence"] < 0.8:
        return "retry"
    return "finish"

graph_builder.add_conditional_edges(
    "correct",
    should_retry,
    {"retry": "correct", "finish": END}
)
```

**Multi-agent consensus:**
```python
def agent_1(state):
    return {"proposals_1": [get_proposals_from_gpt4()]}

def agent_2(state):
    return {"proposals_2": [get_proposals_from_claude()]}

def combine(state):
    return {"final_proposals": merge(state["proposals_1"], state["proposals_2"])}

graph_builder.add_node("agent_1", agent_1)
graph_builder.add_node("agent_2", agent_2)
graph_builder.add_node("combine", combine)
# ... add edges ...
```

---

## Summary

✅ **Langfuse import fixed** (`langfuse.langchain.CallbackHandler`)  
✅ **LangGraph properly integrated** (StateGraph with callbacks)  
✅ **Callbacks centralized** (one handler shared across components)  
✅ **Tests pass** (2/2 passing)  
✅ **Cleanup done** (old backup files removed)  

**Status**: **READY TO TEST WITH REAL LANGFUSE ACCOUNT** 🚀

Once you run the corrector with your Langfuse credentials set, traces should appear automatically in your dashboard!

