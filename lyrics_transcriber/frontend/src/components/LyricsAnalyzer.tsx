import { useState, useEffect, useCallback, useMemo, memo } from 'react'
import {
    AnchorSequence,
    CorrectionData,
    GapSequence,
    HighlightInfo,
    InteractionMode,
    LyricsSegment,
    ReferenceSource,
    WordCorrection
} from '../types'
import { Box, Button, Grid, useMediaQuery, useTheme } from '@mui/material'
import { ApiClient } from '../api'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import { WordClickInfo, FlashType } from './shared/types'
import EditModal from './EditModal'
import ReviewChangesModal from './ReviewChangesModal'
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
    canRedo
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
    const [isEditAllModalOpen, setIsEditAllModalOpen] = useState(false)
    const [globalEditSegment, setGlobalEditSegment] = useState<LyricsSegment | null>(null)
    const [originalGlobalSegment, setOriginalGlobalSegment] = useState<LyricsSegment | null>(null)
    const [originalTranscribedGlobalSegment, setOriginalTranscribedGlobalSegment] = useState<LyricsSegment | null>(null)
    const [isLoadingGlobalEdit, setIsLoadingGlobalEdit] = useState(false)
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
            isEditAllModalOpen ||
            isTimingOffsetModalOpen
        )
        setIsAnyModalOpen(modalOpen)
    }, [modalContent, editModalSegment, isReviewModalOpen, isAddLyricsModalOpen, isFindReplaceModalOpen, isEditAllModalOpen, isTimingOffsetModalOpen])

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
        setEditModalSegment(null)
    }, [history, historyIndex, editModalSegment, updateDataWithHistory])

    const handleDeleteSegment = useCallback((segmentIndex: number) => {
        const newData = deleteSegment(data, segmentIndex)
        updateDataWithHistory(newData, 'delete segment')
    }, [data, updateDataWithHistory])

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

            setIsReviewComplete(true)
            setIsReviewModalOpen(false)

            // Close the browser tab
            window.close()
        } catch (error) {
            console.error('Failed to submit corrections:', error)
            alert('Failed to submit corrections. Please try again.')
        }
    }, [apiClient, data, timingOffsetMs])

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

    // Add handler for Edit All functionality
    const handleEditAll = useCallback(() => {
        console.log('EditAll - Starting process');

        // Create empty placeholder segments to prevent the modal from closing
        const placeholderSegment: LyricsSegment = {
            id: 'loading-placeholder',
            words: [],
            text: '',
            start_time: 0,
            end_time: 1
        };

        // Set placeholder segments first
        setGlobalEditSegment(placeholderSegment);
        setOriginalGlobalSegment(placeholderSegment);

        // Show loading state
        setIsLoadingGlobalEdit(true);
        console.log('EditAll - Set loading state to true');

        // Open the modal with placeholder data
        setIsEditAllModalOpen(true);
        console.log('EditAll - Set modal open to true');

        // Use requestAnimationFrame to ensure the modal with loading state is rendered
        // before doing the expensive operation
        requestAnimationFrame(() => {
            console.log('EditAll - Inside requestAnimationFrame');

            // Use setTimeout to allow the modal to render before doing the expensive operation
            setTimeout(() => {
                console.log('EditAll - Inside setTimeout, starting data processing');

                try {
                    console.time('EditAll - Data processing');

                    // Create a combined segment with all words from all segments
                    const allWords = data.corrected_segments.flatMap(segment => segment.words)
                    console.log(`EditAll - Collected ${allWords.length} words from all segments`);

                    // Sort words by start time to maintain chronological order
                    const sortedWords = [...allWords].sort((a, b) => {
                        const aTime = a.start_time ?? 0
                        const bTime = b.start_time ?? 0
                        return aTime - bTime
                    })
                    console.log('EditAll - Sorted words by start time');

                    // Create a global segment containing all words
                    const globalSegment: LyricsSegment = {
                        id: 'global-edit',
                        words: sortedWords,
                        text: sortedWords.map(w => w.text).join(' '),
                        start_time: sortedWords[0]?.start_time ?? null,
                        end_time: sortedWords[sortedWords.length - 1]?.end_time ?? null
                    }
                    console.log('EditAll - Created global segment');

                    // Store the original global segment for reset functionality
                    setGlobalEditSegment(globalSegment)
                    console.log('EditAll - Set global edit segment');

                    setOriginalGlobalSegment(JSON.parse(JSON.stringify(globalSegment)))
                    console.log('EditAll - Set original global segment');

                    // Create the original transcribed global segment for Un-Correct functionality
                    if (originalData.original_segments) {
                        console.log('EditAll - Processing original segments for Un-Correct functionality');

                        // Get all words from original segments
                        const originalWords = originalData.original_segments.flatMap((segment: LyricsSegment) => segment.words)
                        console.log(`EditAll - Collected ${originalWords.length} words from original segments`);

                        // Sort words by start time
                        const sortedOriginalWords = [...originalWords].sort((a, b) => {
                            const aTime = a.start_time ?? 0
                            const bTime = b.start_time ?? 0
                            return aTime - bTime
                        })
                        console.log('EditAll - Sorted original words by start time');

                        // Create the original transcribed global segment
                        const originalTranscribedGlobal: LyricsSegment = {
                            id: 'original-transcribed-global',
                            words: sortedOriginalWords,
                            text: sortedOriginalWords.map(w => w.text).join(' '),
                            start_time: sortedOriginalWords[0]?.start_time ?? null,
                            end_time: sortedOriginalWords[sortedOriginalWords.length - 1]?.end_time ?? null
                        }
                        console.log('EditAll - Created original transcribed global segment');

                        setOriginalTranscribedGlobalSegment(originalTranscribedGlobal)
                        console.log('EditAll - Set original transcribed global segment');
                    } else {
                        setOriginalTranscribedGlobalSegment(null)
                        console.log('EditAll - No original segments found, set original transcribed global segment to null');
                    }

                    console.timeEnd('EditAll - Data processing');
                } catch (error) {
                    console.error('Error preparing global edit data:', error);
                } finally {
                    // Clear loading state
                    console.log('EditAll - Finished processing, setting loading state to false');
                    setIsLoadingGlobalEdit(false);
                }
            }, 100); // Small delay to allow the modal to render
        });
    }, [data.corrected_segments, originalData.original_segments])

    // Handle saving the global edit
    const handleSaveGlobalEdit = useCallback((updatedSegment: LyricsSegment) => {
        console.log('Global Edit - Saving with new approach:', {
            updatedSegmentId: updatedSegment.id,
            wordCount: updatedSegment.words.length,
            originalSegmentCount: data.corrected_segments.length,
            originalTotalWordCount: data.corrected_segments.reduce((count, segment) => count + segment.words.length, 0)
        })

        // Get the updated words from the global segment
        const updatedWords = updatedSegment.words

        // Create a new array of segments with the same structure as the original
        const updatedSegments = []
        let wordIndex = 0

        // Distribute words to segments based on the original segment sizes
        for (const segment of data.corrected_segments) {
            const originalWordCount = segment.words.length

            // Get the words for this segment from the updated global segment
            const segmentWords = []
            const endIndex = Math.min(wordIndex + originalWordCount, updatedWords.length)

            for (let i = wordIndex; i < endIndex; i++) {
                segmentWords.push(updatedWords[i])
            }

            // Update the word index for the next segment
            wordIndex = endIndex

            // If we have words for this segment, create an updated segment
            if (segmentWords.length > 0) {
                // Recalculate segment start and end times
                const validStartTimes = segmentWords.map(w => w.start_time).filter((t): t is number => t !== null)
                const validEndTimes = segmentWords.map(w => w.end_time).filter((t): t is number => t !== null)

                const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
                const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

                // Create the updated segment
                updatedSegments.push({
                    ...segment,
                    words: segmentWords,
                    text: segmentWords.map(w => w.text).join(' '),
                    start_time: segmentStartTime,
                    end_time: segmentEndTime
                })
            }
        }

        // If there are any remaining words, add them to the last segment
        if (wordIndex < updatedWords.length) {
            const remainingWords = updatedWords.slice(wordIndex)
            const lastSegment = updatedSegments[updatedSegments.length - 1]

            // Combine the remaining words with the last segment
            const combinedWords = [...lastSegment.words, ...remainingWords]

            // Recalculate segment start and end times
            const validStartTimes = combinedWords.map(w => w.start_time).filter((t): t is number => t !== null)
            const validEndTimes = combinedWords.map(w => w.end_time).filter((t): t is number => t !== null)

            const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
            const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

            // Update the last segment
            updatedSegments[updatedSegments.length - 1] = {
                ...lastSegment,
                words: combinedWords,
                text: combinedWords.map(w => w.text).join(' '),
                start_time: segmentStartTime,
                end_time: segmentEndTime
            }
        }

        console.log('Global Edit - Updated Segments with new approach:', {
            segmentCount: updatedSegments.length,
            firstSegmentWordCount: updatedSegments[0]?.words.length,
            totalWordCount: updatedSegments.reduce((count, segment) => count + segment.words.length, 0),
            originalTotalWordCount: data.corrected_segments.reduce((count, segment) => count + segment.words.length, 0)
        })

        // Update the data with the new segments
        const newData = {
            ...data,
            corrected_segments: updatedSegments
        };
        updateDataWithHistory(newData, 'edit all'); // Update history

        // Close the modal
        setIsEditAllModalOpen(false)
        setGlobalEditSegment(null)
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
                onEditAll={handleEditAll}
                onTimingOffset={handleOpenTimingOffsetModal}
                timingOffsetMs={timingOffsetMs}
                onUndo={handleUndo}
                onRedo={handleRedo}
                canUndo={canUndo}
                canRedo={canRedo}
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
                open={isEditAllModalOpen}
                onClose={() => {
                    setIsEditAllModalOpen(false)
                    setGlobalEditSegment(null)
                    setOriginalGlobalSegment(null)
                    setOriginalTranscribedGlobalSegment(null)
                    handleSetModalSpacebarHandler(undefined)
                }}
                segment={globalEditSegment ? 
                    timingOffsetMs !== 0 ? 
                        applyOffsetToSegment(globalEditSegment, timingOffsetMs) : 
                        globalEditSegment : 
                    null}
                segmentIndex={null}
                originalSegment={originalGlobalSegment ? 
                    timingOffsetMs !== 0 ? 
                        applyOffsetToSegment(originalGlobalSegment, timingOffsetMs) : 
                        originalGlobalSegment : 
                    null}
                onSave={handleSaveGlobalEdit}
                onPlaySegment={handlePlaySegment}
                currentTime={currentAudioTime}
                setModalSpacebarHandler={handleSetModalSpacebarHandler}
                originalTranscribedSegment={originalTranscribedGlobalSegment ? 
                    timingOffsetMs !== 0 ? 
                        applyOffsetToSegment(originalTranscribedGlobalSegment, timingOffsetMs) : 
                        originalTranscribedGlobalSegment : 
                    null}
                isGlobal={true}
                isLoading={isLoadingGlobalEdit}
            />

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
        </Box>
    )
} 