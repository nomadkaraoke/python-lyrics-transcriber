import {
    AnchorSequence,
    CorrectionData,
    GapSequence,
    HighlightInfo,
    InteractionMode,
    LyricsSegment
} from '../types'
import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Grid, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState, useEffect } from 'react'
import { ApiClient } from '../api'
import CorrectionMetrics from './CorrectionMetrics'
import DetailsModal from './DetailsModal'
import ModeSelector from './ModeSelector'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import { WordClickInfo, FlashType } from './shared/types'
import EditModal from './EditModal'
import ReviewChangesModal from './ReviewChangesModal'
import AudioPlayer from './AudioPlayer'
import { initializeDataWithIds, normalizeDataForSubmission } from './shared/utils/initializeDataWithIds'
import {
    addSegmentBefore,
    splitSegment,
    deleteSegment,
    updateSegment
} from './shared/utils/segmentOperations'
import { loadSavedData, saveData, clearSavedData } from './shared/utils/localStorage'
import { setupKeyboardHandlers } from './shared/utils/keyboardHandlers'

// Add type for window augmentation at the top of the file
declare global {
    interface Window {
        toggleAudioPlayback?: () => void;
        seekAndPlayAudio?: (startTime: number) => void;
    }
}

interface LyricsAnalyzerProps {
    data: CorrectionData
    onFileLoad: () => void
    onShowMetadata: () => void
    apiClient: ApiClient | null
    isReadOnly: boolean
}

export type ModalContent = {
    type: 'anchor'
    data: AnchorSequence & {
        wordId: string
        word?: string
    }
} | {
    type: 'gap'
    data: GapSequence & {
        wordId: string
        word: string
    }
}

export default function LyricsAnalyzer({ data: initialData, onFileLoad, apiClient, isReadOnly }: LyricsAnalyzerProps) {
    const [modalContent, setModalContent] = useState<ModalContent | null>(null)
    const [flashingType, setFlashingType] = useState<FlashType>(null)
    const [highlightInfo, setHighlightInfo] = useState<HighlightInfo | null>(null)
    const [currentSource, setCurrentSource] = useState<string>(() => {
        const availableSources = Object.keys(initialData.reference_texts)
        return availableSources.length > 0 ? availableSources[0] : ''
    })
    const [isReviewComplete, setIsReviewComplete] = useState(false)
    const [data, setData] = useState(() => initializeDataWithIds(initialData))
    // Create deep copy of initial data for comparison later
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
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

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
        if (effectiveMode === 'edit') {
            const segment = data.corrected_segments.find(segment =>
                segment.words.some(word => word.id === info.word_id)
            )

            if (segment) {
                const segmentIndex = data.corrected_segments.indexOf(segment)
                setEditModalSegment({
                    segment,
                    index: segmentIndex,
                    originalSegment: originalData.corrected_segments[segmentIndex]
                })
            }
        } else {
            // Update flash handling for anchors/gaps
            if (info.type === 'anchor' && info.anchor) {
                handleFlash('word', {
                    type: 'anchor',
                    word_ids: info.anchor.word_ids,
                    reference_word_ids: info.anchor.reference_word_ids
                })
            } else if (info.type === 'gap' && info.gap) {
                handleFlash('word', {
                    type: 'gap',
                    word_ids: info.gap.word_ids
                })
            }
        }
    }, [effectiveMode, data.corrected_segments, handleFlash, originalData.corrected_segments])

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
            const dataToSubmit = normalizeDataForSubmission(data)
            await apiClient.submitCorrections(dataToSubmit)

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
            clearSavedData(initialData.transcribed_text)
            const freshData = initializeDataWithIds(JSON.parse(JSON.stringify(initialData)))
            setData(freshData)
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

    return (
        <Box>
            {isReadOnly && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, color: 'text.secondary' }}>
                    <LockIcon sx={{ mr: 1 }} />
                    <Typography variant="body2">
                        View Only Mode
                    </Typography>
                </Box>
            )}
            <Box sx={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                gap: 2,
                justifyContent: 'space-between',
                alignItems: isMobile ? 'stretch' : 'center',
                mb: 3
            }}>
                <Typography variant="h4" sx={{ fontSize: isMobile ? '1.75rem' : '2.125rem' }}>
                    Lyrics Correction Review
                </Typography>
                {isReadOnly && (
                    <Button
                        variant="outlined"
                        startIcon={<UploadFileIcon />}
                        onClick={onFileLoad}
                        fullWidth={isMobile}
                    >
                        Load File
                    </Button>
                )}
            </Box>

            <Box sx={{ mb: 3 }}>
                <CorrectionMetrics
                    // Anchor metrics
                    anchorCount={data.metadata.anchor_sequences_count}
                    multiSourceAnchors={data.anchor_sequences?.filter(anchor =>
                        // Add null checks
                        anchor?.reference_word_ids &&
                        Object.keys(anchor.reference_word_ids || {}).length > 1
                    ).length ?? 0}
                    anchorWordCount={data.anchor_sequences?.reduce((sum, anchor) =>
                        sum + (anchor.length || 0), 0) ?? 0}
                    // Gap metrics
                    correctedGapCount={data.gap_sequences?.filter(gap =>
                        gap.corrections?.length > 0).length ?? 0}
                    uncorrectedGapCount={data.gap_sequences?.filter(gap =>
                        !gap.corrections?.length).length ?? 0}
                    uncorrectedGaps={data.gap_sequences
                        ?.filter(gap => !gap.corrections?.length && gap.word_ids)
                        .map(gap => ({
                            position: gap.word_ids?.[0] ?? '',
                            length: gap.length ?? 0
                        })) ?? []}
                    // Correction details
                    replacedCount={data.gap_sequences?.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => !c.is_deletion && !c.split_total).length ?? 0), 0) ?? 0}
                    addedCount={data.gap_sequences?.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => c.split_total).length ?? 0), 0) ?? 0}
                    deletedCount={data.gap_sequences?.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => c.is_deletion).length ?? 0), 0) ?? 0}
                    onMetricClick={{
                        anchor: () => handleFlash('anchor'),
                        corrected: () => handleFlash('corrected'),
                        uncorrected: () => handleFlash('uncorrected')
                    }}
                    totalWords={data.metadata.total_words}
                />
            </Box>

            <Box sx={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                gap: 5,
                alignItems: 'flex-start',
                justifyContent: 'flex-start',
                mb: 3
            }}>
                <ModeSelector
                    effectiveMode={effectiveMode}
                    onChange={setInteractionMode}
                />
                <AudioPlayer
                    apiClient={apiClient}
                    onTimeUpdate={setCurrentAudioTime}
                />
            </Box>

            <Grid container spacing={2} direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <TranscriptionView
                        data={data}
                        mode={effectiveMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        highlightInfo={highlightInfo}
                        onPlaySegment={handlePlaySegment}
                        currentTime={currentAudioTime}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <ReferenceView
                        referenceTexts={data.reference_texts}
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
                    />
                </Grid>
            </Grid>

            <DetailsModal
                open={modalContent !== null}
                content={modalContent}
                onClose={() => setModalContent(null)}
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