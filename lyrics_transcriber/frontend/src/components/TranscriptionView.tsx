import React from 'react'
import { Paper, Typography } from '@mui/material'
import { TranscriptionViewProps } from './shared/types'
import { calculateWordPositions } from './shared/utils/positionCalculator'
import { HighlightedText } from './shared/components/HighlightedText'

export default function TranscriptionView({
    data,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo,
    mode
}: TranscriptionViewProps) {
    // Calculate word positions once when data changes
    const wordPositions = React.useMemo(
        () => calculateWordPositions(data),
        [data]
    )

    return (
        <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                Corrected Transcription
            </Typography>
            <HighlightedText
                wordPositions={wordPositions}
                anchors={data.anchor_sequences}
                gaps={data.gap_sequences}
                onElementClick={onElementClick}
                onWordClick={onWordClick}
                flashingType={flashingType}
                highlightInfo={highlightInfo}
                mode={mode}
            />
        </Paper>
    )
} 