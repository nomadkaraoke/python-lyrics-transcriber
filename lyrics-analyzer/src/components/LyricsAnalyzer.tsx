import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Grid, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState } from 'react'
import { ApiClient } from '../api'
import { CorrectionData, LyricsData, HighlightInfo, AnchorMatchInfo, GapSequence, AnchorSequence, LyricsSegment, WordCorrection } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import DetailsModal from './DetailsModal'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import DebugPanel from './DebugPanel'

interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: AnchorSequence
    gap?: GapSequence
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
    data: LyricsData['anchor_sequences'][0] & {
        position: number
    }
} | {
    type: 'gap'
    data: LyricsData['gap_sequences'][0] & {
        position: number
        word: string
    }
}

export type FlashType = 'anchor' | 'corrected' | 'uncorrected' | 'word' | null

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
    const [anchorMatchInfo, setAnchorMatchInfo] = useState<AnchorMatchInfo[]>([])
    const [manualCorrections, setManualCorrections] = useState<Map<number, string[]>>(new Map())
    const [isReviewComplete, setIsReviewComplete] = useState(false)
    const [data, setData] = useState(initialData)
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
        console.group('Word Click Debug Info')
        console.log('Clicked word info:', JSON.stringify(info, null, 2))

        if (info.type === 'gap' && info.gap) {
            console.log('Gap sequence:', JSON.stringify(info.gap, null, 2))
            const modalData = {
                type: 'gap' as const,
                data: {
                    ...info.gap,
                    position: info.gap.transcription_position,
                    word: info.gap.words[info.wordIndex - info.gap.transcription_position]
                }
            }
            setModalContent(modalData)
            console.log('Set modal content:', JSON.stringify(modalData, null, 2))
        }

        console.groupEnd()
    }, [])

    const handleUpdateCorrection = useCallback((position: number, updatedWords: string[]) => {
        console.group('handleUpdateCorrection Debug')
        console.log('Position:', position)
        console.log('Updated words:', updatedWords)

        // Update manual corrections
        setManualCorrections(prev => {
            const newCorrections = new Map(prev)
            newCorrections.set(position, updatedWords)
            return newCorrections
        })

        // Create a deep clone of the data
        const newData = JSON.parse(JSON.stringify(data))

        // Find and update the gap sequence
        const gapIndex = newData.gap_sequences.findIndex(
            (gap: GapSequence) => gap.transcription_position === position
        )

        if (gapIndex !== -1) {
            const originalGap = newData.gap_sequences[gapIndex]
            console.log('Found gap at index:', gapIndex)
            console.log('Original gap:', {
                text: originalGap.text,
                words: originalGap.words,
                transcription_position: originalGap.transcription_position
            })

            // Create a new correction
            const newCorrection: WordCorrection = {
                original_word: originalGap.text,
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

            // Find the corresponding segment first to get timing information
            const segmentIndex = newData.corrected_segments.findIndex((segment: LyricsSegment) => {
                // Calculate total words before this segment
                let totalWords = 0
                for (let i = 0; i < newData.corrected_segments.indexOf(segment); i++) {
                    totalWords += newData.corrected_segments[i].words.length
                }

                // Check if this segment contains our target position
                const segmentLength = segment.words.length
                return totalWords <= originalGap.transcription_position &&
                    (totalWords + segmentLength) > originalGap.transcription_position
            })

            if (segmentIndex !== -1) {
                const segment = newData.corrected_segments[segmentIndex]
                console.log('Found matching segment:', {
                    text: segment.text,
                    totalWords: newData.corrected_segments
                        .slice(0, segmentIndex)
                        .reduce((sum: number, seg: LyricsSegment) => sum + seg.words.length, 0)
                })

                // Calculate the word index within the segment
                let wordsBefore = 0
                for (let i = 0; i < segmentIndex; i++) {
                    wordsBefore += newData.corrected_segments[i].words.length
                }
                const wordIndex = originalGap.transcription_position - wordsBefore
                const timingWord = segment.words[wordIndex]

                console.log('Found word in segment:', {
                    index: wordIndex,
                    word: timingWord.text,
                    timing: {
                        start: timingWord.start_time,
                        end: timingWord.end_time
                    }
                })

                // Update gap sequence with timing from segment
                newData.gap_sequences[gapIndex] = {
                    ...originalGap,
                    words: updatedWords.map(word => ({
                        text: word,
                        start_time: timingWord.start_time,
                        end_time: timingWord.end_time
                    })),
                    text: updatedWords.join(' '),
                    corrections: originalGap.corrections
                        .filter((c: WordCorrection) => c.source !== 'manual')
                        .concat([newCorrection])
                }

                // Now update the segment
                const newWords = [...segment.words]
                newWords[wordIndex] = {
                    ...timingWord,
                    text: updatedWords[0],
                    confidence: 1.0
                }

                newData.corrected_segments[segmentIndex] = {
                    ...segment,
                    words: newWords,
                    text: newWords.map(word => word.text).join(' ')
                }

                console.log('Updated both gap and segment')
            } else {
                console.log('No matching segment found')
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

            <DebugPanel
                data={data}
                currentSource={currentSource}
                anchorMatchInfo={anchorMatchInfo}
            />

            <Grid container spacing={2} direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <TranscriptionView
                        data={data}
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
                        onElementClick={setModalContent}
                        onWordClick={handleWordClick}
                        flashingType={flashingType}
                        corrected_segments={data.corrected_segments}
                        currentSource={currentSource}
                        onSourceChange={setCurrentSource}
                        onDebugInfoUpdate={setAnchorMatchInfo}
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
                <Box sx={{ mt: 2 }}>
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