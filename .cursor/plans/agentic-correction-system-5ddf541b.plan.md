<!-- 5ddf541b-8e90-4e85-9152-c52f39be9149 f7f98f98-6fab-4b10-9382-4948916b84e2 -->
# Agentic Correction UI Improvements

## Overview

Transform the correction UI to be mobile-first with visual duration indicators, inline correction actions, and category-based metrics specifically designed for agentic AI workflows.

## Core Changes

### 1. Visual Duration Indicators for Words

Transform the Corrected Transcription view to show word durations at a glance.

**File: `lyrics_transcriber/frontend/src/components/TranscriptionView.tsx`**

- Add toggle mode: "Text View" (current) vs "Duration View" (new)
- In Duration View, render each line as a timeline bar similar to TimelineEditor
- Each word rendered as a colored bar with width proportional to duration
- Color coding:
  - Normal words: light gray
  - Corrected words (agentic): green with original word shown above in small gray text
  - Uncorrected gaps: orange/red
  - Anchors: blue
- Show time ruler above each line
- Flag abnormally long words (>2 seconds) with warning indicator
- Mobile-optimized: Scrollable horizontally if needed, bars tall enough for touch

**Implementation approach:**

- Create new component `DurationTimelineView.tsx` based on TimelineEditor logic
- Reuse `timeToPosition` calculation from TimelineEditor
- Group words by segment/line
- Show original word above corrected word: `<Box sx={{fontSize: '0.6rem', color: 'text.secondary'}}>{originalWord}</Box>`

### 2. Inline Correction Actions

Add touch-friendly action buttons directly on corrected words.

**File: `lyrics_transcriber/frontend/src/components/shared/components/Word.tsx`**

Current implementation only shows tooltip. Enhance to:

- When a word has a correction, render with action buttons
- Position buttons in a small action bar that appears inline (not on hover, always visible on mobile)
- Actions:
  - Undo icon (revert to original)
  - Edit icon (open edit modal)
  - Checkmark icon (accept/approve)
- On mobile: Buttons always visible, adequate size (44px touch target)
- On desktop: Can show on hover for cleaner look
- Style: Subtle, icon-only buttons in a compact horizontal strip
- Use Material-UI IconButton with small size

**New component: `CorrectedWordWithActions.tsx`**

```tsx
interface CorrectedWordWithActionsProps {
  word: string
  originalWord: string
  correction: CorrectionInfo
  onRevert: () => void
  onEdit: () => void
  onAccept: () => void
  isMobile: boolean
}
```

### 3. Transform Correction Handlers to Category Metrics

Replace handler toggles with agentic-specific category breakdown.

**File: `lyrics_transcriber/frontend/src/components/Header.tsx`**

When agentic mode detected (check if AgenticCorrector exists in handlers):

- Replace handler toggles with category breakdown
- Show gap categories from `GapCategory` enum:
  - SOUND_ALIKE (5)
  - PUNCTUATION_ONLY (2)
  - BACKGROUND_VOCALS (1)
  - etc.
- Sort by count descending
- Make clickable to filter/highlight those corrections in view
- Add quick filter chips: "Low Confidence" (<60%), "High Confidence" (>80%)
- Show average confidence score for all agentic corrections

**Implementation:**

- Add function to aggregate corrections by `gap_category` field from reason string
- Parse reason field: extract text between `[` and `]` for category
- Create new component `AgenticCorrectionMetrics.tsx`

### 4. Enhanced Correction Detail View

Replace cramped tooltip with rich, touch-friendly correction card.

**New component: `CorrectionDetailCard.tsx`**

Triggered by clicking on a corrected word (not hover):

- Modal or slide-up panel on mobile (bottom sheet style)
- Popover on desktop
- Content:
  - Large display of original → corrected
  - Category badge with icon
  - Confidence meter (progress bar)
  - Full reasoning text (multi-line, readable)
  - Reference context snippet (if available)
  - Action buttons (large, clear labels):
    - "Revert to Original"
    - "Edit Correction"
    - "Mark as Correct"
    - "Report Issue" (future: submit to feedback API)
- Swipe to dismiss on mobile
- Escape key to close on desktop

### 5. Update Data Types

**File: `lyrics_transcriber/frontend/src/types.ts`**

Add:

```typescript
export interface CorrectionAction {
  type: 'revert' | 'edit' | 'accept' | 'reject'
  correctionId: string
  wordId: string
}

export interface GapCategoryMetric {
  category: string
  count: number
  avgConfidence: number
}
```

### 6. State Management for Correction Actions

**File: `lyrics_transcriber/frontend/src/components/LyricsAnalyzer.tsx`**

Add handlers:

- `handleRevertCorrection(wordId: string)`: Restore original word
- `handleEditCorrection(wordId: string)`: Open edit modal with original word
- `handleAcceptCorrection(wordId: string)`: Mark as approved (future: track in annotation system)

Implement revert:

- Find correction by word_id or corrected_word_id
- Find segment containing corrected word
- Replace corrected word with original word from correction.original_word
- Update data state
- Add to undo history

### 7. Mobile Responsiveness

**Files: Multiple component files**

Ensure all new components:

- Use Material-UI breakpoints for responsive layout
- Touch targets minimum 44x44px
- No hover-only interactions
- Swipe gestures where appropriate (detail cards)
- Bottom sheet modals on mobile instead of center modals
- Adequate spacing for fat-finger taps
- Test on mobile viewport (375px width minimum)

## Implementation Order

1. Duration visualization (most impactful for catching long words)
2. Category metrics panel (replaces confusing handler toggles)
3. Inline action buttons (enables quick revert/edit)
4. Detail card modal (replaces cramped tooltip)
5. Action handlers and state management (makes buttons functional)
6. Mobile polish and testing

## Files to Modify

- `lyrics_transcriber/frontend/src/components/TranscriptionView.tsx` - Add duration view toggle
- Create `lyrics_transcriber/frontend/src/components/DurationTimelineView.tsx` - New visualization
- Create `lyrics_transcriber/frontend/src/components/CorrectedWordWithActions.tsx` - Inline actions
- `lyrics_transcriber/frontend/src/components/shared/components/Word.tsx` - Integrate actions
- Create `lyrics_transcriber/frontend/src/components/CorrectionDetailCard.tsx` - Rich detail view
- Create `lyrics_transcriber/frontend/src/components/AgenticCorrectionMetrics.tsx` - Category breakdown
- `lyrics_transcriber/frontend/src/components/Header.tsx` - Switch to category metrics when agentic
- `lyrics_transcriber/frontend/src/components/LyricsAnalyzer.tsx` - Add action handlers
- `lyrics_transcriber/frontend/src/types.ts` - Add new type definitions

## Key Design Decisions

- Mobile-first: All interactions work without hover
- Always-visible duration bars catch timing issues immediately
- Original word shown above corrected word for quick comparison
- Category-based metrics more useful than handler toggles for agentic workflow
- Inline actions minimize taps for common tasks (revert, edit)
- Rich detail card for when user needs full context
- Future-proof: Action handlers can integrate with annotation/feedback API later

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