import { Box, styled } from '@mui/material'
import { Word } from '../types'
import { useRef, useState } from 'react'

interface TimelineEditorProps {
    words: Word[]
    startTime: number
    endTime: number
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    currentTime?: number
    onPlaySegment?: (time: number) => void
    showPlaybackIndicator?: boolean
}

const TimelineContainer = styled(Box)(({ theme }) => ({
    position: 'relative',
    height: '75px',
    backgroundColor: theme.palette.grey[200],
    borderRadius: theme.shape.borderRadius,
    margin: theme.spacing(1, 0),
    padding: theme.spacing(0, 1),
}))

const TimelineRuler = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '40px',
    borderBottom: `1px solid ${theme.palette.grey[300]}`,
    cursor: 'pointer',
}))

const TimelineMark = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: '20px',
    width: '1px',
    height: '18px',
    backgroundColor: theme.palette.grey[700],
    '&.subsecond': {
        top: '25px',
        height: '13px',
        backgroundColor: theme.palette.grey[500],
    }
}))

const TimelineLabel = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: '5px',
    transform: 'translateX(-50%)',
    fontSize: '0.8rem',
    color: theme.palette.text.primary,
    fontWeight: 700,
    backgroundColor: theme.palette.grey[200],
}))

const TimelineWord = styled(Box)(({ theme }) => ({
    position: 'absolute',
    height: '30px',
    top: '40px',
    backgroundColor: theme.palette.primary.main,
    borderRadius: theme.shape.borderRadius,
    color: theme.palette.primary.contrastText,
    padding: theme.spacing(0.5, 1),
    cursor: 'move',
    userSelect: 'none',
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.875rem',
    fontFamily: 'sans-serif',
    transition: 'background-color 0.1s ease',
    boxSizing: 'border-box',
    '&.highlighted': {
        backgroundColor: theme.palette.secondary.main,
    }
}))

const ResizeHandle = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: 0,
    width: 10,
    height: '100%',
    cursor: 'col-resize',
    '&:hover': {
        backgroundColor: theme.palette.primary.light,
        opacity: 0.8,
        boxShadow: `0 0 0 1px ${theme.palette.primary.dark}`,
    },
    '&.left': {
        left: 0,
        right: 'auto',
        paddingRight: 0,
        borderTopLeftRadius: theme.shape.borderRadius,
        borderBottomLeftRadius: theme.shape.borderRadius,
    },
    '&.right': {
        right: 0,
        left: 'auto',
        paddingLeft: 0,
        borderTopRightRadius: theme.shape.borderRadius,
        borderBottomRightRadius: theme.shape.borderRadius,
    }
}))

// Add new styled component for the cursor
const TimelineCursor = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: 0,
    width: '2px',
    height: '100%', // Full height of container
    backgroundColor: theme.palette.error.main, // Red color
    pointerEvents: 'none', // Ensure it doesn't interfere with clicks
    transition: 'left 0.1s linear', // Smooth movement
    zIndex: 1, // Ensure it's above other elements
}))

export default function TimelineEditor({ words, startTime, endTime, onWordUpdate, currentTime = 0, onPlaySegment, showPlaybackIndicator = true }: TimelineEditorProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const [dragState, setDragState] = useState<{
        wordIndex: number
        type: 'move' | 'resize-left' | 'resize-right'
        initialX: number
        initialTime: number
        word: Word
    } | null>(null)

    const MIN_DURATION = 0.1 // Minimum word duration in seconds

    const checkCollision = (
        proposedStart: number,
        proposedEnd: number,
        currentIndex: number,
        isResize: boolean
    ): boolean => {
        if (isResize) {
            if (currentIndex === words.length - 1) return false;

            const nextWord = words[currentIndex + 1]
            if (!nextWord || nextWord.start_time === null) return false
            return proposedEnd > nextWord.start_time
        }

        return words.some((word, index) => {
            if (index === currentIndex) return false
            if (word.start_time === null || word.end_time === null) return false

            return (
                (proposedStart >= word.start_time && proposedStart <= word.end_time) ||
                (proposedEnd >= word.start_time && proposedEnd <= word.end_time) ||
                (proposedStart <= word.start_time && proposedEnd >= word.end_time)
            )
        })
    }

    const timeToPosition = (time: number): number => {
        const duration = endTime - startTime
        const position = ((time - startTime) / duration) * 100
        return Math.max(0, Math.min(100, position))
    }

    const generateTimelineMarks = () => {
        const marks = []
        const startSecond = Math.floor(startTime)
        const endSecond = Math.ceil(endTime)

        // Generate marks for each 0.1 second interval
        for (let time = startSecond; time <= endSecond; time += 0.1) {
            if (time >= startTime && time <= endTime) {
                const position = timeToPosition(time)
                const isFullSecond = Math.abs(time - Math.round(time)) < 0.001

                marks.push(
                    <Box key={time}>
                        <TimelineMark
                            className={isFullSecond ? '' : 'subsecond'}
                            sx={{ left: `${position}%` }}
                        />
                        {isFullSecond && (
                            <TimelineLabel sx={{ left: `${position}%` }}>
                                {Math.round(time)}s
                            </TimelineLabel>
                        )}
                    </Box>
                )
            }
        }
        return marks
    }

    const handleMouseDown = (e: React.MouseEvent, wordIndex: number, type: 'move' | 'resize-left' | 'resize-right') => {
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return

        const word = words[wordIndex]
        if (word.start_time === null || word.end_time === null) return

        const initialX = e.clientX - rect.left
        const initialTime = ((initialX / rect.width) * (endTime - startTime))

        setDragState({
            wordIndex,
            type,
            initialX,
            initialTime,
            word
        })
    }

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!dragState || !containerRef.current) return

        const rect = containerRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left
        const width = rect.width

        const currentWord = words[dragState.wordIndex]
        if (currentWord.start_time === null || currentWord.end_time === null ||
            dragState.word.start_time === null || dragState.word.end_time === null) return

        if (dragState.type === 'resize-right') {
            const initialWordDuration = dragState.word.end_time - dragState.word.start_time
            const initialWordWidth = (initialWordDuration / (endTime - startTime)) * width
            const pixelDelta = x - dragState.initialX
            const percentageMoved = pixelDelta / initialWordWidth
            const timeDelta = initialWordDuration * percentageMoved

            const proposedEnd = Math.max(
                currentWord.start_time + MIN_DURATION,
                dragState.word.end_time + timeDelta
            )

            if (checkCollision(currentWord.start_time, proposedEnd, dragState.wordIndex, true)) return

            onWordUpdate(dragState.wordIndex, {
                start_time: currentWord.start_time,
                end_time: proposedEnd
            })
        } else if (dragState.type === 'resize-left') {
            const initialWordDuration = dragState.word.end_time - dragState.word.start_time
            const initialWordWidth = (initialWordDuration / (endTime - startTime)) * width
            const pixelDelta = x - dragState.initialX
            const percentageMoved = pixelDelta / initialWordWidth
            const timeDelta = initialWordDuration * percentageMoved

            const proposedStart = Math.min(
                currentWord.end_time - MIN_DURATION,
                dragState.word.start_time + timeDelta
            )

            if (checkCollision(proposedStart, currentWord.end_time, dragState.wordIndex, true)) return

            onWordUpdate(dragState.wordIndex, {
                start_time: proposedStart,
                end_time: currentWord.end_time
            })
        } else if (dragState.type === 'move') {
            const pixelsPerSecond = width / (endTime - startTime)
            const pixelDelta = x - dragState.initialX
            const timeDelta = pixelDelta / pixelsPerSecond

            const wordDuration = currentWord.end_time - currentWord.start_time
            const proposedStart = dragState.word.start_time + timeDelta
            const proposedEnd = proposedStart + wordDuration

            if (proposedStart < startTime || proposedEnd > endTime) return
            if (checkCollision(proposedStart, proposedEnd, dragState.wordIndex, false)) return

            onWordUpdate(dragState.wordIndex, {
                start_time: proposedStart,
                end_time: proposedEnd
            })
        }
    }

    const handleMouseUp = () => {
        setDragState(null)
    }

    const isWordHighlighted = (word: Word): boolean => {
        if (!currentTime || word.start_time === null || word.end_time === null) return false
        return currentTime >= word.start_time && currentTime <= word.end_time
    }

    const handleTimelineClick = (e: React.MouseEvent) => {
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect || !onPlaySegment) return

        const x = e.clientX - rect.left
        const clickedPosition = (x / rect.width) * (endTime - startTime) + startTime

        console.log('Timeline clicked:', {
            x,
            width: rect.width,
            clickedTime: clickedPosition
        })

        onPlaySegment(clickedPosition)
    }

    return (
        <TimelineContainer
            ref={containerRef}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        >
            <TimelineRuler onClick={handleTimelineClick}>
                {generateTimelineMarks()}
            </TimelineRuler>

            {/* Add cursor line */}
            {showPlaybackIndicator && (
                <TimelineCursor
                    sx={{
                        left: `${timeToPosition(currentTime)}%`,
                        display: currentTime >= startTime && currentTime <= endTime ? 'block' : 'none'
                    }}
                />
            )}

            {words.map((word, index) => {
                // Skip words with null timestamps
                if (word.start_time === null || word.end_time === null) return null;

                const leftPosition = timeToPosition(word.start_time)
                const rightPosition = timeToPosition(word.end_time)
                const width = rightPosition - leftPosition
                // Remove the visual padding that creates gaps
                const adjustedWidth = width

                return (
                    <TimelineWord
                        key={index}
                        className={isWordHighlighted(word) ? 'highlighted' : ''}
                        sx={{
                            left: `${leftPosition}%`,
                            width: `${adjustedWidth}%`,
                            maxWidth: `calc(${100 - leftPosition}%)`,
                        }}
                        onMouseDown={(e) => {
                            e.stopPropagation()
                            handleMouseDown(e, index, 'move')
                        }}
                    >
                        <ResizeHandle
                            className="left"
                            onMouseDown={(e) => {
                                e.stopPropagation()
                                handleMouseDown(e, index, 'resize-left')
                            }}
                        />
                        {word.text}
                        <ResizeHandle
                            className="right"
                            onMouseDown={(e) => {
                                e.stopPropagation()
                                handleMouseDown(e, index, 'resize-right')
                            }}
                        />
                    </TimelineWord>
                )
            })}
        </TimelineContainer>
    )
} 