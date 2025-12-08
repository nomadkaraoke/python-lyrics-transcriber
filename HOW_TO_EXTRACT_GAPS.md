# How to Extract Gaps for Manual Review

## Quick Start

I've added temporary gap extraction code to `corrector.py`. To use it:

```bash
DUMP_GAPS=1 USE_AGENTIC_AI=0 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
```

This will:
1. Fetch reference lyrics (needed to find gaps!)
2. Run transcription
3. Find anchor sequences and identify gaps
4. Dump all gap data to `gaps_review.yaml`
5. Exit before making any corrections

## What You'll Get

`gaps_review.yaml` will contain all gaps with this structure:

```yaml
gaps:
- gap_id: 1
  position: 7
  gap_text: "out, I'm starting over I'm"
  transcribed_words:
  - id: w7
    text: out,
    start_time: 10.532
    end_time: 10.817
  - id: w8
    text: I'm
    start_time: 10.871
    end_time: 11.065
  - id: w9
    text: starting
    start_time: 11.129
    end_time: 11.486
  # ... more words
  reference_context: "Starting now I'm starting over I'm gonna sleep in all my..."
  word_count: 5
  annotations:
    your_decision: ""
    action_type: "# NO_ACTION | REPLACE | DELETE | INSERT | MERGE | SPLIT"
    target_word_ids: []
    replacement_text: ""
    notes: ""
```

## How to Annotate

For each gap, fill in the `annotations` section:

### Example 1: Replace a word
```yaml
annotations:
  your_decision: "Replace 'out,' with 'now' - transcription error"
  action_type: "REPLACE"
  target_word_ids: ["w7"]
  replacement_text: "now"
  notes: "Reference says 'now I'm starting over'"
```

### Example 2: No action needed
```yaml
annotations:
  your_decision: "Gap is fine - just stylistic difference (quote marks)"
  action_type: "NO_ACTION"
  target_word_ids: []
  replacement_text: ""
  notes: "Transcription used straight quotes, reference uses curly quotes"
```

### Example 3: Insert missing word
```yaml
annotations:
  your_decision: "Missing word 'gonna' after 'I'm'"
  action_type: "INSERT"
  target_word_ids: ["w11"]  # Insert after this word
  replacement_text: "gonna"
  notes: "Reference says 'I'm gonna sleep' but transcription missed 'gonna'"
```

### Example 4: Delete word
```yaml
annotations:
  your_decision: "Word 'well' is not in reference lyrics"
  action_type: "DELETE"
  target_word_ids: ["w15"]
  replacement_text: ""
  notes: "Transcription added 'well' that doesn't belong"
```

## After Annotating

Once you've reviewed and annotated 10-20 gaps, share `gaps_review.yaml` with me and I'll:

1. **Redesign the prompt** to:
   - Provide structured word data (IDs, timestamps)
   - Request specific word IDs in responses
   - Add a classification step ("needs correction?")
   - Break complex changes into multiple proposals

2. **Fix the adapter** to:
   - Properly map word IDs from proposals
   - Handle all action types
   - Validate proposals before applying

3. **Improve the workflow** to:
   - Add multi-step reasoning
   - Include confidence thresholds
   - Handle edge cases you identify

## Removing Temporary Code

After extraction, you can remove the `=== TEMPORARY ===` block from `corrector.py` (lines 286-345) or just leave it - it only runs when `DUMP_GAPS=1`.

## Current Issues (Why We Need This)

1. **LLM doesn't know word IDs** - Prompt doesn't provide them
2. **Adapter can't map** - Proposals have no word_id field
3. **LLM tries too hard** - Suggests fixes for stylistic differences
4. **No classification** - Doesn't determine if action is needed first

Your annotations will help us fix all of these!

