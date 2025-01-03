import { useState, useCallback } from 'react'
import { Box, Grid, Paper, Typography, Button, useTheme, useMediaQuery } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { LyricsData } from '../types'
import TranscriptionView from './TranscriptionView'
import ReferenceView from './ReferenceView'
import DetailsModal from './DetailsModal'
import { COLORS } from './constants'

interface LyricsAnalyzerProps {
    data: LyricsData
    onFileLoad: () => void
    onShowMetadata: () => void
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

export default function LyricsAnalyzer({ data, onFileLoad, onShowMetadata }: LyricsAnalyzerProps) {
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

    const handleCloseModal = () => {
        setModalContent(null)
    }

    return (
        <Box>
            <Box sx={{ 
                display: 'flex', 
                flexDirection: isMobile ? 'column' : 'row',
                gap: 2,
                justifyContent: 'space-between', 
                alignItems: isMobile ? 'stretch' : 'center',
                mb: 3 
            }}>
                <Typography variant="h4" sx={{ fontSize: isMobile ? '1.75rem' : '2.125rem' }}>
                    Lyrics Analysis
                </Typography>
                <Button
                    variant="outlined"
                    startIcon={<UploadFileIcon />}
                    onClick={onFileLoad}
                    fullWidth={isMobile}
                >
                    Load File
                </Button>
            </Box>

            <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                '&:hover': {
                                    bgcolor: 'action.hover'
                                }
                            }}
                            onClick={() => handleFlash('anchor')}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Box
                                    sx={{
                                        width: 16,
                                        height: 16,
                                        borderRadius: 1,
                                        bgcolor: COLORS.anchor,
                                        mr: 1,
                                    }}
                                />
                                <Typography variant="subtitle2" color="text.secondary">
                                    Anchor Sequences
                                </Typography>
                            </Box>
                            <Typography variant="h6">
                                {data.metadata.anchor_sequences_count}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Click to highlight matched sections
                            </Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                '&:hover': {
                                    bgcolor: 'action.hover'
                                }
                            }}
                            onClick={() => handleFlash('corrected')}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Box
                                    sx={{
                                        width: 16,
                                        height: 16,
                                        borderRadius: 1,
                                        bgcolor: COLORS.corrected,
                                        mr: 1,
                                    }}
                                />
                                <Typography variant="subtitle2" color="text.secondary">
                                    Corrections Made
                                </Typography>
                            </Box>
                            <Typography variant="h6">
                                {data.corrections_made}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Successfully fixed transcription errors
                            </Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                '&:hover': {
                                    bgcolor: 'action.hover'
                                }
                            }}
                            onClick={() => handleFlash('uncorrected')}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Box
                                    sx={{
                                        width: 16,
                                        height: 16,
                                        borderRadius: 1,
                                        bgcolor: COLORS.uncorrectedGap,
                                        mr: 1,
                                    }}
                                />
                                <Typography variant="subtitle2" color="text.secondary">
                                    Uncorrected Gaps
                                </Typography>
                            </Box>
                            <Typography variant="h6">
                                {data.metadata.gap_sequences_count - data.corrections_made}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Sections that may need manual review
                            </Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Paper
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                '&:hover': {
                                    bgcolor: 'action.hover'
                                }
                            }}
                            onClick={onShowMetadata}
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Typography variant="subtitle2" color="text.secondary">
                                    Confidence Score
                                </Typography>
                            </Box>
                            <Typography variant="h6">
                                {(data.confidence * 100).toFixed(1)}%
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Click for correction metadata
                            </Typography>
                        </Paper>
                    </Grid>
                </Grid>
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
                    />
                </Grid>
            </Grid>

            {modalContent && (
                <DetailsModal
                    content={modalContent}
                    onClose={() => setModalContent(null)}
                />
            )}
        </Box>
    )
} 