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
    flashingHandler,
    highlightInfo,
    mode,
    onPlaySegment,
    currentTime = 0,
    anchors = []
}: TranscriptionViewProps) {
    console.log('TranscriptionView props:', { flashingType, flashingHandler });
    const [selectedSegmentIndex, setSelectedSegmentIndex] = useState<number | null>(null)

    return (
        <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
                Corrected Transcription
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                {data.corrected_segments.map((segment, segmentIndex) => {
                    const segmentWords: TranscriptionWordPosition[] = segment.words.map(word => {
                        // Find if this word is part of a correction
                        const correction = data.corrections?.find(c => 
                            c.corrected_word_id === word.id || 
                            c.word_id === word.id
                        )

                        // Find if this word is part of an anchor sequence
                        const anchor = data.anchor_sequences?.find(a =>
                            a.transcribed_word_ids.includes(word.id)
                        )

                        // If not in anchor, check if it belongs to a gap sequence
                        const gap = data.gap_sequences?.find(g => {
                            // Check transcribed words
                            const inTranscribed = g.transcribed_word_ids.includes(word.id)

                            // Check reference words
                            const inReference = Object.values(g.reference_word_ids).some(ids =>
                                ids.includes(word.id)
                            )

                            // Check if this word is a corrected version
                            const isCorrection = data.corrections.some(c =>
                                (c.corrected_word_id === word.id || c.word_id === word.id) &&
                                g.transcribed_word_ids.includes(c.word_id)
                            )

                            return inTranscribed || inReference || isCorrection
                        })

                        return {
                            word: {
                                id: word.id,
                                text: word.text,
                                start_time: word.start_time ?? undefined,
                                end_time: word.end_time ?? undefined
                            },
                            type: anchor ? 'anchor' : gap ? 'gap' : 'other',
                            sequence: anchor || gap,
                            sequencePosition: anchor?.transcription_position ?? gap?.transcription_position ?? undefined,
                            isInRange: true,
                            isCorrected: Boolean(correction),
                            gap: gap
                        }
                    })

                    return (
                        <Box key={segment.id} sx={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
                            <SegmentControls>
                                <SegmentIndex
                                    variant="body2"
                                    onClick={() => setSelectedSegmentIndex(segmentIndex)}
                                >
                                    {segmentIndex}
                                </SegmentIndex>
                                {segment.start_time !== null && (
                                    <IconButton
                                        size="small"
                                        onClick={() => onPlaySegment?.(segment.start_time!)}
                                        sx={{ padding: '2px' }}
                                    >
                                        <PlayCircleOutlineIcon fontSize="small" />
                                    </IconButton>
                                )}
                            </SegmentControls>
                            <TextContainer>
                                <HighlightedText
                                    wordPositions={segmentWords}
                                    anchors={anchors}
                                    onElementClick={onElementClick}
                                    onWordClick={onWordClick}
                                    flashingType={flashingType}
                                    flashingHandler={flashingHandler}
                                    highlightInfo={highlightInfo}
                                    mode={mode}
                                    preserveSegments={true}
                                    currentTime={currentTime}
                                    gaps={data.gap_sequences}
                                    corrections={data.corrections}
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