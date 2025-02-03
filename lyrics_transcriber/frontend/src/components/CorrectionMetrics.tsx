import { Grid, Paper, Box, Typography } from '@mui/material'
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
                p: 2,
                cursor: onClick ? 'pointer' : 'default',
                '&:hover': onClick ? {
                    bgcolor: 'action.hover'
                } : undefined
            }}
            onClick={onClick}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {color && (
                    <Box
                        sx={{
                            width: 16,
                            height: 16,
                            borderRadius: 1,
                            bgcolor: color,
                            mr: 1,
                        }}
                    />
                )}
                <Typography variant="subtitle2" color="text.secondary">
                    {label}
                </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 0.5 }}>
                <Typography variant="h6">
                    {value}
                </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
                {description}
            </Typography>
            {details && (
                <Box sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
                    {details.map((detail, index) => (
                        <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                                {detail.label}
                            </Typography>
                            <Typography variant="caption">
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
        position: number
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
    // For corrected percentage, we'll use the total affected words
    const correctedWordCount = replacedCount + addedCount
    const correctedPercentage = totalWords > 0 ?
        Math.round((correctedWordCount / totalWords) * 100) : 0

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.anchor}
                    label="Anchor Sequences"
                    value={`${anchorCount ?? '-'} (${anchorPercentage}%)`}
                    description="Matched sections between transcription and reference"
                    details={[
                        { label: "Words in Anchors", value: anchorWordCount },
                        { label: "Multi-source Matches", value: multiSourceAnchors },
                    ]}
                    onClick={onMetricClick?.anchor}
                />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.corrected}
                    label="Corrected Gaps"
                    value={`${correctedGapCount} (${correctedPercentage}%)`}
                    description="Successfully corrected sections"
                    details={[
                        { label: "Words Replaced", value: replacedCount },
                        { label: "Words Added / Deleted", value: `+${addedCount} / -${deletedCount}` },
                    ]}
                    onClick={onMetricClick?.corrected}
                />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.uncorrectedGap}
                    label="Uncorrected Gaps"
                    value={`${uncorrectedGapCount} (${uncorrectedPercentage}%)`}
                    description="Sections that may need manual review"
                    details={[
                        { label: "Words Uncorrected", value: uncorrectedWordCount },
                        { label: "Number of Gaps", value: uncorrectedGapCount },
                    ]}
                    onClick={onMetricClick?.uncorrected}
                />
            </Grid>
        </Grid>
    )
} 