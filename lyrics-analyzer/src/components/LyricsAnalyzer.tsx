import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, Button, Grid, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useCallback, useState } from 'react'
import { ApiClient } from '../api'
import { CorrectionData, LyricsData } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import DetailsModal from './DetailsModal'
import ReferenceView from './ReferenceView'
import TranscriptionView from './TranscriptionView'

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

export type FlashType = 'anchor' | 'corrected' | 'uncorrected' | null

export default function LyricsAnalyzer({ data, onFileLoad, apiClient, isReadOnly }: LyricsAnalyzerProps) {
    const [modalContent, setModalContent] = useState<ModalContent | null>(null)
    const [flashingType, setFlashingType] = useState<FlashType>(null)
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

    const handleFlash = useCallback((type: FlashType) => {
        // Clear any existing flash animation
        setFlashingType(null)

        // Force a new render cycle before starting the animation
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                setFlashingType(type)
                // Reset after animation completes
                setTimeout(() => {
                    setFlashingType(null)
                }, 1200) // Adjusted to match new animation duration (0.4s × 3)
            })
        })
    }, [])

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

            <Grid container spacing={2} direction={isMobile ? 'column' : 'row'}>
                <Grid item xs={12} md={6}>
                    <TranscriptionView
                        data={data}
                        onElementClick={setModalContent}
                        flashingType={flashingType}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <ReferenceView
                        referenceTexts={data.reference_texts}
                        anchors={data.anchor_sequences}
                        gaps={data.gap_sequences}
                        onElementClick={setModalContent}
                        flashingType={flashingType}
                        corrected_segments={data.corrected_segments}
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