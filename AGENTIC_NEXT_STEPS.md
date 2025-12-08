# Agentic AI Corrector - Next Steps

## Current Status ✅

- ✅ Sessions working - All traces grouped in Langfuse
- ✅ LangChain + LangGraph integrated
- ✅ Circuit breaker and retry logic
- ✅ Observability with Langfuse
- ✅ Gap extraction code added to `corrector.py`

## Problems Identified 🔍

### 1. Adapter Always Returns 0 Corrections
**Root Cause**: LLM proposals don't include `word_id`, so the adapter can't map them to actual words.

**Why**: The prompt doesn't:
- Provide structured word data with IDs
- Request word IDs in the response
- Give enough context for unambiguous identification

### 2. LLM Proposals Are Too Aggressive
**Issue**: LLM suggests corrections for stylistic differences (quotes, spacing, etc.) that don't need fixing.

**Why**: No classification step - the LLM jumps straight to proposing actions without first determining if the gap needs correction.

### 3. Proposals Lack Actionable Detail
**Issue**: Responses like `"replacement_text": "I'm gonna"` don't specify:
- Which word to replace
- Where to insert it
- What to do with surrounding words

**Why**: The prompt is too vague and doesn't enforce structured, unambiguous actions.

## Next Steps 📋

### Step 1: Extract Gap Data (YOU)
Run this command:
```bash
DUMP_GAPS=1 USE_AGENTIC_AI=0 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
```

This creates `gaps_review.yaml` with all gap data.

### Step 2: Manual Annotation (YOU)
Open `gaps_review.yaml` and for each gap (recommend doing 10-20), fill in:

```yaml
annotations:
  your_decision: "Replace 'out,' with 'now'"
  action_type: "REPLACE"
  target_word_ids: ["w7"]
  replacement_text: "now"
  notes: "Transcription error - reference says 'now'"
```

See `HOW_TO_EXTRACT_GAPS.md` for detailed examples.

### Step 3: Workflow Redesign (ME)
Based on your annotations, I'll:

#### A. Fix the Prompt
```python
prompt = f"""You are correcting transcription errors in song lyrics.

TRANSCRIBED WORDS (may contain errors):
{json.dumps([{"id": w.id, "text": w.text, "time": w.start_time} for w in gap_words], indent=2)}

REFERENCE LYRICS CONTEXT:
{ref_text}

TASK:
1. First, classify if this gap needs correction:
   - Compare transcribed words to reference
   - Ignore stylistic differences (quotes, punctuation, spacing)
   - Only flag actual transcription errors

2. If correction is needed, propose actions with specific word IDs:
   - Use the "id" field to identify which word(s) to operate on
   - Be precise and unambiguous

OUTPUT FORMAT:
{{
  "needs_correction": true/false,
  "reason": "Brief explanation",
  "proposals": [
    {{
      "target_word_ids": ["w7"],  // Which words to operate on
      "action": "REPLACE",
      "replacement_text": "now",
      "confidence": 0.95,
      "reason": "Transcription error"
    }}
  ]
}}
"""
```

#### B. Update the Schema
```python
class CorrectionDecision(BaseModel):
    needs_correction: bool
    reason: str
    proposals: List[CorrectionProposal]

class CorrectionProposal(BaseModel):
    target_word_ids: List[str]  # Now required!
    action: Literal["REPLACE", "DELETE", "INSERT", "MERGE", "SPLIT", "NO_ACTION"]
    replacement_text: Optional[str]
    insert_position: Optional[Literal["before", "after"]]  # For INSERT
    confidence: float
    reason: str
```

#### C. Fix the Adapter
```python
def adapt_proposals_to_word_corrections(
    decision: CorrectionDecision,
    word_map: Dict[str, Word],
    linear_position_map: Dict[str, int],
) -> List[WordCorrection]:
    """Convert proposals with proper word ID mapping."""
    if not decision.needs_correction:
        return []  # Early exit
    
    results = []
    for proposal in decision.proposals:
        # Now we have target_word_ids!
        for word_id in proposal.target_word_ids:
            if word_id not in word_map:
                logger.warning(f"Word ID {word_id} not found in word_map")
                continue
            
            word = word_map[word_id]
            # ... create WordCorrection with proper mapping
```

### Step 4: Testing (ME)
- Update integration tests
- Verify proposals → corrections flow works
- Check Langfuse traces show proper structure

### Step 5: Iteration (BOTH)
- Run on Time-Bomb with new workflow
- Compare results to your annotations
- Refine prompt/schema based on accuracy

## Expected Outcome 🎯

After this iteration:
- ✅ LLM proposals include word IDs
- ✅ Adapter successfully creates corrections
- ✅ Classification step reduces false positives
- ✅ Actions are precise and unambiguous
- ✅ You see actual corrections being applied

## Timeline

- **Now**: Gap extraction code is ready
- **You**: Extract and annotate gaps (30-60 min?)
- **Me**: Redesign based on annotations (1-2 hours)
- **Together**: Test and iterate (30 min)

Ready to extract those gaps? 🚀

