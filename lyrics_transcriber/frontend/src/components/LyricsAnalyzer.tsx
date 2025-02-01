import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Grid, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState } from 'react'
import { ApiClient } from '../api'
import { CorrectionData, GapSequence, HighlightInfo, InteractionMode, LyricsData, LyricsSegment, WordCorrection } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import DetailsModal from './DetailsModal'
import ModeSelector from './ModeSelector'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import { WordClickInfo, FlashType } from './shared/types'

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
    const [currentSource, setCurrentSource] = useState<'genius' | 'spotify'>('genius')
    const [manualCorrections, setManualCorrections] = useState<Map<number, string[]>>(new Map())
    const [isReviewComplete, setIsReviewComplete] = useState(false)
    const [data, setData] = useState(initialData)
    const [interactionMode, setInteractionMode] = useState<InteractionMode>('details')
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

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
        // For any word click, flash the containing sequence
        if (info.type === 'anchor' && info.anchor) {
            // Change flash type from 'word' to 'anchor' to ensure both views highlight
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
    }, [handleFlash])

    const handleUpdateCorrection = useCallback((position: number, updatedWords: string[]) => {
        console.group('handleUpdateCorrection Debug')
        console.log('Position:', position)
        console.log('Updated words:', updatedWords)

        // Create a deep clone of the data
        const newData = JSON.parse(JSON.stringify(data))

        // Find the gap that contains this position
        const gapIndex = newData.gap_sequences.findIndex(
            (gap: GapSequence) =>
                position >= gap.transcription_position &&
                position < gap.transcription_position + gap.words.length
        )

        if (gapIndex !== -1) {
            const originalGap = newData.gap_sequences[gapIndex]
            const wordIndexInGap = position - originalGap.transcription_position
            console.log('Found gap at index:', gapIndex, 'word index in gap:', wordIndexInGap)

            // Update manual corrections
            setManualCorrections(prev => {
                const newCorrections = new Map(prev)
                newCorrections.set(position, updatedWords)
                return newCorrections
            })

            // Create a new correction
            const newCorrection: WordCorrection = {
                original_word: originalGap.words[wordIndexInGap],
                corrected_word: updatedWords.join(' '),
                segment_index: 0,
                original_position: position,
                source: 'manual',
                confidence: 1.0,
                reason: 'Manual correction during review',
                alternatives: {},
                is_deletion: false,
                length: updatedWords.length,
                reference_positions: {}
            }

            // Find the corresponding segment by counting words
            let currentPosition = 0
            let segmentIndex = -1
            let wordIndex = -1

            for (let i = 0; i < newData.corrected_segments.length; i++) {
                const segment = newData.corrected_segments[i]
                if (position >= currentPosition && position < currentPosition + segment.words.length) {
                    segmentIndex = i
                    wordIndex = position - currentPosition
                    break
                }
                currentPosition += segment.words.length
            }

            console.log('Segment search:', {
                position,
                segmentIndex,
                wordIndex,
                totalSegments: newData.corrected_segments.length
            })

            if (segmentIndex !== -1 && wordIndex !== -1) {
                const segment = newData.corrected_segments[segmentIndex]
                const timingWord = segment.words[wordIndex]

                console.log('Found matching segment:', {
                    text: segment.text,
                    wordCount: segment.words.length,
                    wordIndex,
                    word: timingWord?.text
                })

                if (!timingWord) {
                    console.error('Could not find timing word in segment')
                    console.groupEnd()
                    return
                }

                // Update gap sequence
                const newWords = [...originalGap.words]
                newWords[wordIndexInGap] = updatedWords[0]
                newData.gap_sequences[gapIndex] = {
                    ...originalGap,
                    words: newWords,
                    text: newWords.join(' '),
                    corrections: originalGap.corrections
                        .filter((c: WordCorrection) => c.source !== 'manual')
                        .concat([newCorrection])
                }

                // Update segment
                const newSegmentWords = [...segment.words]
                newSegmentWords[wordIndex] = {
                    ...timingWord,
                    text: updatedWords[0],
                    confidence: 1.0
                }

                newData.corrected_segments[segmentIndex] = {
                    ...segment,
                    words: newSegmentWords,
                    text: newSegmentWords.map(word => word.text).join(' ')
                }

                console.log('Updated both gap and segment')
            } else {
                console.error('Could not find matching segment for position:', position)
            }
        }

        // Update the corrected_text field
        newData.corrected_text = newData.corrected_segments
            .map((segment: LyricsSegment) => segment.text)
            .join('\n')

        setData(newData)
        console.groupEnd()
    }, [data])

    const handleFinishReview = useCallback(async () => {
        if (!apiClient) return

        let dataToSubmit: CorrectionData
        if (manualCorrections.size > 0) {
            console.log('Manual corrections found:', Array.from(manualCorrections.entries()))

            // Only proceed with data modifications if there were manual corrections
            const updatedData = JSON.parse(JSON.stringify(data))
            console.log('Deep cloned data:', JSON.stringify(updatedData, null, 2))

            // Only update the specific gaps that were manually corrected
            updatedData.gap_sequences = updatedData.gap_sequences.map((gap: GapSequence) => {
                const manualUpdate = manualCorrections.get(gap.transcription_position)
                if (manualUpdate) {
                    return {
                        ...gap,
                        words: manualUpdate,
                        text: manualUpdate.join(' '),
                        corrections: [
                            ...gap.corrections,
                            {
                                original_word: gap.text,
                                corrected_word: manualUpdate.join(' '),
                                segment_index: 0,
                                original_position: gap.transcription_position,
                                source: 'manual',
                                confidence: 1.0,
                                reason: 'Manual correction during review',
                                alternatives: {},
                                is_deletion: false,
                                length: manualUpdate.length,
                                reference_positions: {}
                            }
                        ]
                    }
                }
                return gap
            })

            // Preserve original newline formatting in corrected_text
            if (manualCorrections.size > 0) {
                const lines: string[] = updatedData.corrected_text.split('\n')
                let currentPosition = 0
                const updatedLines = lines.map((line: string) => {
                    const words = line.trim().split(/\s+/)
                    const lineLength = words.length

                    // Check if this line contains any corrections
                    let lineUpdated = false
                    for (const [position, updatedWords] of manualCorrections.entries()) {
                        if (position >= currentPosition && position < currentPosition + lineLength) {
                            const gapPosition = position - currentPosition
                            const gap = updatedData.gap_sequences.find((g: GapSequence) =>
                                g.transcription_position === position
                            )
                            if (gap) {
                                words.splice(gapPosition, gap.length, ...updatedWords)
                                lineUpdated = true
                            }
                        }
                    }
                    currentPosition += lineLength
                    return lineUpdated ? words.join(' ') : line
                })
                updatedData.corrected_text = updatedLines.join('\n')
            }

            dataToSubmit = normalizeDataForSubmission(updatedData)
            console.log('Submitting data with manual corrections:', dataToSubmit)
        } else {
            console.log('Original data:', initialData)
            console.log('No manual corrections, submitting original data')
            dataToSubmit = normalizeDataForSubmission(initialData)
        }

        console.log('Data being sent to API:', dataToSubmit)
        await apiClient.submitCorrections(dataToSubmit)
        setIsReviewComplete(true)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [apiClient, initialData, manualCorrections])

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
                    singleSourceMatches={{
                        spotify: data.anchor_sequences.filter(anchor =>
                            Object.keys(anchor.reference_positions).length === 1 &&
                            'spotify' in anchor.reference_positions).length,
                        genius: data.anchor_sequences.filter(anchor =>
                            Object.keys(anchor.reference_positions).length === 1 &&
                            'genius' in anchor.reference_positions).length
                    }}
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
                />
            </Box>

            <Box sx={{ mb: 3 }}>
                <ModeSelector
                    mode={interactionMode}
                    onChange={setInteractionMode}
                />
            </Box>

            <Grid container spacing={2} direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <TranscriptionView
                        data={data}
                        mode={interactionMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        highlightInfo={highlightInfo}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <ReferenceView
                        referenceTexts={data.reference_texts}
                        anchors={data.anchor_sequences}
                        gaps={data.gap_sequences}
                        mode={interactionMode}
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        highlightInfo={highlightInfo}
                        corrected_segments={data.corrected_segments}
                        currentSource={currentSource}
                        onSourceChange={setCurrentSource}
                    />
                </Grid>
            </Grid>

            <DetailsModal
                open={modalContent !== null}
                content={modalContent}
                onClose={() => setModalContent(null)}
                onUpdateCorrection={handleUpdateCorrection}
                isReadOnly={isReadOnly}
            />

            {!isReadOnly && apiClient && (
                <Box sx={{ mt: 2, mb: 3 }}>
                    <Button
                        variant="contained"
                        onClick={handleFinishReview}
                        disabled={isReviewComplete}
                    >
                        {isReviewComplete ? 'Review Complete' : 'Finish Review'}
                    </Button>
                </Box>
            )}
        </Box>
    )
} 