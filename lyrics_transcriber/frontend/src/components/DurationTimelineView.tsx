import { Box, Typography, styled } from '@mui/material'
import { LyricsSegment, WordCorrection, AnchorSequence, GapSequence } from '../types'
import { COLORS } from './shared/constants'
import WarningIcon from '@mui/icons-material/Warning'

interface DurationTimelineViewProps {
    segments: LyricsSegment[]
    corrections: WordCorrection[]
    anchors: AnchorSequence[]
    gaps: GapSequence[]
    onWordClick?: (wordId: string) => void
}

const TimelineContainer = styled(Box)({
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '8px',
    overflowX: 'auto',
    minWidth: '100%'
})

const SegmentTimeline = styled(Box)({
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    minWidth: '100%'
})

const TimelineRuler = styled(Box)({
    position: 'relative',
    height: '20px',
    borderBottom: '1px solid #ccc',
    marginBottom: '4px'
})

const TimelineMark = styled(Box)({
    position: 'absolute',
    width: '1px',
    height: '8px',
    backgroundColor: '#999',
    bottom: 0
})

const TimelineLabel = styled(Typography)({
    position: 'absolute',
    fontSize: '0.65rem',
    color: '#666',
    bottom: '10px',
    transform: 'translateX(-50%)',
    whiteSpace: 'nowrap'
})

const WordsBar = styled(Box)({
    position: 'relative',
    height: '60px', // Increased from 48px for better readability
    display: 'flex',
    alignItems: 'stretch',
    minWidth: '100%',
    touchAction: 'pan-y', // Better mobile scrolling
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
    marginBottom: '8px'
})

const WordBar = styled(Box, {
    shouldForwardProp: (prop) => !['isLong', 'isCorrected', 'isGap', 'isAnchor'].includes(prop as string)
})<{ isLong?: boolean; isCorrected?: boolean; isGap?: boolean; isAnchor?: boolean }>(
    ({ isLong, isCorrected, isGap, isAnchor }) => ({
        position: 'absolute',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '2px 4px',
        borderRight: '1px solid rgba(255,255,255,0.3)',
        fontSize: '0.75rem',
        cursor: 'pointer',
        transition: 'all 0.2s',
        backgroundColor: isAnchor 
            ? COLORS.anchor
            : isCorrected
                ? COLORS.corrected
                : isGap
                    ? COLORS.uncorrectedGap
                    : '#e0e0e0',
        border: isLong ? '2px solid #f44336' : 'none',
        boxShadow: isLong ? '0 0 4px rgba(244, 67, 54, 0.5)' : 'none',
        '&:hover': {
            opacity: 0.8,
            transform: 'scale(1.02)',
            zIndex: 10
        },
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        minWidth: '20px' // Ensure very short words are still tappable
    })
)

const OriginalWordLabel = styled(Typography)({
    fontSize: '0.65rem',
    color: '#888',
    lineHeight: 1.1,
    marginBottom: '3px',
    textDecoration: 'line-through',
    opacity: 0.85,
    fontWeight: 500,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    padding: '1px 3px',
    borderRadius: '2px'
})

const LongWordWarning = styled(WarningIcon)({
    position: 'absolute',
    top: '-2px',
    right: '-2px',
    fontSize: '16px',
    color: '#f44336'
})

export default function DurationTimelineView({
    segments,
    corrections,
    anchors,
    gaps,
    onWordClick
}: DurationTimelineViewProps) {
    
    const timeToPosition = (time: number, startTime: number, endTime: number): number => {
        const duration = endTime - startTime
        if (duration === 0) return 0
        const position = ((time - startTime) / duration) * 100
        return Math.max(0, Math.min(100, position))
    }

    const generateTimelineMarks = (startTime: number, endTime: number) => {
        const marks = []
        const startSecond = Math.floor(startTime)
        const endSecond = Math.ceil(endTime)

        // Generate marks roughly every 2 seconds for readability
        for (let time = startSecond; time <= endSecond; time += 2) {
            if (time >= startTime && time <= endTime) {
                const position = timeToPosition(time, startTime, endTime)
                marks.push(
                    <Box key={time}>
                        <TimelineMark sx={{ left: `${position}%` }} />
                        <TimelineLabel sx={{ left: `${position}%` }}>
                            {time}s
                        </TimelineLabel>
                    </Box>
                )
            }
        }
        return marks
    }

    return (
        <TimelineContainer>
            {segments.map((segment) => {
                // Calculate segment time range
                const segmentWords = segment.words.filter(w => w.start_time !== null && w.end_time !== null)
                if (segmentWords.length === 0) return null

                const startTime = Math.min(...segmentWords.map(w => w.start_time!))
                const endTime = Math.max(...segmentWords.map(w => w.end_time!))

                return (
                    <SegmentTimeline key={segment.id}>
                        <TimelineRuler>
                            {generateTimelineMarks(startTime, endTime)}
                        </TimelineRuler>
                        <WordsBar>
                            {segment.words.map((word, wordIndex) => {
                                if (word.start_time === null || word.end_time === null) return null

                                const leftPosition = timeToPosition(word.start_time, startTime, endTime)
                                const rightPosition = timeToPosition(word.end_time, startTime, endTime)
                                const width = rightPosition - leftPosition
                                const duration = word.end_time - word.start_time
                                const isLong = duration > 2.0

                                // Check if this word is corrected
                                const correction = corrections.find(c =>
                                    c.corrected_word_id === word.id || c.word_id === word.id
                                )

                                // Check if anchor
                                const isAnchor = anchors.some(a =>
                                    a.transcribed_word_ids.includes(word.id)
                                )

                                // Check if uncorrected gap
                                const isGap = gaps.some(g =>
                                    g.transcribed_word_ids.includes(word.id)
                                ) && !correction

                                return (
                                    <WordBar
                                        key={`${segment.id}-${wordIndex}`}
                                        sx={{
                                            left: `${leftPosition}%`,
                                            width: `${width}%`
                                        }}
                                        isLong={isLong}
                                        isCorrected={!!correction}
                                        isGap={isGap}
                                        isAnchor={isAnchor}
                                        onClick={() => onWordClick?.(word.id)}
                                    >
                                        {isLong && <LongWordWarning />}
                                        {correction && (
                                            <OriginalWordLabel>
                                                {correction.original_word}
                                            </OriginalWordLabel>
                                        )}
                                        <Typography
                                            sx={{
                                                fontSize: correction ? '0.85rem' : '0.75rem',
                                                fontWeight: correction ? 700 : 500,
                                                lineHeight: 1.2,
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                                width: '100%',
                                                textAlign: 'center',
                                                color: correction ? '#1b5e20' : 'inherit'
                                            }}
                                        >
                                            {word.text}
                                        </Typography>
                                        {duration > 0.1 && (
                                            <Typography
                                                sx={{
                                                    fontSize: '0.6rem',
                                                    color: 'rgba(0,0,0,0.6)',
                                                    lineHeight: 1,
                                                    marginTop: '3px',
                                                    fontWeight: 600
                                                }}
                                            >
                                                {duration.toFixed(1)}s
                                            </Typography>
                                        )}
                                    </WordBar>
                                )
                            })}
                        </WordsBar>
                    </SegmentTimeline>
                )
            })}
        </TimelineContainer>
    )
}

