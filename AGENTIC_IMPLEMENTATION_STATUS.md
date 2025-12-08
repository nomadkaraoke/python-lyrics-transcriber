# Agentic Correction System - Implementation Status

**Last Updated:** 2025-10-27
**Status:** Phase 1 and Phase 2 (Backend) Complete

## Overview

This document tracks the implementation of the classification-first agentic correction system with human feedback loop as specified in the plan.

## ✅ Completed

### Phase 1: Classification-First Correction Workflow

#### 1.1 Gap Classification Schema ✅
**File:** `lyrics_transcriber/correction/agentic/models/schemas.py`

- Added `GapCategory` enum with 8 categories:
  - `PUNCTUATION_ONLY`: Style differences only
  - `SOUND_ALIKE`: Homophones and similar-sounding errors
  - `BACKGROUND_VOCALS`: Transcribed backing vocals in parentheses
  - `EXTRA_WORDS`: Filler words like "And", "But"
  - `REPEATED_SECTION`: Chorus repetitions
  - `COMPLEX_MULTI_ERROR`: Large gaps with multiple error types
  - `AMBIGUOUS`: Unclear without audio
  - `NO_ERROR`: Matches at least one reference source

- Added `GapClassification` model with fields:
  - `gap_id`: Unique identifier
  - `category`: Gap category
  - `confidence`: 0-1 score
  - `reasoning`: Explanation
  - `suggested_handler`: Handler recommendation

- Updated `CorrectionProposal` with:
  - `gap_category`: Classification category
  - `requires_human_review`: Flag for manual review
  - `artist`, `title`: Song metadata
  - Added "NoAction" and "Flag" to action types

#### 1.2 Classification Prompt ✅
**File:** `lyrics_transcriber/correction/agentic/prompts/classifier.py`

- Created `build_classification_prompt()` function that:
  - Includes gap text, context, and reference lyrics from all sources
  - Includes artist/title for proper noun context
  - Provides few-shot examples from `gaps_review.yaml`
  - Requests structured JSON output matching `GapClassification` schema

- Implemented `load_few_shot_examples()` with:
  - Dynamic loading from `examples.yaml` (if exists)
  - Hardcoded fallback examples covering all categories
  - Examples extracted directly from your manual gap annotations

#### 1.3 Category-Specific Handlers ✅
**Files:** `lyrics_transcriber/correction/agentic/handlers/`

Implemented 8 handler classes:

1. **`PunctuationHandler`**: Returns NO_ACTION for style differences
2. **`NoErrorHandler`**: Returns NO_ACTION when reference matches
3. **`BackgroundVocalsHandler`**: Proposes DELETE for parenthesized content
4. **`ExtraWordsHandler`**: Detects and removes filler words
5. **`SoundAlikeHandler`**: Extracts replacement from reference context
6. **`RepeatedSectionHandler`**: Flags for human review
7. **`ComplexMultiErrorHandler`**: Flags complex gaps
8. **`AmbiguousHandler`**: Flags unclear cases

- Created `HandlerRegistry` for mapping categories to handlers
- All handlers extend `BaseHandler` abstract class
- Handlers return `CorrectionProposal` objects with metadata

#### 1.4 AgenticCorrector Workflow ✅
**File:** `lyrics_transcriber/correction/agentic/agent.py`

- Added `classify_gap()` method:
  - Builds classification prompt
  - Calls AI provider for classification
  - Returns `GapClassification` or None

- Added `propose_for_gap()` method implementing two-step workflow:
  1. Classify the gap using LLM
  2. Route to appropriate handler based on category
  3. Handler generates correction proposals
  4. Add metadata (artist, title, category) to proposals
  5. Handle errors gracefully with fallback to FLAG

- Kept legacy `propose()` method marked as deprecated

#### 1.5 LyricsCorrector Integration ✅
**File:** `lyrics_transcriber/correction/corrector.py`

- Updated agentic correction section to:
  - Prepare structured gap data (words with IDs, times)
  - Extract context (10 preceding/following words)
  - Build reference contexts from all sources
  - Pass artist and title from metadata
  - Call new `propose_for_gap()` method instead of old prompt-based approach

### Phase 2: Human Feedback Collection System (Backend)

#### 2.1 Correction Annotation Schema ✅
**File:** `lyrics_transcriber/correction/feedback/schemas.py`

- Created `CorrectionAnnotationType` enum (9 types including MANUAL_EDIT)
- Created `CorrectionAction` enum (7 actions: NO_ACTION, REPLACE, DELETE, INSERT, MERGE, SPLIT, FLAG)

- Created `CorrectionAnnotation` model with:
  - Unique `annotation_id` (UUID)
  - Song identification (`audio_hash`, `artist`, `title`)
  - Classification (`annotation_type`, `action_taken`)
  - Content (`original_text`, `corrected_text`)
  - Human metadata (`confidence` 1-5, `reasoning` min 10 chars)
  - Agentic comparison (`agentic_proposal`, `agentic_category`, `agentic_agreed`)
  - Reference tracking (`reference_sources_consulted`)
  - Session tracking (`session_id`, `timestamp`)

- Created `AnnotationStatistics` for aggregated metrics

#### 2.2 Feedback Storage Backend ✅
**File:** `lyrics_transcriber/correction/feedback/store.py`

- Implemented `FeedbackStore` class with JSONL storage:
  - File: `{cache_dir}/correction_annotations.jsonl`
  - One annotation per line for easy appending
  - Automatic datetime serialization/deserialization

- Methods implemented:
  - `save_annotation()`: Save single annotation
  - `save_annotations()`: Batch save
  - `get_all_annotations()`: Load all with error recovery
  - `get_annotations_by_song()`: Filter by audio hash
  - `get_annotations_by_category()`: Filter by type
  - `get_statistics()`: Aggregate metrics (counts, averages, patterns)
  - `export_to_training_data()`: Export high-confidence annotations for fine-tuning

#### 2.3 Backend API Endpoints ✅
**File:** `lyrics_transcriber/review/server.py`

- Initialized `NewFeedbackStore` in `ReviewServer.__init__()`
- Added 3 new API endpoints:
  - `POST /api/v1/annotations`: Save annotation with validation
  - `GET /api/v1/annotations/{audio_hash}`: Get annotations for song
  - `GET /api/v1/annotations/stats`: Get aggregated statistics

- All endpoints include proper error handling and HTTP status codes

## 🚧 In Progress / Not Started

### Phase 2: Human Feedback Collection (Frontend)

#### 2.4 UI Annotation Modal Component ⏳
**File:** `lyrics_transcriber/frontend/src/components/CorrectionAnnotationModal.tsx` (to create)

**Required:** React modal component with:
- Annotation type dropdown (9 categories)
- Confidence slider (1-5 scale)
- Reasoning textarea (required, min 10 chars)
- Display of agentic AI suggestion (if applicable)
- Display of reference lyrics context
- "Save & Continue" and "Skip" buttons
- Local state management until final submission

#### 2.5 Edit Workflow Integration ⏳
**Files:** 
- `lyrics_transcriber/frontend/src/components/EditModal.tsx`
- `lyrics_transcriber/frontend/src/components/EditWordList.tsx`

**Required:** Wrap edit actions to trigger annotation modal:
- Show modal after user confirms word edit/delete/merge/split
- Collect annotation data in React state
- Submit all annotations on "Finish Review"
- Add settings toggle for "Enable correction annotations"

#### 2.6 Frontend Types and API Client ⏳
**Files:**
- `lyrics_transcriber/frontend/src/types.ts`
- `lyrics_transcriber/frontend/src/api.ts`

**Required:**
- Add `CorrectionAnnotation` TypeScript interface
- Add `submitAnnotations()` method to API client
- Add `getAnnotationStats()` method

### Phase 3: Continuous Improvement Infrastructure

#### 3.1 Analysis Scripts ⏳
**File:** `scripts/analyze_annotations.py` (to create)

**Required:** Python script that:
- Loads all annotations from JSONL
- Generates Markdown report with:
  - Most common error categories
  - Agentic AI accuracy by category
  - Frequently mis-heard words/phrases
  - Cases where reference lyrics were wrong
- Outputs to `CORRECTION_ANALYSIS.md`

#### 3.2 Few-Shot Example Generator ⏳
**File:** `scripts/generate_few_shot_examples.py` (to create)

**Required:** Python script that:
- Selects high-confidence annotations (confidence >= 4)
- Formats as YAML prompt examples
- Outputs to `lyrics_transcriber/correction/agentic/prompts/examples.yaml`
- Can be run periodically to update classifier

#### 3.3 Classifier Dynamic Examples ⏳
**File:** `lyrics_transcriber/correction/agentic/prompts/classifier.py` (update)

**Required:** 
- Already has `load_few_shot_examples()` infrastructure
- Will automatically load from `examples.yaml` if file exists
- No changes needed - just need to generate the YAML file

#### 3.4 Feedback Loop Documentation ⏳
**File:** `HUMAN_FEEDBACK_LOOP.md` (to create)

**Required:** Document:
- How to use annotation collection in UI
- How to run analysis scripts
- How to regenerate few-shot examples
- How to evaluate improvement over time
- Path to fine-tuning custom model with RLHF

### Phase 4: Testing and Validation

#### 4.1 Unit Tests ⏳
**File:** `tests/unit/correction/test_classifier.py` (to create)

**Required:** Test cases for:
- Gap classifier with examples from `gaps_review.yaml`
- Each category handler
- Edge cases (ambiguous, no reference match)

#### 4.2 Integration Tests ⏳
**File:** `tests/integration/test_agentic_workflow.py` (update)

**Required:** End-to-end tests:
- Classification → correction flow
- Use Time Bomb song as fixture
- Verify correct handlers are invoked
- Verify FLAG actions for ambiguous cases

#### 4.3 Feedback System Tests ⏳
**File:** `tests/unit/correction/test_feedback_store.py` (to create)

**Required:** Test cases for:
- Save and retrieve annotations
- JSONL format correctness
- Statistics generation
- Training data export

## Testing the Implementation

### Backend Testing (Can be done now)

1. **Test Classification Workflow:**
```bash
USE_AGENTIC_AI=1 python -m lyrics_transcriber.cli.cli_main Time-Bomb.flac \
  --artist "Rancid" --title "Time Bomb"
```

Expected: Gaps will be classified into categories, handlers will propose corrections

2. **Test Annotation Storage:**
```python
from lyrics_transcriber.correction.feedback.store import FeedbackStore
from lyrics_transcriber.correction.feedback.schemas import CorrectionAnnotation, CorrectionAnnotationType, CorrectionAction

store = FeedbackStore("cache")
annotation = CorrectionAnnotation(
    audio_hash="test123",
    annotation_type=CorrectionAnnotationType.SOUND_ALIKE,
    action_taken=CorrectionAction.REPLACE,
    original_text="out",
    corrected_text="now",
    confidence=5.0,
    reasoning="Reference lyrics confirm it should be 'now'",
    artist="Rancid",
    title="Time Bomb",
    session_id="test_session"
)
store.save_annotation(annotation)
stats = store.get_statistics()
print(stats)
```

3. **Test API Endpoints:**
```bash
# Start review server and test endpoints
curl -X POST http://localhost:8000/api/v1/annotations \
  -H "Content-Type: application/json" \
  -d '{"audio_hash": "test", "annotation_type": "sound_alike", ...}'

curl http://localhost:8000/api/v1/annotations/stats
```

### Frontend Testing (Once UI is implemented)

1. Open review UI
2. Make a correction (edit/delete/merge word)
3. Annotation modal should appear
4. Fill in annotation details
5. Click "Save & Continue"
6. Make more corrections
7. Click "Finish Review"
8. Check `cache/correction_annotations.jsonl` for saved data

## Architecture Decisions

### Classification-First Approach
- **Why:** Breaks complex problem into simpler steps
- **Benefit:** Each handler can focus on one error type
- **Trade-off:** Two LLM calls per gap (classification + handler logic), but handlers are deterministic

### JSONL Storage
- **Why:** Simple, append-only, no database required
- **Benefit:** Easy to parse, version control friendly, portable
- **Trade-off:** Not suitable for millions of annotations (but we expect hundreds/thousands)

### Fail-Fast on Errors
- **Why:** Better to flag for human review than make wrong correction
- **Benefit:** Maintains transcription quality
- **Trade-off:** More human review needed initially (improves over time with feedback)

### Handler Registry Pattern
- **Why:** Easy to add new category handlers
- **Benefit:** Extensible, testable, follows Open/Closed Principle
- **Trade-off:** Slightly more complex than if/else routing

## Next Steps

**Priority 1 (Required for feedback loop):**
1. Implement `CorrectionAnnotationModal.tsx`
2. Integrate modal into edit workflow
3. Update frontend types and API client
4. Test end-to-end annotation collection

**Priority 2 (Analysis and improvement):**
5. Create `analyze_annotations.py` script
6. Create `generate_few_shot_examples.py` script
7. Generate initial `examples.yaml` from collected data
8. Document feedback loop in `HUMAN_FEEDBACK_LOOP.md`

**Priority 3 (Validation):**
9. Write unit tests for classifiers and handlers
10. Write integration tests for full workflow
11. Write tests for feedback store

## Files Created

### Python Backend
- `lyrics_transcriber/correction/agentic/models/schemas.py` (updated)
- `lyrics_transcriber/correction/agentic/prompts/__init__.py` (new)
- `lyrics_transcriber/correction/agentic/prompts/classifier.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/__init__.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/base.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/punctuation.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/no_error.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/background_vocals.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/extra_words.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/sound_alike.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/repeated_section.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/complex_multi_error.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/ambiguous.py` (new)
- `lyrics_transcriber/correction/agentic/handlers/registry.py` (new)
- `lyrics_transcriber/correction/agentic/agent.py` (updated)
- `lyrics_transcriber/correction/corrector.py` (updated)
- `lyrics_transcriber/correction/feedback/__init__.py` (new)
- `lyrics_transcriber/correction/feedback/schemas.py` (new)
- `lyrics_transcriber/correction/feedback/store.py` (new)
- `lyrics_transcriber/review/server.py` (updated)

### Documentation
- `AGENTIC_IMPLEMENTATION_STATUS.md` (this file)

## Known Issues / Limitations

1. **Classification accuracy depends on LLM quality**
   - Solution: Use better models (GPT-4, Claude Sonnet) for classification
   - Solution: Collect human feedback to improve prompts

2. **SoundAlikeHandler may fail to extract replacement**
   - Fallback: Flags for human review
   - Future: Use fuzzy matching and phonetic algorithms

3. **No A/B testing framework yet**
   - Can't compare different prompt versions easily
   - Future enhancement: Track model performance over time

4. **Frontend not implemented**
   - Can't collect human feedback yet
   - Priority for next implementation phase

## Fixes Applied

### Enum Value Case Mismatch (2025-10-27)
**Issue:** LLM was returning category values in uppercase (e.g., `"SOUND_ALIKE"`) but Pydantic enum expected lowercase with underscores (e.g., `"sound_alike"`), causing validation errors.

**Fix:** Updated all enum values in `GapCategory` and `CorrectionAnnotationType` to use uppercase format that LLMs naturally return. Also updated the prompt to explicitly show the expected format.

**Files Changed:**
- `lyrics_transcriber/correction/agentic/models/schemas.py`
- `lyrics_transcriber/correction/feedback/schemas.py`
- `lyrics_transcriber/correction/agentic/prompts/classifier.py`

### JSON Parsing with Invalid Escapes (2025-10-27)
**Issue:** LLM responses contained invalid JSON escape sequences like `\'` (e.g., in `"out, I\'m"`), which caused JSON parsing to fail. Python's json.loads() only allows specific escape sequences (`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`).

**Fix:** Enhanced `ResponseParser` to automatically fix common JSON issues before parsing:
- Replace invalid `\'` with `'` (single quotes don't need escaping in JSON)
- Remove trailing commas before `}` or `]`
- Retry parsing after fixes before falling back to raw response

**Files Changed:**
- `lyrics_transcriber/correction/agentic/providers/response_parser.py`

**Result:** System now handles LLM responses with imperfect JSON formatting gracefully.

## Performance Considerations

- **Two LLM calls per gap:** Classification + handler logic (if handler needs LLM)
  - Most handlers are deterministic (no LLM call)
  - Only `SoundAlikeHandler` might need LLM for complex cases
  
- **JSONL file grows linearly:**
  - ~1KB per annotation
  - 1000 annotations = ~1MB
  - Should be fine for years of use
  
- **Frontend modal after each edit:**
  - Could be annoying for many edits
  - Consider: Batch annotation at end instead
  - Add "Skip" button and settings toggle

## Success Metrics

Once implemented, track:
1. **Annotation Collection Rate:** % of corrections that get annotated
2. **Agentic Agreement Rate:** % where human agrees with AI proposal
3. **Classification Accuracy:** % correctly classified by category (human-verified)
4. **Correction Quality Over Time:** Track accuracy improvements as more feedback collected
5. **Human Review Rate:** % of gaps flagged vs auto-corrected (should decrease over time)

## References

- Original plan: `.cursor/plans/agentic-correction-system-*.plan.md`
- Manual gap annotations: `gaps_review.yaml`
- Test song: `Time-Bomb.flac` by Rancid

