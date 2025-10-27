<!-- 5ddf541b-8e90-4e85-9152-c52f39be9149 010e2c40-4a44-4364-afad-04889d79cdc1 -->
# Agentic Correction System with Human Feedback Loop

## Phase 1: Classification-First Correction Workflow

### 1.1 Create Gap Classification Schema

**File**: `lyrics_transcriber/correction/agentic/models/schemas.py`

Add new Pydantic models for gap classification:

- `GapCategory` enum: `PUNCTUATION_ONLY`, `SOUND_ALIKE`, `BACKGROUND_VOCALS`, `EXTRA_WORDS`, `REPEATED_SECTION`, `COMPLEX_MULTI_ERROR`, `AMBIGUOUS`, `NO_ERROR`
- `GapClassification` model with fields:
- `gap_id`: str
- `category`: GapCategory
- `confidence`: float (0-1)
- `reasoning`: str
- `suggested_handler`: Optional[str]
- Update `CorrectionProposal` to include:
- `gap_category`: Optional[GapCategory]
- `requires_human_review`: bool
- `artist`: Optional[str]
- `title`: Optional[str]

### 1.2 Build Classification Prompt

**File**: `lyrics_transcriber/correction/agentic/prompts/classifier.py` (new)

Create prompt template for gap classification:

- Include: gap text, preceding/following context, reference lyrics from all sources
- Include: artist name, song title (from metadata)
- Ask LLM to categorize gap and explain reasoning
- Provide examples from `gaps_review.yaml` for few-shot learning
- Request structured JSON output matching `GapClassification` schema

### 1.3 Implement Category-Specific Handlers

**File**: `lyrics_transcriber/correction/agentic/handlers/` (new directory)

Create handler classes for each category:

- `PunctuationHandler`: Returns NO_ACTION if only punctuation differs
- `SoundAlikeHandler`: Uses reference lyrics to propose REPLACE actions
- `BackgroundVocalsHandler`: Detects parentheses and proposes DELETE
- `ExtraWordsHandler`: Detects common filler words ("And", "But") and proposes DELETE
- `RepeatedSectionHandler`: Flags for human review with context about chorus/verse structure
- `ComplexMultiErrorHandler`: Breaks into smaller sub-gaps or flags for review
- `AmbiguousHandler`: Always flags for human review
- `NoErrorHandler`: Returns NO_ACTION when any reference source matches

Each handler returns list of `CorrectionProposal` objects.

### 1.4 Update AgenticCorrector Workflow

**File**: `lyrics_transcriber/correction/agentic/agent.py`

Modify `propose()` method to use two-step process:

1. Call classifier to categorize gap
2. Route to appropriate handler based on category
3. Collect proposals from handler
4. Add metadata: artist, title, session_id

### 1.5 Update LyricsCorrector Integration

**File**: `lyrics_transcriber/correction/corrector.py`

In `_process_corrections()` method:

- Pass artist and title from metadata to `AgenticCorrector`
- Handle FLAG action type (new) by marking proposals for human review
- Store gap classification data in correction_steps for later analysis

## Phase 2: Human Feedback Collection System

### 2.1 Define Correction Annotation Schema

**File**: `lyrics_transcriber/correction/feedback/schemas.py` (new)

Create Pydantic models:

- `CorrectionAnnotationType` enum: matches gap categories plus `MANUAL_EDIT`
- `CorrectionAnnotation` model:
- `annotation_id`: str (UUID)
- `audio_hash`: str
- `gap_id`: Optional[str]
- `annotation_type`: CorrectionAnnotationType
- `original_text`: str
- `corrected_text`: str
- `action_taken`: str (NO_ACTION, REPLACE, DELETE, INSERT, MERGE, SPLIT, FLAG)
- `confidence`: float (1-5 scale)
- `reasoning`: str (required human explanation)
- `word_ids_affected`: List[str]
- `agentic_proposal`: Optional[Dict] (what the AI suggested)
- `agentic_category`: Optional[GapCategory]
- `reference_sources_consulted`: List[str]
- `timestamp`: datetime
- `artist`: str
- `title`: str
- `session_id`: str

### 2.2 Create Feedback Storage Backend

**File**: `lyrics_transcriber/correction/feedback/store.py` (new)

Implement `FeedbackStore` class:

- Uses JSON file storage in cache directory: `correction_annotations.jsonl`
- Each line is one annotation (JSONL format for easy appending)
- Methods:
- `save_annotation(annotation: CorrectionAnnotation)`
- `get_annotations_by_song(audio_hash: str)`
- `get_annotations_by_category(category: str)`
- `export_to_training_data()` (for future fine-tuning)
- `get_statistics()` (aggregations for analysis)

### 2.3 Update Backend API Endpoints

**File**: `lyrics_transcriber/review/server.py`

Add new endpoints:

- `POST /api/v1/annotations` - Save correction annotation
- `GET /api/v1/annotations/{audio_hash}` - Get annotations for song
- `GET /api/v1/annotations/stats` - Get aggregated statistics

Update existing endpoint:

- `POST /api/v1/submit` - Also save annotations when corrections submitted

### 2.4 Create UI Annotation Modal Component

**File**: `lyrics_transcriber/frontend/src/components/CorrectionAnnotationModal.tsx` (new)

Build modal that appears when user makes corrections:

- Triggered when: user edits word, deletes word, merges/splits, etc.
- Form fields:
- Annotation type (dropdown with categories)
- Confidence slider (1-5)
- Reasoning text area (required, min 10 chars)
- Display: what agentic AI suggested (if applicable)
- Display: reference lyrics context
- "Save & Continue" and "Skip" buttons
- Store annotations locally until final submission

### 2.5 Integrate Annotation Collection into Edit Workflow

**Files**:

- `lyrics_transcriber/frontend/src/components/EditModal.tsx`
- `lyrics_transcriber/frontend/src/components/EditWordList.tsx`

Wrap edit actions to capture annotations:

- After user confirms word edit, show annotation modal
- Store annotation in React state
- Submit all annotations when user clicks "Finish Review"
- Add settings toggle: "Enable correction annotations" (default: true)

### 2.6 Update Frontend Types and API Client

**Files**:

- `lyrics_transcriber/frontend/src/types.ts` - Add `CorrectionAnnotation` interface
- `lyrics_transcriber/frontend/src/api.ts` - Add `submitAnnotations()` method

## Phase 3: Continuous Improvement Infrastructure

### 3.1 Create Analysis Scripts

**File**: `scripts/analyze_annotations.py` (new)

Script to analyze collected annotations:

- Load all annotations from JSONL file
- Generate reports:
- Most common error categories
- Agentic AI accuracy by category
- Frequently mis-heard words/phrases
- Cases where reference lyrics were wrong
- Output Markdown report to `CORRECTION_ANALYSIS.md`

### 3.2 Build Few-Shot Example Generator

**File**: `scripts/generate_few_shot_examples.py` (new)

Script to convert annotations into few-shot examples:

- Select high-confidence annotations (4-5 rating)
- Format as prompt examples for classifier
- Output to `lyrics_transcriber/correction/agentic/prompts/examples.yaml`
- Can be loaded by classifier prompt builder

### 3.3 Update Classifier with Examples

**File**: `lyrics_transcriber/correction/agentic/prompts/classifier.py`

Modify to:

- Load examples from `examples.yaml`
- Include top N examples for each category in prompt
- Dynamically update as more annotations collected

### 3.4 Add Feedback Loop Documentation

**File**: `HUMAN_FEEDBACK_LOOP.md` (new)

Document the full feedback loop process:

- How to use annotation collection in UI
- How to run analysis scripts
- How to regenerate few-shot examples
- How to evaluate improvement over time
- Future: Path to fine-tuning custom model with RLHF

## Phase 4: Testing and Validation

### 4.1 Create Unit Tests

**File**: `tests/unit/correction/test_classifier.py` (new)

Test gap classifier with examples from `gaps_review.yaml`:

- Verify correct categorization for each gap type
- Test edge cases (ambiguous gaps, no reference match)

### 4.2 Create Integration Tests

**File**: `tests/integration/test_agentic_workflow.py` (update)

Test full classification → correction flow:

- Use Time Bomb song as fixture
- Verify gaps are correctly classified
- Verify appropriate handlers are invoked
- Verify FLAG actions are generated for ambiguous cases

### 4.3 Create Feedback System Tests

**File**: `tests/unit/correction/test_feedback_store.py` (new)

Test annotation storage:

- Save and retrieve annotations
- JSONL format correctness
- Statistics generation

## Implementation Order

1. Phase 1.1-1.3: Classification infrastructure (schemas, prompts, handlers)
2. Phase 1.4-1.5: Integrate into existing workflow
3. Phase 2.1-2.3: Backend feedback storage
4. Phase 2.4-2.6: UI annotation collection
5. Phase 3.1-3.3: Analysis and improvement tools
6. Phase 4: Testing
7. Phase 3.4: Documentation

## Future Enhancements (Out of Scope)

- Fine-tune small LLM (e.g., Llama 3.1-8B) using collected annotations
- Implement RLHF workflow with human preference rankings
- A/B testing framework for comparing classifier versions
- Active learning: prioritize flagging gaps where model is most uncertain

### To-dos

- [ ] Create gap classification schemas and update CorrectionProposal model
- [ ] Build classification prompt template with few-shot examples from gaps_review.yaml
- [ ] Implement category-specific handler classes for each gap type
- [ ] Update AgenticCorrector to use two-step classification workflow
- [ ] Update LyricsCorrector to pass metadata and handle FLAG actions
- [ ] Define CorrectionAnnotation schema and related types
- [ ] Implement FeedbackStore with JSONL storage
- [ ] Add annotation API endpoints to review server
- [ ] Create CorrectionAnnotationModal component
- [ ] Integrate annotation collection into edit workflow
- [ ] Create annotation analysis script
- [ ] Build few-shot example generator from annotations
- [ ] Update classifier to load dynamic few-shot examples
- [ ] Write comprehensive tests for all new components
- [ ] Document the human feedback loop and improvement process