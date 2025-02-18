import { Box, Button, Typography, useMediaQuery, useTheme, Switch, FormControlLabel, Tooltip, CircularProgress } from '@mui/material'
import LockIcon from '@mui/icons-material/Lock'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { CorrectionData } from '../types'
import CorrectionMetrics from './CorrectionMetrics'
import ModeSelector from './ModeSelector'
import AudioPlayer from './AudioPlayer'
import { InteractionMode } from '../types'
import { ApiClient } from '../api'
import { findWordById } from './shared/utils/wordUtils'

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
    onHandlerToggle: (handler: string, enabled: boolean) => void
    isUpdatingHandlers: boolean
    onHandlerClick?: (handler: string) => void
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
    onTimeUpdate,
    onHandlerToggle,
    isUpdatingHandlers,
    onHandlerClick
}: HeaderProps) {
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))

    // Get handlers with their correction counts
    const handlerCounts = data.corrections?.reduce((counts: Record<string, number>, correction) => {
        counts[correction.handler] = (counts[correction.handler] || 0) + 1
        return counts
    }, {}) || {}

    // Get available handlers from metadata
    const availableHandlers = data.metadata.available_handlers || []
    const enabledHandlers = new Set(data.metadata.enabled_handlers || [])

    // Create a map of gap IDs to their corrections
    const gapCorrections = data.corrections.reduce((map: Record<string, number>, correction) => {
        // Find the gap that contains this correction's word_id
        const gap = data.gap_sequences.find(g =>
            g.transcribed_word_ids.includes(correction.word_id)
        )
        if (gap) {
            map[gap.id] = (map[gap.id] || 0) + 1
        }
        return map
    }, {})

    // Calculate metrics
    const correctedGapCount = Object.keys(gapCorrections).length
    const uncorrectedGapCount = data.gap_sequences.length - correctedGapCount

    const uncorrectedGaps = data.gap_sequences
        .filter(gap => !gapCorrections[gap.id] && gap.transcribed_word_ids.length > 0)
        .map(gap => {
            const firstWord = findWordById(data.corrected_segments, gap.transcribed_word_ids[0])
            return {
                position: firstWord?.id ?? '',
                length: gap.transcribed_word_ids.length
            }
        })

    // Calculate correction type counts
    const replacedCount = data.corrections.filter(c => !c.is_deletion && !c.split_total).length
    const addedCount = data.corrections.filter(c => c.split_total).length
    const deletedCount = data.corrections.filter(c => c.is_deletion).length

    console.log('Header: Render with isUpdatingHandlers =', isUpdatingHandlers)

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
                    gap: 1,
                    minWidth: '250px',
                    position: 'relative'
                }}>
                    <Typography variant="subtitle2" color="text.secondary">
                        Correction Handlers
                    </Typography>

                    {availableHandlers.map(handler => (
                        <Tooltip
                            key={handler.id}
                            title={handler.description}
                            placement="right"
                        >
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={enabledHandlers.has(handler.id)}
                                        onChange={(e) => onHandlerToggle(handler.id, e.target.checked)}
                                        size="small"
                                        disabled={isUpdatingHandlers}
                                    />
                                }
                                label={`${handler.name} (${handlerCounts[handler.id] || 0})`}
                                onClick={(e) => {
                                    if ((e.target as HTMLElement).tagName !== 'INPUT') {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        onHandlerClick?.(handler.id);
                                    }
                                }}
                                sx={{
                                    ml: 0,
                                    '& .MuiFormControlLabel-label': {
                                        fontSize: '0.875rem',
                                        cursor: 'pointer'
                                    }
                                }}
                            />
                        </Tooltip>
                    ))}

                    {isUpdatingHandlers && (
                        <Box sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            backgroundColor: 'rgba(255, 255, 255, 0.7)',
                            borderRadius: 1,
                            zIndex: 1
                        }}>
                            <Box sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 2,
                                padding: 2,
                                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                borderRadius: 1,
                                boxShadow: 1
                            }}>
                                <CircularProgress size={24} />
                                <Typography variant="body2" color="text.secondary">
                                    Updating corrections...
                                </Typography>
                            </Box>
                        </Box>
                    )}
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                    <CorrectionMetrics
                        // Anchor metrics
                        anchorCount={data.metadata.anchor_sequences_count}
                        multiSourceAnchors={data.anchor_sequences?.filter(anchor =>
                            anchor?.reference_word_ids &&
                            Object.keys(anchor.reference_word_ids).length > 1
                        ).length ?? 0}
                        anchorWordCount={data.anchor_sequences?.reduce((sum, anchor) =>
                            sum + (anchor.transcribed_word_ids?.length || 0), 0) ?? 0}
                        // Updated gap metrics
                        correctedGapCount={correctedGapCount}
                        uncorrectedGapCount={uncorrectedGapCount}
                        uncorrectedGaps={uncorrectedGaps}
                        // Updated correction type counts
                        replacedCount={replacedCount}
                        addedCount={addedCount}
                        deletedCount={deletedCount}
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