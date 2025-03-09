import { Paper, Box, Typography } from '@mui/material'
import { COLORS } from './shared/constants'

interface MetricProps {
    color?: string
    label: string
    value: string | number
    description: string
    details?: Array<{ label: string, value: string | number }>
    onClick?: () => void
}

function Metric({ color, label, value, description, details, onClick }: MetricProps) {
    return (
        <Paper
            sx={{
                p: 0.8,
                pt: 0,
                height: '100%',
                cursor: onClick ? 'pointer' : 'default',
                '&:hover': onClick ? {
                    bgcolor: 'action.hover'
                } : undefined,
                display: 'flex',
                flexDirection: 'column'
            }}
            onClick={onClick}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, mt: 0.8 }}>
                {color && (
                    <Box
                        sx={{
                            width: 12,
                            height: 12,
                            borderRadius: 1,
                            bgcolor: color,
                            mr: 0.5,
                        }}
                    />
                )}
                <Typography variant="subtitle2" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    {label}
                </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, mb: 0.3 }}>
                <Typography variant="h6" sx={{ fontSize: '1.1rem' }}>
                    {value}
                </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                {description}
            </Typography>
            {details && (
                <Box sx={{ mt: 0.5, flex: 1, overflow: 'auto' }}>
                    {details.map((detail, index) => (
                        <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.3 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                                {detail.label}
                            </Typography>
                            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                                {detail.value}
                            </Typography>
                        </Box>
                    ))}
                </Box>
            )}
        </Paper>
    )
}

interface CorrectionMetricsProps {
    // Anchor metrics
    anchorCount?: number
    multiSourceAnchors?: number
    anchorWordCount?: number
    // Gap metrics
    correctedGapCount?: number
    uncorrectedGapCount?: number
    uncorrectedGaps?: Array<{
        position: string
        length: number
    }>
    // Correction details
    replacedCount?: number
    addedCount?: number
    deletedCount?: number
    // Add total words count
    totalWords?: number
    onMetricClick?: {
        anchor?: () => void
        corrected?: () => void
        uncorrected?: () => void
    }
}

export default function CorrectionMetrics({
    anchorCount,
    multiSourceAnchors = 0,
    anchorWordCount = 0,
    correctedGapCount = 0,
    uncorrectedGapCount = 0,
    uncorrectedGaps = [],
    replacedCount = 0,
    addedCount = 0,
    deletedCount = 0,
    totalWords = 0,
    onMetricClick
}: CorrectionMetricsProps) {
    // Calculate percentages based on word counts
    const anchorPercentage = totalWords > 0 ? Math.round((anchorWordCount / totalWords) * 100) : 0
    const uncorrectedWordCount = uncorrectedGaps?.reduce((sum, gap) => sum + gap.length, 0) ?? 0
    const uncorrectedPercentage = totalWords > 0 ? Math.round((uncorrectedWordCount / totalWords) * 100) : 0
    const correctedWordCount = replacedCount + addedCount
    const correctedPercentage = totalWords > 0 ?
        Math.round((correctedWordCount / totalWords) * 100) : 0

    return (
        <Box sx={{ height: '100%', display: 'flex' }}>
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'row', gap: 1, height: '100%' }}>
                <Box sx={{ flex: 1, height: '100%' }}>
                    <Metric
                        color={COLORS.anchor}
                        label="Anchor Sequences"
                        value={`${anchorCount ?? '-'} (${anchorPercentage}%)`}
                        description="Matched sections between transcription and reference"
                        details={[
                            { label: 'Words in Anchors', value: anchorWordCount },
                            { label: 'Multi-source Matches', value: multiSourceAnchors }
                        ]}
                        onClick={onMetricClick?.anchor}
                    />
                </Box>
                <Box sx={{ flex: 1, height: '100%' }}>
                    <Metric
                        color={COLORS.corrected}
                        label="Corrected Gaps"
                        value={`${correctedGapCount} (${correctedPercentage}%)`}
                        description="Successfully corrected sections"
                        details={[
                            { label: 'Words Replaced', value: replacedCount },
                            { label: 'Words Added / Deleted', value: `+${addedCount} / -${deletedCount}` }
                        ]}
                        onClick={onMetricClick?.corrected}
                    />
                </Box>
                <Box sx={{ flex: 1, height: '100%' }}>
                    <Metric
                        color={COLORS.uncorrectedGap}
                        label="Uncorrected Gaps"
                        value={`${uncorrectedGapCount} (${uncorrectedPercentage}%)`}
                        description="Sections that may need manual review"
                        details={[
                            { label: 'Words Uncorrected', value: uncorrectedWordCount },
                            { label: 'Number of Gaps', value: uncorrectedGaps.length }
                        ]}
                        onClick={onMetricClick?.uncorrected}
                    />
                </Box>
            </Box>
        </Box>
    )
} 