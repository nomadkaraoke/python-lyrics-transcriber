import {
    CorrectionData,
    HighlightInfo,
    InteractionMode,
    LyricsData,
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

interface LyricsAnalyzerProps {
    data: CorrectionData
    onFileLoad: () => void
    onShowMetadata: () => void
    apiClient: ApiClient | null
    isReadOnly: boolean
}

export type ModalContent = {
    type: 'anchor'
    data: LyricsData['anchor_sequences'][0] & {
        position: number
        word?: string
    }
} | {
    type: 'gap'
    data: LyricsData['gap_sequences'][0] & {
        position: number
        word: string
    }
}

function normalizeDataForSubmission(data: CorrectionData): CorrectionData {
    // Create a deep clone to avoid modifying the original
    const normalized = JSON.parse(JSON.stringify(data))

    // Preserve floating point numbers with original precision
    const preserveFloats = (obj: Record<string, unknown>): void => {
        for (const key in obj) {
            const value = obj[key]
            if (typeof value === 'number') {
                // Handle integers and floats differently
                let formatted: string
                if (Number.isInteger(value)) {
                    formatted = value.toFixed(1)  // Force decimal point for integers
                } else {
                    formatted = value.toString()  // Keep original precision for floats
                }
                obj[key] = parseFloat(formatted)
            } else if (typeof value === 'object' && value !== null) {
                preserveFloats(value as Record<string, unknown>)
            }
        }
    }
    preserveFloats(normalized)
    return normalized
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
    const [data, setData] = useState(initialData)
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

    // Add local storage handling
    useEffect(() => {
        // On mount, try to load saved data
        const savedData = localStorage.getItem('lyrics_analyzer_data')
        if (savedData) {
            try {
                const parsed = JSON.parse(savedData)
                // Only restore if it's the same song (matching transcribed text)
                if (parsed.transcribed_text === initialData.transcribed_text) {
                    console.log('Restored saved progress from local storage')
                    setData(parsed)
                } else {
                    // Clear old data if it's a different song
                    localStorage.removeItem('lyrics_analyzer_data')
                }
            } catch (error) {
                console.error('Failed to parse saved data:', error)
                localStorage.removeItem('lyrics_analyzer_data')
            }
        }
    }, [initialData.transcribed_text])

    // Save to local storage whenever data changes
    useEffect(() => {
        if (!isReadOnly) {
            localStorage.setItem('lyrics_analyzer_data', JSON.stringify(data))
        }
    }, [data, isReadOnly])

    // Add keyboard event handlers
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ignore if user is typing in an input or textarea
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                return
            }

            if (e.key === 'Shift') {
                setIsShiftPressed(true)
                document.body.style.userSelect = 'none'
            } else if (e.key === 'Meta') {
                setIsCtrlPressed(true)
            } else if (e.key === ' ' || e.code === 'Space') {
                e.preventDefault() // Prevent page scroll
                if ((window as any).toggleAudioPlayback) {
                    (window as any).toggleAudioPlayback()
                }
            }
        }

        const handleKeyUp = (e: KeyboardEvent) => {
            if (e.key === 'Shift') {
                setIsShiftPressed(false)
                document.body.style.userSelect = ''
            } else if (e.key === 'Meta') {
                setIsCtrlPressed(false)
            }
        }

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
            let currentPosition = 0
            const segmentIndex = data.corrected_segments.findIndex(segment => {
                if (info.wordIndex >= currentPosition &&
                    info.wordIndex < currentPosition + segment.words.length) {
                    return true
                }
                currentPosition += segment.words.length
                return false
            })

            if (segmentIndex !== -1) {
                setEditModalSegment({
                    segment: data.corrected_segments[segmentIndex],
                    index: segmentIndex,
                    originalSegment: originalData.corrected_segments[segmentIndex]
                })
            }
        } else {
            // Existing word click handling for other modes...
            if (info.type === 'anchor' && info.anchor) {
                handleFlash('word', {
                    type: 'anchor',
                    transcriptionIndex: info.anchor.transcription_position,
                    transcriptionLength: info.anchor.length,
                    referenceIndices: info.anchor.reference_positions,
                    referenceLength: info.anchor.length
                })
            } else if (info.type === 'gap' && info.gap) {
                handleFlash('word', {
                    type: 'gap',
                    transcriptionIndex: info.gap.transcription_position,
                    transcriptionLength: info.gap.length,
                    referenceIndices: {},
                    referenceLength: info.gap.length
                })
            }
        }
    }, [effectiveMode, data.corrected_segments, handleFlash, originalData.corrected_segments])

    const handleUpdateSegment = useCallback((updatedSegment: LyricsSegment) => {
        console.log('LyricsAnalyzer - handleUpdateSegment called:', {
            editModalSegment,
            updatedSegment,
            currentSegmentsCount: data.corrected_segments.length
        })

        if (!editModalSegment) {
            console.warn('LyricsAnalyzer - No editModalSegment found')
            return
        }

        const newData = { ...data }
        console.log('LyricsAnalyzer - Before update:', {
            segmentIndex: editModalSegment.index,
            oldText: newData.corrected_segments[editModalSegment.index].text,
            newText: updatedSegment.text
        })

        newData.corrected_segments[editModalSegment.index] = updatedSegment

        // Update corrected_text
        newData.corrected_text = newData.corrected_segments
            .map(segment => segment.text)
            .join('\n')

        console.log('LyricsAnalyzer - After update:', {
            segmentsCount: newData.corrected_segments.length,
            updatedText: newData.corrected_text
        })

        setData(newData)
        setEditModalSegment(null)  // Close the modal
    }, [data, editModalSegment])

    const handleDeleteSegment = useCallback((segmentIndex: number) => {
        console.log('LyricsAnalyzer - handleDeleteSegment called:', {
            segmentIndex,
            currentSegmentsCount: data.corrected_segments.length
        })

        const newData = { ...data }
        newData.corrected_segments = newData.corrected_segments.filter((_, index) => index !== segmentIndex)

        // Update corrected_text
        newData.corrected_text = newData.corrected_segments
            .map(segment => segment.text)
            .join('\n')

        console.log('LyricsAnalyzer - After delete:', {
            segmentsCount: newData.corrected_segments.length,
            updatedText: newData.corrected_text
        })

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

    const handlePlaySegment = useCallback((startTime: number) => {
        // Access the globally exposed seekAndPlay method
        if ((window as any).seekAndPlayAudio) {
            (window as any).seekAndPlayAudio(startTime)
        }
    }, [])

    const handleResetCorrections = useCallback(() => {
        if (window.confirm('Are you sure you want to reset all corrections? This cannot be undone.')) {
            // Clear local storage
            localStorage.removeItem('lyrics_analyzer_data')
            // Reset data to initial state
            setData(JSON.parse(JSON.stringify(initialData)))
        }
    }, [initialData])

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
                    multiSourceAnchors={data.anchor_sequences.filter(anchor =>
                        Object.keys(anchor.reference_positions).length > 1).length}
                    anchorWordCount={data.anchor_sequences.reduce((sum, anchor) => sum + anchor.length, 0)}
                    // Gap metrics
                    correctedGapCount={data.gap_sequences.filter(gap =>
                        gap.corrections?.length > 0).length}
                    uncorrectedGapCount={data.gap_sequences.filter(gap =>
                        !gap.corrections?.length).length}
                    uncorrectedGaps={data.gap_sequences
                        .filter(gap => !gap.corrections?.length)
                        .map(gap => ({
                            position: gap.transcription_position,
                            length: gap.length
                        }))}
                    // Correction details
                    replacedCount={data.gap_sequences.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => !c.is_deletion && !c.split_total).length ?? 0), 0)}
                    addedCount={data.gap_sequences.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => c.split_total).length ?? 0), 0)}
                    deletedCount={data.gap_sequences.reduce((count, gap) =>
                        count + (gap.corrections?.filter(c => c.is_deletion).length ?? 0), 0)}
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