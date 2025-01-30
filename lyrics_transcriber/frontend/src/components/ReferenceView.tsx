import { useMemo } from 'react'
import { Paper, Typography, Box } from '@mui/material'
import { ReferenceViewProps } from './shared/types'
import { calculateNewlineIndices } from './shared/utils/newlineCalculator'
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
    const newlineIndices = useMemo(() =>
        calculateNewlineIndices(corrected_segments, anchors, currentSource),
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
                />
            </Box>
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
                newlineIndices={newlineIndices}
            />
        </Paper>
    )
} 