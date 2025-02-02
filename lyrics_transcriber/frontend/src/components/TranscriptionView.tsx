import { useState } from 'react'
import { Paper, Typography, Box, IconButton } from '@mui/material'
import { TranscriptionViewProps } from './shared/types'
import { HighlightedText } from './shared/components/HighlightedText'
import { styled } from '@mui/material/styles'
import SegmentDetailsModal from './SegmentDetailsModal'
import { TranscriptionWordPosition } from './shared/types'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'

const SegmentIndex = styled(Typography)(({ theme }) => ({
    color: theme.palette.text.secondary,
    width: '2em',
    minWidth: '2em',
    textAlign: 'right',
    marginRight: theme.spacing(1),
    userSelect: 'none',
    fontFamily: 'monospace',
    cursor: 'pointer',
    paddingTop: '3px',
    '&:hover': {
        textDecoration: 'underline',
    },
}))

const TextContainer = styled(Box)({
    flex: 1,
    minWidth: 0,
})

const SegmentControls = styled(Box)({
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    minWidth: '3em',
    paddingTop: '3px',
    paddingRight: '8px'
})

export default function TranscriptionView({
    data,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo,
    mode,
    onPlaySegment,
    currentTime = 0
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
                            word: {
                                text: word.text,
                                start_time: word.start_time,
                                end_time: word.end_time
                            },
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
                            <SegmentControls>
                                <SegmentIndex
                                    variant="body2"
                                    onClick={() => setSelectedSegmentIndex(segmentIndex)}
                                >
                                    {segmentIndex}
                                </SegmentIndex>
                                {segment.start_time !== undefined && (
                                    <IconButton
                                        size="small"
                                        onClick={() => onPlaySegment?.(segment.start_time)}
                                        sx={{ padding: '2px' }}
                                    >
                                        <PlayCircleOutlineIcon fontSize="small" />
                                    </IconButton>
                                )}
                            </SegmentControls>
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
                                    currentTime={currentTime}
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