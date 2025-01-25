import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Grid, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState } from 'react'
import { ApiClient } from '../api'
import { CorrectionData, LyricsData, HighlightInfo, AnchorMatchInfo } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import DetailsModal from './DetailsModal'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'
import DebugPanel from './DebugPanel'

interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: LyricsData['anchor_sequences'][0]
    gap?: LyricsData['gap_sequences'][0]
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

export default function LyricsAnalyzer({ data, onFileLoad, apiClient, isReadOnly }: LyricsAnalyzerProps) {
    const [modalContent, setModalContent] = useState<ModalContent | null>(null)
    const [flashingType, setFlashingType] = useState<FlashType>(null)
    const [highlightInfo, setHighlightInfo] = useState<HighlightInfo | null>(null)
    const [currentSource, setCurrentSource] = useState<'genius' | 'spotify'>('genius')
    const [anchorMatchInfo, setAnchorMatchInfo] = useState<AnchorMatchInfo[]>([])
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

        // Log the clicked word info
        console.log(`Clicked word index: ${info.wordIndex}`)
        console.log(`Word type: ${info.type}`)

        if (info.type === 'anchor' && info.anchor) {
            // Log detailed anchor info
            console.log(`Anchor text: "${info.anchor.text}"`)
            console.log(`Anchor position in transcription: ${info.anchor.transcription_position}`)
            console.log(`Anchor length: ${info.anchor.length}`)
            console.log('Reference positions:', {
                genius: info.anchor.reference_positions.genius,
                spotify: info.anchor.reference_positions.spotify
            })

            // Log what we're sending to handleFlash
            const highlightInfo = {
                type: 'anchor' as const,
                transcriptionIndex: info.anchor.transcription_position,
                transcriptionLength: info.anchor.length,
                referenceIndices: info.anchor.reference_positions,
                referenceLength: info.anchor.length
            }
            console.log('Sending highlight info:', {
                type: highlightInfo.type,
                transIndex: highlightInfo.transcriptionIndex,
                transLength: highlightInfo.transcriptionLength,
                refIndices: {
                    genius: highlightInfo.referenceIndices.genius,
                    spotify: highlightInfo.referenceIndices.spotify
                },
                refLength: highlightInfo.referenceLength
            })

            handleFlash('word', highlightInfo)
        } else if (info.type === 'gap' && info.gap) {
            // Show modal for gaps on single click
            setModalContent({
                type: 'gap',
                data: {
                    ...info.gap,
                    position: info.wordIndex,
                    word: info.gap.text
                }
            })
        } else {
            console.log('Word is not part of an anchor sequence or gap')
        }
        console.groupEnd()
    }, [handleFlash, setModalContent])

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
                    multiSourceAnchors={data.anchor_sequences.filter(a =>
                        Object.keys(a.reference_positions).length > 1).length}
                    singleSourceMatches={{
                        spotify: data.anchor_sequences.filter(a =>
                            Object.keys(a.reference_positions).length === 1 && 'spotify' in a.reference_positions).length,
                        genius: data.anchor_sequences.filter(a =>
                            Object.keys(a.reference_positions).length === 1 && 'genius' in a.reference_positions).length
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
                        highlightInfo={highlightInfo}
                        currentSource={currentSource}
                        onSourceChange={setCurrentSource}
                        onDebugInfoUpdate={setAnchorMatchInfo}
                    />
                </Grid>
            </Grid>

            {modalContent && (
                <DetailsModal
                    content={modalContent}
                    onClose={() => setModalContent(null)}
                    open={Boolean(modalContent)}
                />
            )}

            {!isReadOnly && apiClient && (
                <Box sx={{ mt: 2 }}>
                    {/* Edit interface coming soon */}
                </Box>
            )}
        </Box>
    )
} 