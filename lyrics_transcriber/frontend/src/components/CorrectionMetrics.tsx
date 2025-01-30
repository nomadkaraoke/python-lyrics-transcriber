import { Grid, Paper, Box, Typography } from '@mui/material'
import { COLORS } from './shared/constants'

interface MetricProps {
    color?: string
    label: string
    value: string | number
    description: string
    details?: Array<{ label: string, value: number }>
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
            <Typography variant="h6">
                {value}
            </Typography>
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
    singleSourceMatches?: {
        spotify: number
        genius: number
    }
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
    onMetricClick?: {
        anchor?: () => void
        corrected?: () => void
        uncorrected?: () => void
    }
}

export default function CorrectionMetrics({
    anchorCount,
    multiSourceAnchors = 0,
    singleSourceMatches = { spotify: 0, genius: 0 },
    correctedGapCount = 0,
    uncorrectedGapCount = 0,
    uncorrectedGaps = [],
    replacedCount = 0,
    addedCount = 0,
    deletedCount = 0,
    onMetricClick
}: CorrectionMetricsProps) {
    const formatPositionLabel = (position: number, length: number) => {
        if (length === 1) {
            return `Position ${position}`;
        }
        return `Positions ${position}-${position + length - 1}`;
    };

    return (
        <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.anchor}
                    label="Anchor Sequences"
                    value={anchorCount ?? '-'}
                    description="Matched sections between transcription and reference"
                    details={[
                        { label: "Multi-source Matches", value: multiSourceAnchors },
                        { label: "Spotify Only", value: singleSourceMatches.spotify },
                        { label: "Genius Only", value: singleSourceMatches.genius },
                    ]}
                    onClick={onMetricClick?.anchor}
                />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.corrected}
                    label="Corrected Gaps"
                    value={correctedGapCount ?? '-'}
                    description="Successfully corrected sections"
                    details={[
                        { label: "Words Replaced", value: replacedCount },
                        { label: "Words Added", value: addedCount },
                        { label: "Words Deleted", value: deletedCount },
                    ]}
                    onClick={onMetricClick?.corrected}
                />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
                <Metric
                    color={COLORS.uncorrectedGap}
                    label="Uncorrected Gaps"
                    value={uncorrectedGapCount}
                    description="Sections that may need manual review"
                    details={uncorrectedGaps.map(gap => ({
                        label: formatPositionLabel(gap.position, gap.length),
                        value: gap.length
                    }))}
                    onClick={onMetricClick?.uncorrected}
                />
            </Grid>
        </Grid>
    )
} 