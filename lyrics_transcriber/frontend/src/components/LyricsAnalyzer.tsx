import {
    AnchorSequence,
    CorrectionData,
    GapSequence,
    HighlightInfo,
    InteractionMode,
    LyricsSegment
} from '../types'
import { Box, Button, Grid, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState, useEffect } from 'react'
import { ApiClient } from '../api'
import DetailsModal from './DetailsModal'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import { WordClickInfo, FlashType } from './shared/types'
import EditModal from './EditModal'
import ReviewChangesModal from './ReviewChangesModal'
import {
    addSegmentBefore,
    splitSegment,
    deleteSegment,
    updateSegment
} from './shared/utils/segmentOperations'
import { loadSavedData, saveData, clearSavedData } from './shared/utils/localStorage'
import { setupKeyboardHandlers } from './shared/utils/keyboardHandlers'
import Header from './Header'
import { findWordById, getWordsFromIds } from './shared/utils/wordUtils'

// Add type for window augmentation at the top of the file
declare global {
    interface Window {
        toggleAudioPlayback?: () => void;
        seekAndPlayAudio?: (startTime: number) => void;
    }
}

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
    const [data, setData] = useState(initialData)
    const [originalData] = useState(() => JSON.parse(JSON.stringify(initialData)))
    const [interactionMode, setInteractionMode] = useState<InteractionMode>('details')
    const [isShiftPressed, setIsShiftPressed] = useState(false)
    const [isCtrlPressed, setIsCtrlPressed] = useState(false)
    const [editModalSegment, setEditModalSegment] = useState<{
        segment: LyricsSegment
        index: number
        originalSegment: LyricsSegment
    } | null>(null)
    const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
    const [currentAudioTime, setCurrentAudioTime] = useState(0)
    const [isUpdatingHandlers, setIsUpdatingHandlers] = useState(false)
    const [flashingHandler, setFlashingHandler] = useState<string | null>(null)
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

    // Update debug logging to use new ID-based structure
    useEffect(() => {
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
    }, [initialData]);

    // Load saved data
    useEffect(() => {
        const savedData = loadSavedData(initialData)
        if (savedData && window.confirm('Found saved progress for this song. Would you like to restore it?')) {
            setData(savedData)
        }
    }, [initialData])

    // Save data
    useEffect(() => {
        if (!isReadOnly) {
            saveData(data, initialData)
        }
    }, [data, isReadOnly, initialData])

    // Keyboard handlers
    useEffect(() => {
        const { handleKeyDown, handleKeyUp } = setupKeyboardHandlers({
            setIsShiftPressed,
            setIsCtrlPressed
        })

        window.addEventListener('keydown', handleKeyDown)
        window.addEventListener('keyup', handleKeyUp)
        return () => {
            window.removeEventListener('keydown', handleKeyDown)
            window.removeEventListener('keyup', handleKeyUp)
            document.body.style.userSelect = ''
        }
    }, [])

    // Calculate effective mode based on modifier key states
    const effectiveMode = isShiftPressed ? 'highlight' :
        isCtrlPressed ? 'edit' :
            interactionMode

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
        console.log('LyricsAnalyzer handleWordClick:', { info });

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
                        return [
                            source,
                            getWordsFromIds([tempSourceSegment], ids)
                        ]
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
                g.transcribed_word_ids.includes(info.word_id) ||
                Object.values(g.reference_word_ids).some(ids =>
                    ids.includes(info.word_id)
                )
            );

            if (gap) {
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
                        return [
                            source,
                            getWordsFromIds([tempSourceSegment], ids)
                        ]
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
        } else if (effectiveMode === 'details') {
            if (info.type === 'anchor' && info.anchor) {
                const word = findWordById(data.corrected_segments, info.word_id);
                setModalContent({
                    type: 'anchor',
                    data: {
                        ...info.anchor,
                        wordId: info.word_id,
                        word: word?.text,
                        anchor_sequences: data.anchor_sequences
                    }
                });
            } else if (info.type === 'gap' && info.gap) {
                const word = findWordById(data.corrected_segments, info.word_id);
                setModalContent({
                    type: 'gap',
                    data: {
                        ...info.gap,
                        wordId: info.word_id,
                        word: word?.text || '',
                        anchor_sequences: data.anchor_sequences
                    }
                });
            }
        }
    }, [data, effectiveMode, setModalContent]);

    const handleUpdateSegment = useCallback((updatedSegment: LyricsSegment) => {
        if (!editModalSegment) return
        const newData = updateSegment(data, editModalSegment.index, updatedSegment)
        setData(newData)
        setEditModalSegment(null)
    }, [data, editModalSegment])

    const handleDeleteSegment = useCallback((segmentIndex: number) => {
        const newData = deleteSegment(data, segmentIndex)
        setData(newData)
    }, [data])

    const handleFinishReview = useCallback(() => {
        setIsReviewModalOpen(true)
    }, [])

    const handleSubmitToServer = useCallback(async () => {
        if (!apiClient) return

        try {
            console.log('Submitting changes to server')
            await apiClient.submitCorrections(data)

            setIsReviewComplete(true)
            setIsReviewModalOpen(false)

            // Close the browser tab
            window.close()
        } catch (error) {
            console.error('Failed to submit corrections:', error)
            alert('Failed to submit corrections. Please try again.')
        }
    }, [apiClient, data])

    // Update play segment handler
    const handlePlaySegment = useCallback((startTime: number) => {
        if (window.seekAndPlayAudio) {
            window.seekAndPlayAudio(startTime)
        }
    }, [])

    const handleResetCorrections = useCallback(() => {
        if (window.confirm('Are you sure you want to reset all corrections? This cannot be undone.')) {
            clearSavedData(initialData)
            setData(JSON.parse(JSON.stringify(initialData)))
            setModalContent(null)
            setFlashingType(null)
            setHighlightInfo(null)
            setInteractionMode('details')
        }
    }, [initialData])

    const handleAddSegment = useCallback((beforeIndex: number) => {
        const newData = addSegmentBefore(data, beforeIndex)
        setData(newData)
    }, [data])

    const handleSplitSegment = useCallback((segmentIndex: number, afterWordIndex: number) => {
        const newData = splitSegment(data, segmentIndex, afterWordIndex)
        if (newData) {
            setData(newData)
            setEditModalSegment(null)
        }
    }, [data])

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
            setData(newData)

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
    }, [apiClient, data.metadata.enabled_handlers, handleFlash])

    const handleHandlerClick = useCallback((handler: string) => {
        console.log('Handler clicked:', handler);
        setFlashingHandler(handler);
        setFlashingType('handler');
        console.log('Set flashingHandler to:', handler);
        console.log('Set flashingType to: handler');

        // Clear the flash after a short delay
        setTimeout(() => {
            console.log('Clearing flash state');
            setFlashingHandler(null);
            setFlashingType(null);
        }, 1500);
    }, []);

    return (
        <Box sx={{
            p: 3,
            pb: 6,
            maxWidth: '100%',
            overflowX: 'hidden'
        }}>
            <Header
                isReadOnly={isReadOnly}
                onFileLoad={onFileLoad}
                data={data}
                onMetricClick={{
                    anchor: () => handleFlash('anchor'),
                    corrected: () => handleFlash('corrected'),
                    uncorrected: () => handleFlash('uncorrected')
                }}
                effectiveMode={effectiveMode}
                onModeChange={setInteractionMode}
                apiClient={apiClient}
                audioHash={audioHash}
                onTimeUpdate={setCurrentAudioTime}
                onHandlerToggle={handleHandlerToggle}
                isUpdatingHandlers={isUpdatingHandlers}
                onHandlerClick={handleHandlerClick}
            />

            <Grid container spacing={2} direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <TranscriptionView
                        data={data}
                        mode={effectiveMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        flashingHandler={flashingHandler}
                        highlightInfo={highlightInfo}
                        onPlaySegment={handlePlaySegment}
                        currentTime={currentAudioTime}
                        anchors={data.anchor_sequences}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <ReferenceView
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
                    />
                </Grid>
            </Grid>

            <DetailsModal
                open={modalContent !== null}
                content={modalContent}
                onClose={() => setModalContent(null)}
                allCorrections={data.corrections}
                referenceLyrics={data.reference_lyrics}
            />

            <EditModal
                open={Boolean(editModalSegment)}
                onClose={() => setEditModalSegment(null)}
                segment={editModalSegment?.segment ?? null}
                segmentIndex={editModalSegment?.index ?? null}
                originalSegment={editModalSegment?.originalSegment ?? null}
                onSave={handleUpdateSegment}
                onDelete={handleDeleteSegment}
                onAddSegment={handleAddSegment}
                onSplitSegment={handleSplitSegment}
                onPlaySegment={handlePlaySegment}
                currentTime={currentAudioTime}
            />

            <ReviewChangesModal
                open={isReviewModalOpen}
                onClose={() => setIsReviewModalOpen(false)}
                originalData={originalData}
                updatedData={data}
                onSubmit={handleSubmitToServer}
                apiClient={apiClient}
            />

            {!isReadOnly && apiClient && (
                <Box sx={{ mt: 2, mb: 3, display: 'flex', gap: 2 }}>
                    <Button
                        variant="contained"
                        onClick={handleFinishReview}
                        disabled={isReviewComplete}
                    >
                        {isReviewComplete ? 'Review Complete' : 'Finish Review'}
                    </Button>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={handleResetCorrections}
                    >
                        Reset Corrections
                    </Button>
                </Box>
            )}
        </Box>
    )
} 