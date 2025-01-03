import { useState } from 'react'
import { Box, Grid, Paper, Typography } from '@mui/material'
import { LyricsData } from '../types'
import TranscriptionView from './TranscriptionView'
import ReferenceView from './ReferenceView'
import DetailsModal from './DetailsModal'

interface LyricsAnalyzerProps {
    data: LyricsData
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

export const COLORS = {
    anchor: '#e3f2fd', // Pale blue
    corrected: '#e8f5e9', // Pale green
    uncorrectedGap: '#fff3e0', // Pale orange
} as const

export default function LyricsAnalyzer({ data }: LyricsAnalyzerProps) {
    const [modalContent, setModalContent] = useState<ModalContent | null>(null)

    const handleCloseModal = () => {
        setModalContent(null)
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Lyrics Analysis
            </Typography>

            <Box sx={{ mb: 3 }}>
                <Grid container spacing={2}>
                    <Grid item xs={4}>
                        <Paper sx={{ p: 2 }}>
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
                                Matched sections between transcription and reference
                            </Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={4}>
                        <Paper sx={{ p: 2 }}>
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
                    <Grid item xs={4}>
                        <Paper sx={{ p: 2 }}>
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
                </Grid>
            </Box>

            <Grid container spacing={2}>
                <Grid item xs={6}>
                    <TranscriptionView
                        data={data}
                        onElementClick={setModalContent}
                    />
                </Grid>
                <Grid item xs={6}>
                    <ReferenceView
                        referenceTexts={data.reference_texts}
                        anchors={data.anchor_sequences}
                        onElementClick={setModalContent}
                    />
                </Grid>
            </Grid>

            <DetailsModal
                open={modalContent !== null}
                content={modalContent}
                onClose={handleCloseModal}
            />
        </Box>
    )
} 