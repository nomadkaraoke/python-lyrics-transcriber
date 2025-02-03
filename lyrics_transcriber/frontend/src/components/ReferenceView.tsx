import { useMemo } from 'react'
import { Paper, Typography, Box } from '@mui/material'
import { ReferenceViewProps } from './shared/types'
import { calculateReferenceLinePositions } from './shared/utils/referenceLineCalculator'
import { SourceSelector } from './shared/components/SourceSelector'
import { HighlightedText } from './shared/components/HighlightedText'

export default function ReferenceView({
    referenceTexts,
    anchors,
    gaps,
    onElementClick,
    onWordClick,
    flashingType,
    corrected_segments,
    currentSource,
    onSourceChange,
    highlightInfo,
    mode
}: ReferenceViewProps) {
    // Get available sources from referenceTexts object
    const availableSources = useMemo(() => 
        Object.keys(referenceTexts) as Array<string>,
        [referenceTexts]
    )

    const { linePositions } = useMemo(() =>
        calculateReferenceLinePositions(
            corrected_segments,
            anchors,
            currentSource
        ),
        [corrected_segments, anchors, currentSource]
    )

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    Reference Text
                </Typography>
                <SourceSelector
                    currentSource={currentSource}
                    onSourceChange={onSourceChange}
                    availableSources={availableSources}
                />
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <HighlightedText
                    text={referenceTexts[currentSource]}
                    anchors={anchors}
                    gaps={gaps}
                    onElementClick={onElementClick}
                    onWordClick={onWordClick}
                    flashingType={flashingType}
                    highlightInfo={highlightInfo}
                    mode={mode}
                    isReference={true}
                    currentSource={currentSource}
                    linePositions={linePositions}
                />
            </Box>
        </Paper>
    )
} 