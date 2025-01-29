import React from 'react'
import { Paper, Typography } from '@mui/material'
import { TranscriptionViewProps, WordClickInfo } from './types'
import { calculateWordPositions } from './utils/positionCalculator'
import { TextSegment } from './components/TextSegment'

export default function TranscriptionView({
    data,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo
}: TranscriptionViewProps) {
    // Convert WordClickInfo to WordPosition if needed
    const handleWordClick = (info: WordClickInfo) => {
        onWordClick?.(info)
    }

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
            <TextSegment
                wordPositions={wordPositions}
                onElementClick={onElementClick}
                onWordClick={handleWordClick}
                flashingType={flashingType}
                highlightInfo={highlightInfo}
            />
        </Paper>
    )
} 