import { useState, useEffect, useCallback, useMemo, memo } from 'react'
import {
    AnchorSequence,
    CorrectionData,
    GapSequence,
    HighlightInfo,
    InteractionMode,
    LyricsSegment,
    ReferenceSource,
    WordCorrection,
    CorrectionAnnotation
} from '../types'
import { Box, Button, Grid, useMediaQuery, useTheme } from '@mui/material'
import { ApiClient } from '../api'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import { WordClickInfo, FlashType } from './shared/types'
import EditModal from './EditModal'
import ReviewChangesModal from './ReviewChangesModal'
import ReplaceAllLyricsModal from './ReplaceAllLyricsModal'
import CorrectionAnnotationModal from './CorrectionAnnotationModal'
import CorrectionDetailCard from './CorrectionDetailCard'
import {
    addSegmentBefore,
    splitSegment,
    deleteSegment,
    mergeSegment,
    findAndReplace,
    deleteWord
} from './shared/utils/segmentOperations'
import { loadSavedData, saveData, clearSavedData } from './shared/utils/localStorage'
import { setupKeyboardHandlers, setModalHandler, getModalState } from './shared/utils/keyboardHandlers'
import Header from './Header'
import { getWordsFromIds } from './shared/utils/wordUtils'
import AddLyricsModal from './AddLyricsModal'
import { RestoreFromTrash, OndemandVideo } from '@mui/icons-material'
import FindReplaceModal from './FindReplaceModal'
import TimingOffsetModal from './TimingOffsetModal'
import { applyOffsetToCorrectionData, applyOffsetToSegment } from './shared/utils/timingUtils'

// Add type for window augmentation at the top of the file
declare global {
    interface Window {
        toggleAudioPlayback?: () => void;
        seekAndPlayAudio?: (startTime: number) => void;
        getAudioDuration?: () => number;
        isAudioPlaying?: boolean;
    }
}

const debugLog = false;
export interface LyricsAnalyzerProps {
    data: CorrectionData
    onFileLoad: () => void
    onShowMetadata: () => void
    apiClient: ApiClient | null
    isReadOnly: boolean
    audioHash: string
}

export type ModalContent = {
    type: 'anchor'
    data: AnchorSequence & {
        wordId: string
        word?: string
        anchor_sequences: AnchorSequence[]
    }
} | {
    type: 'gap'
    data: GapSequence & {
        wordId: string
        word: string
        anchor_sequences: AnchorSequence[]
    }
}

// Define types for the memoized components
interface MemoizedTranscriptionViewProps {
    data: CorrectionData
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick: (info: WordClickInfo) => void
    flashingType: FlashType
    flashingHandler: string | null
    highlightInfo: HighlightInfo | null
    onPlaySegment?: (time: number) => void
    currentTime: number
    anchors: AnchorSequence[]
    disableHighlighting: boolean
    onDataChange?: (updatedData: CorrectionData) => void
}

// Create a memoized TranscriptionView component
const MemoizedTranscriptionView = memo(function MemoizedTranscriptionView({
    data,
    mode,
    onElementClick,
    onWordClick,
    flashingType,
    flashingHandler,
    highlightInfo,
    onPlaySegment,
    currentTime,
    anchors,
    disableHighlighting,
    onDataChange
}: MemoizedTranscriptionViewProps) {
    return (
        <TranscriptionView
            data={data}
            mode={mode}
            onElementClick={onElementClick}
            onWordClick={onWordClick}
            flashingType={flashingType}
            flashingHandler={flashingHandler}
            highlightInfo={highlightInfo}
            onPlaySegment={onPlaySegment}
            currentTime={disableHighlighting ? undefined : currentTime}
            anchors={anchors}
            onDataChange={onDataChange}
        />
    );
});

interface MemoizedReferenceViewProps {
    referenceSources: Record<string, ReferenceSource>
    anchors: AnchorSequence[]
    gaps: GapSequence[]
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
    currentSource: string
    onSourceChange: (source: string) => void
    corrected_segments: LyricsSegment[]
    corrections: WordCorrection[]
    onAddLyrics?: () => void
}

// Create a memoized ReferenceView component
const MemoizedReferenceView = memo(function MemoizedReferenceView({
    referenceSources,
    anchors,
    gaps,
    mode,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo,
    currentSource,
    onSourceChange,
    corrected_segments,
    corrections,
    onAddLyrics
}: MemoizedReferenceViewProps) {
    return (
        <ReferenceView
            referenceSources={referenceSources}
            anchors={anchors}
            gaps={gaps}
            mode={mode}
            onElementClick={onElementClick}
            onWordClick={onWordClick}
            flashingType={flashingType}
            highlightInfo={highlightInfo}
            currentSource={currentSource}
            onSourceChange={onSourceChange}
            corrected_segments={corrected_segments}
            corrections={corrections}
            onAddLyrics={onAddLyrics}
        />
    );
});

interface MemoizedHeaderProps {
    isReadOnly: boolean
    onFileLoad: () => void
    data: CorrectionData
    onMetricClick: {
        anchor: () => void
        corrected: () => void
        uncorrected: () => void
    }
    effectiveMode: InteractionMode
    onModeChange: (mode: InteractionMode) => void
    apiClient: ApiClient | null
    audioHash: string
    onTimeUpdate: (time: number) => void
    onHandlerToggle: (handler: string, enabled: boolean) => void
    isUpdatingHandlers: boolean
    onHandlerClick?: (handler: string) => void
    onAddLyrics?: () => void
    onFindReplace?: () => void
    onEditAll?: () => void
    onTimingOffset: () => void
    timingOffsetMs: number
    onUndo: () => void
    onRedo: () => void
    canUndo: boolean
    canRedo: boolean
    onUnCorrectAll: () => void
}

// Create a memoized Header component
const MemoizedHeader = memo(function MemoizedHeader({
    isReadOnly,
    onFileLoad,
    data,
    onMetricClick,
    effectiveMode,
    onModeChange,
    apiClient,
    audioHash,
    onTimeUpdate,
    onHandlerToggle,
    isUpdatingHandlers,
    onHandlerClick,
    onFindReplace,
    onEditAll,
    onTimingOffset,
    timingOffsetMs,
    onUndo,
    onRedo,
    canUndo,
    canRedo,
    onUnCorrectAll
}: MemoizedHeaderProps) {
    return (
        <Header
            isReadOnly={isReadOnly}
            onFileLoad={onFileLoad}
            data={data}
            onMetricClick={onMetricClick}
            effectiveMode={effectiveMode}
            onModeChange={onModeChange}
            apiClient={apiClient}
            audioHash={audioHash}
            onTimeUpdate={onTimeUpdate}
            onHandlerToggle={onHandlerToggle}
            isUpdatingHandlers={isUpdatingHandlers}
            onHandlerClick={onHandlerClick}
            onFindReplace={onFindReplace}
            onEditAll={onEditAll}
            onTimingOffset={onTimingOffset}
            timingOffsetMs={timingOffsetMs}
            onUndo={onUndo}
            onRedo={onRedo}
            canUndo={canUndo}
            canRedo={canRedo}
            onUnCorrectAll={onUnCorrectAll}
        />
    );
});

export default function LyricsAnalyzer({ data: initialData, onFileLoad, apiClient, isReadOnly, audioHash }: LyricsAnalyzerProps) {
    const [modalContent, setModalContent] = useState<ModalContent | null>(null)
    const [flashingType, setFlashingType] = useState<FlashType>(null)
    const [highlightInfo, setHighlightInfo] = useState<HighlightInfo | null>(null)
    const [currentSource, setCurrentSource] = useState<string>(() => {
        if (!initialData?.reference_lyrics) {
            return ''
        }
        const availableSources = Object.keys(initialData.reference_lyrics)
        return availableSources.length > 0 ? availableSources[0] : ''
    })
    const [isReviewComplete, setIsReviewComplete] = useState(false)
    const [originalData] = useState(() => JSON.parse(JSON.stringify(initialData)))
    const [interactionMode, setInteractionMode] = useState<InteractionMode>('edit')
    const [isShiftPressed, setIsShiftPressed] = useState(false)
    const [isCtrlPressed, setIsCtrlPressed] = useState(false)
    const [editModalSegment, setEditModalSegment] = useState<{
        segment: LyricsSegment
        index: number
        originalSegment: LyricsSegment
    } | null>(null)
    const [isReplaceAllLyricsModalOpen, setIsReplaceAllLyricsModalOpen] = useState(false)
    const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
    const [currentAudioTime, setCurrentAudioTime] = useState(0)
    const [isUpdatingHandlers, setIsUpdatingHandlers] = useState(false)
    const [flashingHandler, setFlashingHandler] = useState<string | null>(null)
    const [isAddingLyrics, setIsAddingLyrics] = useState(false)
    const [isAddLyricsModalOpen, setIsAddLyricsModalOpen] = useState(false)
    const [isAnyModalOpen, setIsAnyModalOpen] = useState(false)
    const [isFindReplaceModalOpen, setIsFindReplaceModalOpen] = useState(false)
    const [isTimingOffsetModalOpen, setIsTimingOffsetModalOpen] = useState(false)
    const [timingOffsetMs, setTimingOffsetMs] = useState(0)
    
    // Annotation collection state
    const [annotations, setAnnotations] = useState<Omit<CorrectionAnnotation, 'annotation_id' | 'timestamp'>[]>([])
    const [isAnnotationModalOpen, setIsAnnotationModalOpen] = useState(false)
    const [pendingAnnotation, setPendingAnnotation] = useState<{
        originalText: string
        correctedText: string
        wordIdsAffected: string[]
        gapId?: string
    } | null>(null)
    const [annotationsEnabled] = useState(() => {
        // Check localStorage for user preference
        const saved = localStorage.getItem('annotationsEnabled')
        return saved !== null ? saved === 'true' : true // Default: enabled
        // TODO: Add UI toggle to enable/disable via setAnnotationsEnabled
    })
    
    // Correction detail card state
    const [correctionDetailOpen, setCorrectionDetailOpen] = useState(false)
    const [selectedCorrection, setSelectedCorrection] = useState<{
        wordId: string
        originalWord: string
        correctedWord: string
        category: string | null
        confidence: number
        reason: string
        handler: string
        source: string
    } | null>(null)
    
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

    // State history for Undo/Redo
    const [history, setHistory] = useState<CorrectionData[]>([initialData])
    const [historyIndex, setHistoryIndex] = useState(0)

    // Derived state: the current data based on history index
    const data = history[historyIndex];

    // Function to update data and manage history
    const updateDataWithHistory = useCallback((newData: CorrectionData, actionDescription?: string) => {
        if (debugLog) {
            console.log(`[DEBUG] updateDataWithHistory: Action - ${actionDescription || 'Unknown'}. Current index: ${historyIndex}, History length: ${history.length}`);
        }
        const newHistory = history.slice(0, historyIndex + 1)
        const deepCopiedNewData = JSON.parse(JSON.stringify(newData));

        newHistory.push(deepCopiedNewData)
        setHistory(newHistory)
        setHistoryIndex(newHistory.length - 1)
        if (debugLog) {
            console.log(`[DEBUG] updateDataWithHistory: History updated. New index: ${newHistory.length - 1}, New length: ${newHistory.length}`);
        }
    }, [history, historyIndex])

    // Reset history when initial data changes (e.g., new file loaded)
    useEffect(() => {
        setHistory([initialData])
        setHistoryIndex(0)
    }, [initialData])

    // Update debug logging to use new ID-based structure
    useEffect(() => {
        if (debugLog) {
            console.log('LyricsAnalyzer Initial Data:', {
                hasData: !!initialData,
                segmentsCount: initialData?.corrected_segments?.length ?? 0,
                anchorsCount: initialData?.anchor_sequences?.length ?? 0,
                gapsCount: initialData?.gap_sequences?.length ?? 0,
                firstAnchor: initialData?.anchor_sequences?.[0] && {
                    transcribedWordIds: initialData.anchor_sequences[0].transcribed_word_ids,
                    referenceWordIds: initialData.anchor_sequences[0].reference_word_ids
                },
                firstSegment: initialData?.corrected_segments?.[0],
                referenceSources: Object.keys(initialData?.reference_lyrics ?? {})
            });
        }
    }, [initialData]);

    // Load saved data
    useEffect(() => {
        const savedData = loadSavedData(initialData)
        if (savedData && window.confirm('Found saved progress for this song. Would you like to restore it?')) {
            // Replace history with saved data as the initial state
            setHistory([savedData])
            setHistoryIndex(0)
        }
    }, [initialData]) // Keep dependency only on initialData

    // Save data - This should save the *current* state, not affect history
    useEffect(() => {
        if (!isReadOnly) {
            saveData(data, initialData) // Use 'data' derived from history and the initialData prop
        }
    }, [data, isReadOnly, initialData]) // Correct dependencies

    // Keyboard handlers
    useEffect(() => {
        const { currentModalHandler } = getModalState()

        if (debugLog) {
            console.log('LyricsAnalyzer - Setting up keyboard effect', {
                isAnyModalOpen,
                hasSpacebarHandler: !!currentModalHandler
            })
        }

        const { handleKeyDown, handleKeyUp, cleanup } = setupKeyboardHandlers({
            setIsShiftPressed,
            setIsCtrlPressed
        })

        // Always add keyboard listeners
        if (debugLog) {
            console.log('LyricsAnalyzer - Adding keyboard event listeners')
        }
        window.addEventListener('keydown', handleKeyDown)
        window.addEventListener('keyup', handleKeyUp)

        // Reset modifier states when a modal opens
        if (isAnyModalOpen) {
            setIsShiftPressed(false)
            setIsCtrlPressed(false)
        }

        // Cleanup function
        return () => {
            if (debugLog) {
                console.log('LyricsAnalyzer - Cleanup effect running')
            }
            window.removeEventListener('keydown', handleKeyDown)
            window.removeEventListener('keyup', handleKeyUp)
            document.body.style.userSelect = ''
            // Call the cleanup function to remove window blur/focus listeners
            cleanup()
        }
    }, [setIsShiftPressed, setIsCtrlPressed, isAnyModalOpen])

    // Update modal state tracking
    useEffect(() => {
        const modalOpen = Boolean(
            modalContent ||
            editModalSegment ||
            isReviewModalOpen ||
            isAddLyricsModalOpen ||
            isFindReplaceModalOpen ||
            isReplaceAllLyricsModalOpen ||
            isTimingOffsetModalOpen
        )
        setIsAnyModalOpen(modalOpen)
    }, [modalContent, editModalSegment, isReviewModalOpen, isAddLyricsModalOpen, isFindReplaceModalOpen, isReplaceAllLyricsModalOpen, isTimingOffsetModalOpen])

    // Calculate effective mode based on modifier key states
    const effectiveMode = isCtrlPressed ? 'delete_word' : (isShiftPressed ? 'highlight' : interactionMode)

    const handleFlash = useCallback((type: FlashType, info?: HighlightInfo) => {
        setFlashingType(null)
        setHighlightInfo(null)

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                setFlashingType(type)
                if (info) {
                    setHighlightInfo(info)
                }
                setTimeout(() => {
                    setFlashingType(null)
                    setHighlightInfo(null)
                }, 1200)
            })
        })
    }, [])

    const handleWordClick = useCallback((info: WordClickInfo) => {
        if (debugLog) {
            console.log('LyricsAnalyzer handleWordClick:', { info });
        }

        if (effectiveMode === 'delete_word') {
            // Use the shared deleteWord utility function
            const newData = deleteWord(data, info.word_id);
            updateDataWithHistory(newData, 'delete word'); // Update history

            // Flash to indicate the word was deleted
            handleFlash('word');
            return;
        }

        if (effectiveMode === 'highlight') {
            // Find if this word is part of a correction
            const correction = data.corrections?.find(c =>
                c.corrected_word_id === info.word_id ||
                c.word_id === info.word_id
            );

            if (correction) {
                // For agentic corrections, show the detail card instead of just highlighting
                if (correction.handler === 'AgenticCorrector') {
                    handleShowCorrectionDetail(info.word_id)
                    return
                }
                
                setHighlightInfo({
                    type: 'correction',
                    transcribed_words: [], // Required by type but not used for corrections
                    correction: correction
                });
                setFlashingType('word');
                return;
            }

            // Find if this word is part of an anchor sequence
            const anchor = data.anchor_sequences?.find(a =>
                a.transcribed_word_ids.includes(info.word_id) ||
                Object.values(a.reference_word_ids).some(ids =>
                    ids.includes(info.word_id)
                )
            );

            if (anchor) {
                // Create a temporary segment containing all words
                const allWords = data.corrected_segments.flatMap(s => s.words)
                const tempSegment: LyricsSegment = {
                    id: 'temp',
                    words: allWords,
                    text: allWords.map(w => w.text).join(' '),
                    start_time: allWords[0]?.start_time ?? null,
                    end_time: allWords[allWords.length - 1]?.end_time ?? null
                }

                const transcribedWords = getWordsFromIds(
                    [tempSegment],
                    anchor.transcribed_word_ids
                );

                const referenceWords = Object.fromEntries(
                    Object.entries(anchor.reference_word_ids).map(([source, ids]) => {
                        const sourceWords = data.reference_lyrics[source].segments.flatMap(s => s.words)
                        const tempSourceSegment: LyricsSegment = {
                            id: `temp-${source}`,
                            words: sourceWords,
                            text: sourceWords.map(w => w.text).join(' '),
                            start_time: sourceWords[0]?.start_time ?? null,
                            end_time: sourceWords[sourceWords.length - 1]?.end_time ?? null
                        }
                        return [source, getWordsFromIds([tempSourceSegment], ids)]
                    })
                );

                setHighlightInfo({
                    type: 'anchor',
                    sequence: anchor,
                    transcribed_words: transcribedWords,
                    reference_words: referenceWords
                });
                setFlashingType('word');
                return;
            }

            // Find if this word is part of a gap sequence
            const gap = data.gap_sequences?.find(g =>
                g.transcribed_word_ids.includes(info.word_id)
            );

            if (gap) {
                // Create a temporary segment containing all words
                const allWords = data.corrected_segments.flatMap(s => s.words)
                const tempSegment: LyricsSegment = {
                    id: 'temp',
                    words: allWords,
                    text: allWords.map(w => w.text).join(' '),
                    start_time: allWords[0]?.start_time ?? null,
                    end_time: allWords[allWords.length - 1]?.end_time ?? null
                }

                const transcribedWords = getWordsFromIds(
                    [tempSegment],
                    gap.transcribed_word_ids
                );

                const referenceWords = Object.fromEntries(
                    Object.entries(gap.reference_word_ids).map(([source, ids]) => {
                        const sourceWords = data.reference_lyrics[source].segments.flatMap(s => s.words)
                        const tempSourceSegment: LyricsSegment = {
                            id: `temp-${source}`,
                            words: sourceWords,
                            text: sourceWords.map(w => w.text).join(' '),
                            start_time: sourceWords[0]?.start_time ?? null,
                            end_time: sourceWords[sourceWords.length - 1]?.end_time ?? null
                        }
                        return [source, getWordsFromIds([tempSourceSegment], ids)]
                    })
                );

                setHighlightInfo({
                    type: 'gap',
                    sequence: gap,
                    transcribed_words: transcribedWords,
                    reference_words: referenceWords
                });
                setFlashingType('word');
                return;
            }
        } else if (effectiveMode === 'edit') {
            // Find the segment containing this word
            const segmentIndex = data.corrected_segments.findIndex(segment =>
                segment.words.some(word => word.id === info.word_id)
            );

            if (segmentIndex !== -1) {
                const segment = data.corrected_segments[segmentIndex];
                setEditModalSegment({
                    segment,
                    index: segmentIndex,
                    originalSegment: JSON.parse(JSON.stringify(segment))
                });
            }
        }
    }, [data, effectiveMode, setModalContent, handleFlash, deleteWord, updateDataWithHistory]);
    
    // Annotation handlers (declared early for use in other callbacks)
    const handleSaveAnnotation = useCallback((annotation: Omit<CorrectionAnnotation, 'annotation_id' | 'timestamp'>) => {
        setAnnotations(prev => [...prev, annotation])
        console.log('Annotation saved:', annotation)
    }, [])
    
    const handleSkipAnnotation = useCallback(() => {
        console.log('Annotation skipped')
    }, [])
    
    const triggerAnnotationModal = useCallback((
        originalText: string,
        correctedText: string,
        wordIdsAffected: string[],
        gapId?: string
    ) => {
        if (!annotationsEnabled || isReadOnly) {
            return
        }
        
        setPendingAnnotation({
            originalText,
            correctedText,
            wordIdsAffected,
            gapId
        })
        setIsAnnotationModalOpen(true)
    }, [annotationsEnabled, isReadOnly])

    const handleUpdateSegment = useCallback((updatedSegment: LyricsSegment) => {
        if (!editModalSegment) return

        if (debugLog) {
            console.log('[DEBUG] handleUpdateSegment: Updating history from modal save', {
                segmentIndex: editModalSegment.index,
                currentHistoryIndex: historyIndex,
                currentHistoryLength: history.length,
                currentSegmentText: history[historyIndex]?.corrected_segments[editModalSegment.index]?.text,
                updatedSegmentText: updatedSegment.text
            });
        }

        // --- Ensure Immutability Here ---
        const currentData = history[historyIndex];
        const newSegments = currentData.corrected_segments.map((segment, i) =>
            i === editModalSegment.index ? updatedSegment : segment
        );
        const newDataImmutable: CorrectionData = {
            ...currentData,
            corrected_segments: newSegments,
        };
        // --- End Immutability Ensure ---

        updateDataWithHistory(newDataImmutable, 'update segment');

        if (debugLog) {
            console.log('[DEBUG] handleUpdateSegment: History updated (async)', {
                newHistoryIndex: historyIndex + 1,
                newHistoryLength: history.length - historyIndex === 1 ? history.length + 1 : historyIndex + 2
            });
        }
        
        // Trigger annotation modal if enabled and text changed
        const originalSegment = editModalSegment.originalSegment || editModalSegment.segment
        if (originalSegment && originalSegment.text !== updatedSegment.text) {
            // Get word IDs that were affected
            const wordIds = updatedSegment.words.map(w => w.id)
            triggerAnnotationModal(
                originalSegment.text,
                updatedSegment.text,
                wordIds
            )
        }
        
        setEditModalSegment(null)
    }, [history, historyIndex, editModalSegment, updateDataWithHistory, triggerAnnotationModal])

    const handleDeleteSegment = useCallback((segmentIndex: number) => {
        const newData = deleteSegment(data, segmentIndex)
        updateDataWithHistory(newData, 'delete segment')
    }, [data, updateDataWithHistory])

    // Correction action handlers
    const handleRevertCorrection = useCallback((wordId: string) => {
        // Find the correction for this word
        const correction = data.corrections?.find(c => 
            c.corrected_word_id === wordId || c.word_id === wordId
        )
        
        if (!correction) {
            console.error('Correction not found for word:', wordId)
            return
        }

        // Find the segment containing the corrected word
        const segmentIndex = data.corrected_segments.findIndex(segment =>
            segment.words.some(w => w.id === wordId)
        )

        if (segmentIndex === -1) {
            console.error('Segment not found for word:', wordId)
            return
        }

        const segment = data.corrected_segments[segmentIndex]
        
        // Replace the corrected word with the original
        const newWords = segment.words.map(word => {
            if (word.id === wordId) {
                return {
                    ...word,
                    text: correction.original_word,
                    id: correction.word_id // Restore original word ID
                }
            }
            return word
        })

        // Rebuild segment text
        const newText = newWords.map(w => w.text).join(' ')

        const newSegment = {
            ...segment,
            words: newWords,
            text: newText
        }

        // Update data
        const newSegments = data.corrected_segments.map((seg, idx) =>
            idx === segmentIndex ? newSegment : seg
        )

        // Remove the correction from the corrections list
        const newCorrections = data.corrections?.filter(c =>
            c.corrected_word_id !== wordId && c.word_id !== wordId
        )

        const newData: CorrectionData = {
            ...data,
            corrected_segments: newSegments,
            corrections: newCorrections || []
        }

        updateDataWithHistory(newData, 'revert correction')
        
        console.log('Reverted correction:', {
            originalWord: correction.original_word,
            correctedWord: correction.corrected_word,
            wordId
        })
    }, [data, updateDataWithHistory])

    const handleEditCorrection = useCallback((wordId: string) => {
        // Find the segment containing this word
        const segmentIndex = data.corrected_segments.findIndex(segment =>
            segment.words.some(w => w.id === wordId)
        )

        if (segmentIndex === -1) {
            console.error('Segment not found for word:', wordId)
            return
        }

        // Open edit modal for this segment
        const segment = data.corrected_segments[segmentIndex]
        setEditModalSegment({
            segment: segment,
            index: segmentIndex,
            originalSegment: segment
        })
    }, [data])

    const handleAcceptCorrection = useCallback((wordId: string) => {
        // For now, just log acceptance
        // In the future, this could be tracked in the annotation system
        console.log('Accepted correction for word:', wordId)
        
        // TODO: Track acceptance in annotation system
        // This could be used to build confidence in the AI's corrections over time
    }, [])

    const handleShowCorrectionDetail = useCallback((wordId: string) => {
        // Find the correction for this word
        const correction = data.corrections?.find(c => 
            c.corrected_word_id === wordId || c.word_id === wordId
        )
        
        if (!correction) {
            console.error('Correction not found for word:', wordId)
            return
        }

        // Extract category from reason (format: "reason [CATEGORY] (confidence: XX%)")
        const categoryMatch = correction.reason?.match(/\[([A-Z_]+)\]/)
        const category = categoryMatch ? categoryMatch[1] : null

        // Find the corrected word text
        const correctedWord = data.corrected_segments
            .flatMap(s => s.words)
            .find(w => w.id === wordId)?.text || correction.corrected_word

        setSelectedCorrection({
            wordId,
            originalWord: correction.original_word,
            correctedWord: correctedWord,
            category,
            confidence: correction.confidence,
            reason: correction.reason,
            handler: correction.handler,
            source: correction.source
        })
        setCorrectionDetailOpen(true)
    }, [data])

    const handleFinishReview = useCallback(() => {
        console.log(`[TIMING] handleFinishReview - Current timing offset: ${timingOffsetMs}ms`);
        setIsReviewModalOpen(true)
    }, [timingOffsetMs])

    const handleSubmitToServer = useCallback(async () => {
        if (!apiClient) return

        try {
            if (debugLog) {
                console.log('Submitting changes to server')
            }
            
            // Debug logging for timing offset
            console.log(`[TIMING] handleSubmitToServer - Current timing offset: ${timingOffsetMs}ms`);
            
            // Apply timing offset to the data before submission if needed
            const dataToSubmit = timingOffsetMs !== 0 
                ? applyOffsetToCorrectionData(data, timingOffsetMs) 
                : data
                
            // Log some example timestamps after potential offset application
            if (dataToSubmit.corrected_segments.length > 0) {
                const firstSegment = dataToSubmit.corrected_segments[0];
                console.log(`[TIMING] Submitting data - First segment id: ${firstSegment.id}`);
                console.log(`[TIMING] - start_time: ${firstSegment.start_time}, end_time: ${firstSegment.end_time}`);
                
                if (firstSegment.words.length > 0) {
                    const firstWord = firstSegment.words[0];
                    console.log(`[TIMING] - first word "${firstWord.text}" time: ${firstWord.start_time} -> ${firstWord.end_time}`);
                }
            }
                
            await apiClient.submitCorrections(dataToSubmit)
            
            // Submit annotations if any were collected
            if (annotations.length > 0) {
                console.log(`Submitting ${annotations.length} annotations...`)
                try {
                    await apiClient.submitAnnotations(annotations)
                    console.log('Annotations submitted successfully')
                } catch (error) {
                    console.error('Failed to submit annotations:', error)
                    // Don't block the main submission if annotations fail
                }
            }

            setIsReviewComplete(true)
            setIsReviewModalOpen(false)

            // Close the browser tab
            window.close()
        } catch (error) {
            console.error('Failed to submit corrections:', error)
            alert('Failed to submit corrections. Please try again.')
        }
    }, [apiClient, data, timingOffsetMs, annotations])

    // Update play segment handler
    const handlePlaySegment = useCallback((startTime: number) => {
        if (window.seekAndPlayAudio) {
            // Apply the timing offset to the start time
            const adjustedStartTime = timingOffsetMs !== 0 
                ? startTime + (timingOffsetMs / 1000) 
                : startTime;
                
            window.seekAndPlayAudio(adjustedStartTime)
        }
    }, [timingOffsetMs])

    const handleResetCorrections = useCallback(() => {
        if (window.confirm('Are you sure you want to reset all corrections? This cannot be undone.')) {
            clearSavedData(initialData)
            // Reset history to the original initial data
            setHistory([JSON.parse(JSON.stringify(initialData))])
            setHistoryIndex(0)
            setModalContent(null)
            setFlashingType(null)
            setHighlightInfo(null)
            setInteractionMode('edit')
        }
    }, [initialData])

    const handleAddSegment = useCallback((beforeIndex: number) => {
        const newData = addSegmentBefore(data, beforeIndex)
        updateDataWithHistory(newData, 'add segment')
    }, [data, updateDataWithHistory])

    const handleSplitSegment = useCallback((segmentIndex: number, afterWordIndex: number) => {
        const newData = splitSegment(data, segmentIndex, afterWordIndex)
        if (newData) {
            updateDataWithHistory(newData, 'split segment')
            setEditModalSegment(null)
        }
    }, [data, updateDataWithHistory])

    const handleMergeSegment = useCallback((segmentIndex: number, mergeWithNext: boolean) => {
        const newData = mergeSegment(data, segmentIndex, mergeWithNext)
        updateDataWithHistory(newData, 'merge segment')
        setEditModalSegment(null)
    }, [data, updateDataWithHistory])

    const handleHandlerToggle = useCallback(async (handler: string, enabled: boolean) => {
        if (!apiClient) return

        try {
            setIsUpdatingHandlers(true);

            // Get current enabled handlers
            const currentEnabled = new Set(data.metadata.enabled_handlers || [])

            // Update the set based on the toggle
            if (enabled) {
                currentEnabled.add(handler)
            } else {
                currentEnabled.delete(handler)
            }

            // Call API to update handlers
            const newData = await apiClient.updateHandlers(Array.from(currentEnabled))

            // Update local state with new correction data
            // This API call returns the *entire* new state, so treat it as a single history step
            updateDataWithHistory(newData, `toggle handler ${handler}`); // Update history

            // Clear any existing modals or highlights
            setModalContent(null)
            setFlashingType(null)
            setHighlightInfo(null)

            // Flash the updated corrections
            handleFlash('corrected')
        } catch (error) {
            console.error('Failed to update handlers:', error)
            alert('Failed to update correction handlers. Please try again.')
        } finally {
            setIsUpdatingHandlers(false);
        }
    }, [apiClient, data.metadata.enabled_handlers, handleFlash, updateDataWithHistory])

    const handleHandlerClick = useCallback((handler: string) => {
        if (debugLog) {
            console.log('Handler clicked:', handler);
        }
        setFlashingHandler(handler);
        setFlashingType('handler');
        if (debugLog) {
            console.log('Set flashingHandler to:', handler);
            console.log('Set flashingType to: handler');
        }
        // Clear the flash after a short delay
        setTimeout(() => {
            if (debugLog) {
                console.log('Clearing flash state');
            }
            setFlashingHandler(null);
            setFlashingType(null);
        }, 1500);
    }, []);

    // Wrap setModalSpacebarHandler in useCallback
    const handleSetModalSpacebarHandler = useCallback((handler: (() => (e: KeyboardEvent) => void) | undefined) => {
        if (debugLog) {
            console.log('LyricsAnalyzer - Setting modal handler:', {
                hasHandler: !!handler
            })
        }
        // Update the global modal handler
        setModalHandler(handler ? handler() : undefined, !!handler)
    }, [])

    // Add new handler for adding lyrics
    const handleAddLyrics = useCallback(async (source: string, lyrics: string) => {
        if (!apiClient) return

        try {
            setIsAddingLyrics(true)
            const newData = await apiClient.addLyrics(source, lyrics)
            // This API call returns the *entire* new state
            updateDataWithHistory(newData, 'add lyrics'); // Update history
        } finally {
            setIsAddingLyrics(false)
        }
    }, [apiClient, updateDataWithHistory])

    const handleFindReplace = (findText: string, replaceText: string, options: { caseSensitive: boolean, useRegex: boolean, fullTextMode: boolean }) => {
        const newData = findAndReplace(data, findText, replaceText, options)
        updateDataWithHistory(newData, 'find/replace'); // Update history
    }

    // Add handler for Un-Correct All functionality
    const handleUnCorrectAll = useCallback(() => {
        if (!originalData.original_segments) {
            console.warn('No original segments available for un-correcting')
            return
        }

        if (window.confirm('Are you sure you want to revert all segments to their original transcribed state? This will undo all corrections made.')) {
            console.log('Un-Correct All: Reverting all segments to original transcribed state', {
                originalSegmentCount: originalData.original_segments.length,
                currentSegmentCount: data.corrected_segments.length
            })

            // Create new data with original segments as corrected segments
            const newData: CorrectionData = {
                ...data,
                corrected_segments: JSON.parse(JSON.stringify(originalData.original_segments))
            }

            updateDataWithHistory(newData, 'un-correct all segments')
        }
    }, [originalData.original_segments, data, updateDataWithHistory])

    // Add handler for Replace All Lyrics functionality
    const handleReplaceAllLyrics = useCallback(() => {
        console.log('ReplaceAllLyrics - Opening modal')
        setIsReplaceAllLyricsModalOpen(true)
    }, [])

    // Handle saving new segments from Replace All Lyrics
    const handleSaveReplaceAllLyrics = useCallback((newSegments: LyricsSegment[]) => {
        console.log('ReplaceAllLyrics - Saving new segments:', {
            segmentCount: newSegments.length,
            totalWords: newSegments.reduce((count, segment) => count + segment.words.length, 0)
        })

        // Create new data with the replaced segments
        const newData = {
            ...data,
            corrected_segments: newSegments
        }
        
        updateDataWithHistory(newData, 'replace all lyrics')
        setIsReplaceAllLyricsModalOpen(false)
    }, [data, updateDataWithHistory])



    // Undo/Redo handlers
    const handleUndo = useCallback(() => {
        if (historyIndex > 0) {
            const newIndex = historyIndex - 1;
            if (debugLog) {
                console.log(`[DEBUG] Undo: moving from index ${historyIndex} to ${newIndex}. History length: ${history.length}`);
            }
            setHistoryIndex(newIndex);
        } else {
            if (debugLog) {
                console.log(`[DEBUG] Undo: already at the beginning (index ${historyIndex})`);
            }
        }
    }, [historyIndex, history])

    const handleRedo = useCallback(() => {
        if (historyIndex < history.length - 1) {
            const newIndex = historyIndex + 1;
            if (debugLog) {
                console.log(`[DEBUG] Redo: moving from index ${historyIndex} to ${newIndex}. History length: ${history.length}`);
            }
            setHistoryIndex(newIndex);
        } else {
            if (debugLog) {
                console.log(`[DEBUG] Redo: already at the end (index ${historyIndex}, history length ${history.length})`);
            }
        }
    }, [historyIndex, history])

    // Determine if Undo/Redo is possible
    const canUndo = historyIndex > 0
    const canRedo = historyIndex < history.length - 1

    // Memoize the metric click handlers
    const metricClickHandlers = useMemo(() => ({
        anchor: () => handleFlash('anchor'),
        corrected: () => handleFlash('corrected'),
        uncorrected: () => handleFlash('uncorrected')
    }), [handleFlash]);

    // Determine if any modal is open to disable highlighting
    const isAnyModalOpenMemo = useMemo(() => isAnyModalOpen, [isAnyModalOpen]);
    
    // For the TranscriptionView, we need to apply the timing offset when displaying
    const displayData = useMemo(() => {
        return timingOffsetMs !== 0 
            ? applyOffsetToCorrectionData(data, timingOffsetMs)
            : data;
    }, [data, timingOffsetMs]);

    // Handler for opening the timing offset modal
    const handleOpenTimingOffsetModal = useCallback(() => {
        setIsTimingOffsetModalOpen(true)
    }, [])

    // Handler for applying the timing offset
    const handleApplyTimingOffset = useCallback((offsetMs: number) => {
        // Only update if the offset has changed
        if (offsetMs !== timingOffsetMs) {
            console.log(`[TIMING] handleApplyTimingOffset: Changing offset from ${timingOffsetMs}ms to ${offsetMs}ms`);
            setTimingOffsetMs(offsetMs)
            
            // If we're applying an offset, we don't need to update history
            // since we're not modifying the original data
            if (debugLog) {
                console.log(`[DEBUG] handleApplyTimingOffset: Setting offset to ${offsetMs}ms`);
            }
        } else {
            console.log(`[TIMING] handleApplyTimingOffset: Offset unchanged at ${offsetMs}ms`);
        }
    }, [timingOffsetMs])

    // Add logging for timing offset changes
    useEffect(() => {
        console.log(`[TIMING] timingOffsetMs changed to: ${timingOffsetMs}ms`);
    }, [timingOffsetMs]);
    
    return (
        <Box sx={{
            p: 1,
            pb: 3,
            maxWidth: '100%',
            overflowX: 'hidden'
        }}>
            <MemoizedHeader
                isReadOnly={isReadOnly}
                onFileLoad={onFileLoad}
                data={data}
                onMetricClick={metricClickHandlers}
                effectiveMode={effectiveMode}
                onModeChange={setInteractionMode}
                apiClient={apiClient}
                audioHash={audioHash}
                onTimeUpdate={setCurrentAudioTime}
                onHandlerToggle={handleHandlerToggle}
                isUpdatingHandlers={isUpdatingHandlers}
                onHandlerClick={handleHandlerClick}
                onFindReplace={() => setIsFindReplaceModalOpen(true)}
                onEditAll={handleReplaceAllLyrics}
                onTimingOffset={handleOpenTimingOffsetModal}
                timingOffsetMs={timingOffsetMs}
                onUndo={handleUndo}
                onRedo={handleRedo}
                canUndo={canUndo}
                canRedo={canRedo}
                onUnCorrectAll={handleUnCorrectAll}
            />

            <Grid container direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <MemoizedTranscriptionView
                        data={displayData}
                        mode={effectiveMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        flashingHandler={flashingHandler}
                        highlightInfo={highlightInfo}
                        onPlaySegment={handlePlaySegment}
                        currentTime={currentAudioTime}
                        anchors={data.anchor_sequences}
                        disableHighlighting={isAnyModalOpenMemo}
                        onDataChange={(updatedData) => {
                            // Direct data change from TranscriptionView (e.g., drag-and-drop)
                            // needs to update history
                            updateDataWithHistory(updatedData, 'direct data change');
                        }}
                    />
                    {!isReadOnly && apiClient && (
                        <Box sx={{
                            mt: 2,
                            mb: 3,
                            display: 'flex',
                            justifyContent: 'space-between',
                            width: '100%'
                        }}>
                            <Button
                                variant="outlined"
                                color="warning"
                                onClick={handleResetCorrections}
                                startIcon={<RestoreFromTrash />}
                            >
                                Reset Corrections
                            </Button>
                            <Button
                                variant="contained"
                                onClick={handleFinishReview}
                                disabled={isReviewComplete}
                                endIcon={<OndemandVideo />}
                            >
                                {isReviewComplete ? 'Review Complete' : 'Preview Video'}
                            </Button>
                        </Box>
                    )}
                </Grid>
                <Grid item xs={12} md={6}>
                    <MemoizedReferenceView
                        referenceSources={data.reference_lyrics}
                        anchors={data.anchor_sequences}
                        gaps={data.gap_sequences}
                        mode={effectiveMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        highlightInfo={highlightInfo}
                        currentSource={currentSource}
                        onSourceChange={setCurrentSource}
                        corrected_segments={data.corrected_segments}
                        corrections={data.corrections}
                        onAddLyrics={() => setIsAddLyricsModalOpen(true)}
                    />
                </Grid>
            </Grid>



            <EditModal
                open={Boolean(editModalSegment)}
                onClose={() => {
                    setEditModalSegment(null)
                    handleSetModalSpacebarHandler(undefined)
                }}
                segment={editModalSegment?.segment ? 
                    timingOffsetMs !== 0 ? 
                        applyOffsetToSegment(editModalSegment.segment, timingOffsetMs) : 
                        editModalSegment.segment : 
                    null}
                segmentIndex={editModalSegment?.index ?? null}
                originalSegment={editModalSegment?.originalSegment ? 
                    timingOffsetMs !== 0 ? 
                        applyOffsetToSegment(editModalSegment.originalSegment, timingOffsetMs) : 
                        editModalSegment.originalSegment : 
                    null}
                onSave={handleUpdateSegment}
                onDelete={handleDeleteSegment}
                onAddSegment={handleAddSegment}
                onSplitSegment={handleSplitSegment}
                onMergeSegment={handleMergeSegment}
                onPlaySegment={handlePlaySegment}
                currentTime={currentAudioTime}
                setModalSpacebarHandler={handleSetModalSpacebarHandler}
                originalTranscribedSegment={
                    editModalSegment?.segment && editModalSegment?.index !== null && originalData.original_segments
                        ? (() => {
                            const origSegment = originalData.original_segments.find(
                                (s: LyricsSegment) => s.id === editModalSegment.segment.id
                            ) || null;
                            
                            return origSegment && timingOffsetMs !== 0 
                                ? applyOffsetToSegment(origSegment, timingOffsetMs) 
                                : origSegment;
                        })()
                        : null
                }
            />

            <ReviewChangesModal
                open={isReviewModalOpen}
                onClose={() => setIsReviewModalOpen(false)}
                originalData={originalData}
                updatedData={data}
                onSubmit={handleSubmitToServer}
                apiClient={apiClient}
                setModalSpacebarHandler={handleSetModalSpacebarHandler}
                timingOffsetMs={timingOffsetMs}
            />

            <AddLyricsModal
                open={isAddLyricsModalOpen}
                onClose={() => setIsAddLyricsModalOpen(false)}
                onSubmit={handleAddLyrics}
                isSubmitting={isAddingLyrics}
            />

            <FindReplaceModal
                open={isFindReplaceModalOpen}
                onClose={() => setIsFindReplaceModalOpen(false)}
                onReplace={handleFindReplace}
                data={data}
            />

            <TimingOffsetModal
                open={isTimingOffsetModalOpen}
                onClose={() => setIsTimingOffsetModalOpen(false)}
                currentOffset={timingOffsetMs}
                onApply={handleApplyTimingOffset}
            />

            <ReplaceAllLyricsModal
                open={isReplaceAllLyricsModalOpen}
                onClose={() => setIsReplaceAllLyricsModalOpen(false)}
                onSave={handleSaveReplaceAllLyrics}
                onPlaySegment={handlePlaySegment}
                currentTime={currentAudioTime}
                setModalSpacebarHandler={handleSetModalSpacebarHandler}
            />
            
            {pendingAnnotation && (
                <CorrectionAnnotationModal
                    open={isAnnotationModalOpen}
                    onClose={() => {
                        setIsAnnotationModalOpen(false)
                        setPendingAnnotation(null)
                    }}
                    onSave={handleSaveAnnotation}
                    onSkip={handleSkipAnnotation}
                    originalText={pendingAnnotation.originalText}
                    correctedText={pendingAnnotation.correctedText}
                    wordIdsAffected={pendingAnnotation.wordIdsAffected}
                    agenticProposal={undefined} // TODO: Pass agentic proposal if available
                    referenceSources={Object.keys(data.reference_lyrics || {})}
                    audioHash={audioHash}
                    artist={data.metadata?.audio_filepath?.split('/').pop()?.split('.')[0] || 'Unknown'}
                    title={data.metadata?.audio_filepath?.split('/').pop()?.split('.')[0] || 'Unknown'}
                    sessionId={audioHash} // Use audio hash as session ID for now
                    gapId={pendingAnnotation.gapId}
                />
            )}
            
            {selectedCorrection && (
                <CorrectionDetailCard
                    open={correctionDetailOpen}
                    onClose={() => {
                        setCorrectionDetailOpen(false)
                        setSelectedCorrection(null)
                    }}
                    originalWord={selectedCorrection.originalWord}
                    correctedWord={selectedCorrection.correctedWord}
                    category={selectedCorrection.category}
                    confidence={selectedCorrection.confidence}
                    reason={selectedCorrection.reason}
                    handler={selectedCorrection.handler}
                    source={selectedCorrection.source}
                    onRevert={() => {
                        handleRevertCorrection(selectedCorrection.wordId)
                        setCorrectionDetailOpen(false)
                        setSelectedCorrection(null)
                    }}
                    onEdit={() => {
                        handleEditCorrection(selectedCorrection.wordId)
                        setCorrectionDetailOpen(false)
                        setSelectedCorrection(null)
                    }}
                    onAccept={() => {
                        handleAcceptCorrection(selectedCorrection.wordId)
                        setCorrectionDetailOpen(false)
                        setSelectedCorrection(null)
                    }}
                />
            )}
        </Box>
    )
} 