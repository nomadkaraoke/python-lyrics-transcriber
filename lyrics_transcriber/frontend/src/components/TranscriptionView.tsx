import { useState } from 'react'
import { Paper, Typography, Box } from '@mui/material'
import { TranscriptionViewProps } from './shared/types'
import { HighlightedText } from './shared/components/HighlightedText'
import { styled } from '@mui/material/styles'
import SegmentDetailsModal from './SegmentDetailsModal'
import { TranscriptionWordPosition } from './shared/types'

const SegmentIndex = styled(Typography)(({ theme }) => ({
    color: theme.palette.text.secondary,
    width: '2em',
    minWidth: '2em',
    textAlign: 'right',
    marginRight: theme.spacing(1),
    userSelect: 'none',
    fontFamily: 'monospace',
    cursor: 'pointer',
    paddingTop: '4px',
    '&:hover': {
        textDecoration: 'underline',
    },
}))

const TextContainer = styled(Box)({
    flex: 1,
    minWidth: 0,
})

export default function TranscriptionView({
    data,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo,
    mode
}: TranscriptionViewProps) {
    const [selectedSegmentIndex, setSelectedSegmentIndex] = useState<number | null>(null)

    // Keep track of global word position
    let globalWordPosition = 0

    return (
        <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                Corrected Transcription
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                {data.corrected_segments.map((segment, segmentIndex) => {
                    // Convert segment words to TranscriptionWordPosition format
                    const segmentWords: TranscriptionWordPosition[] = segment.words.map((word, idx) => {
                        const position = globalWordPosition + idx
                        const anchor = data.anchor_sequences.find(a =>
                            position >= a.transcription_position &&
                            position < a.transcription_position + a.length
                        )
                        const gap = !anchor ? data.gap_sequences.find(g =>
                            position >= g.transcription_position &&
                            position < g.transcription_position + g.length
                        ) : undefined

                        return {
                            word: word.text,
                            position,
                            type: anchor ? 'anchor' : gap ? 'gap' : 'other',
                            sequence: anchor || gap,
                            isInRange: true
                        }
                    })

                    // Update global position counter for next segment
                    globalWordPosition += segment.words.length

                    return (
                        <Box key={segmentIndex} sx={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
                            <SegmentIndex
                                variant="body2"
                                onClick={() => setSelectedSegmentIndex(segmentIndex)}
                            >
                                {segmentIndex}
                            </SegmentIndex>
                            <TextContainer>
                                <HighlightedText
                                    wordPositions={segmentWords}
                                    anchors={data.anchor_sequences}
                                    gaps={data.gap_sequences}
                                    onElementClick={onElementClick}
                                    onWordClick={onWordClick}
                                    flashingType={flashingType}
                                    highlightInfo={highlightInfo}
                                    mode={mode}
                                    preserveSegments={true}
                                />
                            </TextContainer>
                        </Box>
                    )
                })}
            </Box>

            <SegmentDetailsModal
                open={selectedSegmentIndex !== null}
                onClose={() => setSelectedSegmentIndex(null)}
                segment={selectedSegmentIndex !== null ? data.corrected_segments[selectedSegmentIndex] : null}
                segmentIndex={selectedSegmentIndex}
            />
        </Paper>
    )
} 