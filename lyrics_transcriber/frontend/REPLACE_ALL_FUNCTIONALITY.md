Please read this doc to understand the "Replace All" modal we implemented in a previous chat: @REPLACE_ALL_FUNCTIONALITY.md 

The primary code for the new modal is here: @ReplaceAllLyricsModal.tsx 
but the manual sync functionality relies heavily on @EditTimelineSection.tsx, @useManualSync.ts  and @EditActionBar.tsx 

The functionality mostly works but we need to continue refining it and fixing issues until it is good enough for me and other users to use. Please let me know once you've reviewed the above and you're ready for me to explain the first issue.

# Replace All Lyrics Functionality

## Overview

The "Replace All Lyrics" functionality provides a complete solution for replacing transcribed lyrics when the original transcription quality is too poor to edit word-by-word. This feature allows users to start fresh with clipboard content and manually sync timing for the entire song.

## Key Components

### 1. ReplaceAllLyricsModal.tsx
- **Location**: `src/components/ReplaceAllLyricsModal.tsx`
- **Purpose**: Standalone modal for replacing all lyrics with clipboard content
- **Design**: Separate from EditModal.tsx to maintain clean separation of concerns

### 2. Integration Points
- **useManualSync Hook**: Reuses existing manual sync functionality
- **AudioPlayer Integration**: Leverages global audio controls and duration
- **Types**: Uses existing LyricsSegment and Word types

## User Workflow

### Phase 1: Input
1. **Open Modal**: Access via "Replace All Lyrics" button/action
2. **Paste Content**: Large textarea for pasting lyrics from clipboard
3. **Real-time Feedback**: 
   - Line count display
   - Word count display
   - Preview of how content will be parsed
4. **Validation**: Ensures content is not empty before proceeding

### Phase 2: Manual Sync
1. **Automatic Conversion**: Each line becomes a LyricsSegment, each word becomes a Word object
2. **Timeline View**: 
   - Fixed 30-second zoom window
   - Shows entire song duration (0 to audio duration)
   - Visual indicators for word positions
3. **Manual Timing**: 
   - Spacebar to mark word timings during playback
   - Pause/resume functionality for corrections
   - Real-time progress tracking
4. **Progress Panel**: 
   - Shows all segments with sync status
   - Active segment highlighting (blue)
   - Completed segments (green) with timing display
   - Progress indicators (X/Y words synced)
   - Auto-scroll to follow playback

## Technical Implementation

### Data Structure
```typescript
// Each line becomes a LyricsSegment
{
  id: string,
  text: string, // Full line text
  start_time: number | null,
  end_time: number | null,
  words: Word[] // Each word in the line
}

// Each word becomes a Word object
{
  id: string,
  text: string, // Individual word
  start_time: number | null,
  end_time: number | null,
  confidence: number // Set to 1.0 for manual entries
}
```

### Modal Layout
- **Full Browser Width**: Uses `maxWidth={false}` and viewport-based calculations
- **Split Layout**: 
  - Timeline Section: 2/3 width
  - Progress Panel: 1/3 width
- **Responsive Design**: Adapts to different screen sizes

### Audio Integration
- **Duration Detection**: Uses `window.getAudioDuration()` for accurate song length
- **Playback Control**: Integrates with existing audio controls
- **Auto-cleanup**: Stops audio when canceling sync

## Key Features Implemented

### 1. Stable Timeline View
- **Fixed Zoom**: Always shows 30-second window
- **Full Song Range**: Timeline spans 0 to full audio duration
- **Prevents Zoom Changes**: Disabled during manual sync to maintain consistency

### 2. Manual Sync Enhancement
- **Spacebar Timing**: Press spacebar to mark word timings
- **Pause/Resume**: Alt+P to pause/resume for corrections
- **Visual Feedback**: 
  - Current word highlighting
  - Spacebar press indication
  - Progress tracking

### 3. Progress Tracking
- **Segment Status**: Visual indicators for sync progress
- **Real-time Updates**: Timing updates as words are synced
- **Auto-scroll**: Follows active segment during sync
- **Completion Status**: Clear visual feedback for completed segments

### 4. Error Prevention
- **Input Validation**: Ensures content exists before proceeding
- **Safe Navigation**: Proper cleanup when canceling
- **State Management**: Prevents conflicts with existing edit modals

## Bug Fixes Implemented

### 1. Manual Sync Issues
- **Problem**: Sync stopping after first spacebar press
- **Solution**: Fixed infinite re-renders in useEffect dependencies
- **Result**: Stable manual sync throughout entire song

### 2. Timeline Zoom Problems
- **Problem**: Timeline zooming to single word duration after sync
- **Solution**: Fixed timeRange calculation to always use full song duration
- **Result**: Consistent 30-second view regardless of sync progress

### 3. Audio Duration
- **Problem**: Hardcoded duration fallbacks causing inaccurate timelines
- **Solution**: Integration with real audio duration from AudioPlayer
- **Result**: Accurate timeline representation of song length

### 4. Keyboard Conflicts
- **Problem**: Multiple keyboard handlers causing conflicts
- **Solution**: Proper handler cleanup and event management
- **Result**: Clean keyboard interaction without conflicts

## User Experience Improvements

### 1. Visual Feedback
- **Real-time Counts**: Live word/line counting during input
- **Progress Indicators**: Clear visual feedback on sync progress
- **Color Coding**: Blue for active, green for completed segments

### 2. Navigation
- **Auto-scroll**: Automatically follows playback position
- **Manual Navigation**: Can manually scroll through segments
- **Status Preservation**: Maintains state during navigation

### 3. Error Recovery
- **Pause/Resume**: Ability to pause and correct timing
- **Cancel Support**: Safe cancellation with proper cleanup
- **State Reset**: Clean state management between sessions

## Integration with Existing Codebase

### 1. Reused Components
- **useManualSync**: Leverages existing manual sync logic
- **Timeline Components**: Reuses timeline visualization
- **Audio Controls**: Integrates with existing audio system

### 2. Type Safety
- **TypeScript**: Fully typed implementation
- **Consistent Interfaces**: Uses existing type definitions
- **Validation**: Runtime validation for data integrity

### 3. State Management
- **Isolated State**: Doesn't interfere with existing edit functionality
- **Clean Separation**: Separate modal for replace vs. edit operations
- **Proper Cleanup**: Ensures no state leakage between modals

## Performance Considerations

### 1. Rendering Optimization
- **Memoization**: Strategic use of React.memo and useCallback
- **Efficient Updates**: Minimal re-renders during sync
- **Progressive Loading**: Handles large lyric sets efficiently

### 2. Memory Management
- **Cleanup**: Proper cleanup of event listeners and timers
- **State Reset**: Clean state management between sessions
- **Audio Integration**: Efficient audio control integration

## Future Enhancement Opportunities

### 1. Batch Operations
- **Multi-line Selection**: Select and sync multiple segments at once
- **Timing Adjustment**: Bulk timing adjustments
- **Smart Defaults**: AI-suggested timing based on audio analysis

### 2. Import/Export
- **Format Support**: Support for various lyric file formats
- **Backup/Restore**: Save and restore sync sessions
- **Templates**: Predefined timing templates

### 3. Advanced Sync
- **Beat Detection**: Automatic beat-based timing suggestions
- **Voice Activity**: Audio analysis for timing hints
- **Collaborative Sync**: Multi-user timing collaboration

## Summary

The "Replace All Lyrics" functionality provides a comprehensive solution for handling poor-quality transcriptions by:

1. **Complete Replacement**: Replaces all existing lyrics with fresh clipboard content
2. **Manual Control**: Gives users full control over timing through manual sync
3. **Visual Feedback**: Provides clear progress tracking and status indicators
4. **Stable Interface**: Maintains consistent timeline view throughout the process
5. **Clean Integration**: Works seamlessly with existing audio and editing systems

This implementation significantly improves the user experience for cases where starting fresh is more efficient than editing individual words, while maintaining the high-quality timing precision needed for karaoke applications. 