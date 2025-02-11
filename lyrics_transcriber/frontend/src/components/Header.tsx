import { Box, Button, Typography, useMediaQuery, useTheme } from '@mui/material'
import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { CorrectionData } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import ModeSelector from './ModeSelector'
import AudioPlayer from './AudioPlayer'
import { InteractionMode } from '../types'
import { ApiClient } from '../api'

interface HeaderProps {
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
}

export default function Header({
    isReadOnly,
    onFileLoad,
    data,
    onMetricClick,
    effectiveMode,
    onModeChange,
    apiClient,
    audioHash,
    onTimeUpdate
}: HeaderProps) {
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

    // Get handlers with their correction counts
    const handlerCounts = data.gap_sequences?.reduce((counts: Record<string, number>, gap) => {
        gap.corrections?.forEach(correction => {
            counts[correction.handler] = (counts[correction.handler] || 0) + 1
        })
        return counts
    }, {}) || {}

    // Sort handlers by name
    const correctionHandlers = Object.keys(handlerCounts).sort()

    return (
        <>
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

            <Box sx={{
                display: 'flex',
                gap: 2,
                mb: 3,
                flexDirection: isMobile ? 'column' : 'row'
            }}>
                <Box sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 0.5,
                    minWidth: '150px'
                }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                        Correction Handlers
                    </Typography>
                    {correctionHandlers.map(handler => (
                        <Button
                            key={handler}
                            variant="outlined"
                            size="small"
                            sx={{
                                textTransform: 'none',
                                opacity: 0.8,
                                py: 0.25,
                                px: 1,
                                justifyContent: 'flex-start',
                                minHeight: '24px'
                            }}
                        >
                            {handler} ({handlerCounts[handler]})
                        </Button>
                    ))}
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                    <CorrectionMetrics
                        // Anchor metrics
                        anchorCount={data.metadata.anchor_sequences_count}
                        multiSourceAnchors={data.anchor_sequences?.filter(anchor =>
                            anchor?.reference_words &&
                            Object.keys(anchor.reference_words).length > 1
                        ).length ?? 0}
                        anchorWordCount={data.anchor_sequences?.reduce((sum, anchor) =>
                            sum + (anchor.transcribed_words?.length || 0), 0) ?? 0}
                        // Gap metrics
                        correctedGapCount={data.gap_sequences?.filter(gap =>
                            gap.corrections?.length > 0).length ?? 0}
                        uncorrectedGapCount={data.gap_sequences?.filter(gap =>
                            !gap.corrections?.length).length ?? 0}
                        uncorrectedGaps={data.gap_sequences
                            ?.filter(gap => !gap.corrections?.length && gap.transcribed_words?.length > 0)
                            .map(gap => ({
                                position: gap.transcribed_words[0]?.id ?? '',
                                length: gap.transcribed_words.length ?? 0
                            })) ?? []}
                        // Correction details
                        replacedCount={data.gap_sequences?.reduce((count, gap) =>
                            count + (gap.corrections?.filter(c => !c.is_deletion && !c.split_total).length ?? 0), 0) ?? 0}
                        addedCount={data.gap_sequences?.reduce((count, gap) =>
                            count + (gap.corrections?.filter(c => c.split_total).length ?? 0), 0) ?? 0}
                        deletedCount={data.gap_sequences?.reduce((count, gap) =>
                            count + (gap.corrections?.filter(c => c.is_deletion).length ?? 0), 0) ?? 0}
                        onMetricClick={onMetricClick}
                        totalWords={data.metadata.total_words}
                    />
                </Box>
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
                    onChange={onModeChange}
                />
                <AudioPlayer
                    apiClient={apiClient}
                    onTimeUpdate={onTimeUpdate}
                    audioHash={audioHash}
                />
            </Box>
        </>
    )
} 