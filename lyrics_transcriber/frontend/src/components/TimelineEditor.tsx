import { Box, styled } from '@mui/material'
import { Word } from '../types'
import { useRef, useState } from 'react'

interface TimelineEditorProps {
    words: Word[]
    startTime: number
    endTime: number
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    currentTime?: number
}

const TimelineContainer = styled(Box)(({ theme }) => ({
    position: 'relative',
    height: '60px',
    backgroundColor: theme.palette.grey[200],
    borderRadius: theme.shape.borderRadius,
    margin: theme.spacing(2, 0),
    padding: theme.spacing(0, 1),
}))

const TimelineRuler = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '16px',
    borderBottom: `1px solid ${theme.palette.grey[300]}`,
}))

const TimelineMark = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: '10px',
    width: '1px',
    height: '6px',
    backgroundColor: theme.palette.grey[400],
}))

const TimelineLabel = styled(Box)(({ theme }) => ({
    position: 'absolute',
    top: 0,
    transform: 'translateX(-50%)',
    fontSize: '0.6rem',
    color: theme.palette.grey[600],
}))

const TimelineWord = styled(Box)(({ theme }) => ({
    position: 'absolute',
    height: '30px',
    top: '22px',
    backgroundColor: theme.palette.primary.main,
    borderRadius: theme.shape.borderRadius,
    color: theme.palette.primary.contrastText,
    padding: theme.spacing(0.5, 1),
    cursor: 'move',
    userSelect: 'none',
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.875rem',
    transition: 'background-color 0.1s ease',
    '&.highlighted': {
        backgroundColor: theme.palette.secondary.main,
    }
}))

const ResizeHandle = styled(Box)(({ theme }) => ({
    position: 'absolute',
    right: -4,
    top: 0,
    width: 8,
    height: '100%',
    cursor: 'col-resize',
    '&:hover': {
        backgroundColor: theme.palette.primary.light,
    },
}))

export default function TimelineEditor({ words, startTime, endTime, onWordUpdate, currentTime = 0 }: TimelineEditorProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const [dragState, setDragState] = useState<{
        wordIndex: number
        type: 'move' | 'resize'
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
            // If this is the last word, allow it to extend beyond the timeline
            if (currentIndex === words.length - 1) return false;

            const nextWord = words[currentIndex + 1]
            if (!nextWord) return false
            const hasCollision = proposedEnd > nextWord.start_time
            if (hasCollision) {
                console.log('Resize collision detected:', {
                    proposedEnd,
                    nextWordStart: nextWord.start_time,
                    word: words[currentIndex].text,
                    nextWord: nextWord.text
                })
            }
            return hasCollision
        }

        // For move operations, check all words
        return words.some((word, index) => {
            if (index === currentIndex) return false
            const overlap = (
                (proposedStart >= word.start_time && proposedStart <= word.end_time) ||
                (proposedEnd >= word.start_time && proposedEnd <= word.end_time) ||
                (proposedStart <= word.start_time && proposedEnd >= word.end_time)
            )
            if (overlap) {
                console.log('Move collision detected:', {
                    movingWord: words[currentIndex].text,
                    collidingWord: word.text,
                    proposedTimes: { start: proposedStart, end: proposedEnd },
                    collidingTimes: { start: word.start_time, end: word.end_time }
                })
            }
            return overlap
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

        for (let time = startSecond; time <= endSecond; time++) {
            if (time >= startTime && time <= endTime) {
                const position = timeToPosition(time)
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

    const handleMouseDown = (e: React.MouseEvent, wordIndex: number, type: 'move' | 'resize') => {
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return

        const initialX = e.clientX - rect.left
        const initialTime = ((initialX / rect.width) * (endTime - startTime))

        console.log('Mouse down:', {
            type,
            wordIndex,
            initialX,
            initialTime,
            word: words[wordIndex]
        })

        setDragState({
            wordIndex,
            type,
            initialX,
            initialTime,
            word: words[wordIndex]
        })
    }

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!dragState || !containerRef.current) return

        const rect = containerRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left
        const width = rect.width

        if (dragState.type === 'resize') {
            const currentWord = words[dragState.wordIndex]
            // Use the initial word duration for consistent scaling
            const initialWordDuration = dragState.word.end_time - dragState.word.start_time
            const initialWordWidth = (initialWordDuration / (endTime - startTime)) * width

            // Calculate how much the mouse has moved as a percentage of the initial word width
            const pixelDelta = x - dragState.initialX
            const percentageMoved = pixelDelta / initialWordWidth
            const timeDelta = initialWordDuration * percentageMoved

            console.log('Resize calculation:', {
                initialWordWidth,
                initialWordDuration,
                pixelDelta,
                percentageMoved,
                timeDelta,
                currentDuration: currentWord.end_time - currentWord.start_time
            })

            const proposedEnd = Math.max(
                currentWord.start_time + MIN_DURATION,
                dragState.word.end_time + timeDelta  // Use initial end time as reference
            )

            // Check for collisions
            if (checkCollision(currentWord.start_time, proposedEnd, dragState.wordIndex, true)) return

            // If we get here, the resize is valid
            onWordUpdate(dragState.wordIndex, {
                start_time: currentWord.start_time,
                end_time: proposedEnd
            })
        } else if (dragState.type === 'move') {
            // Use timeline scale for consistent movement
            const pixelsPerSecond = width / (endTime - startTime)
            const pixelDelta = x - dragState.initialX
            const timeDelta = pixelDelta / pixelsPerSecond

            const currentWord = words[dragState.wordIndex]
            const wordDuration = currentWord.end_time - currentWord.start_time

            console.log('Move calculation:', {
                timelineWidth: width,
                timelineDuration: endTime - startTime,
                pixelsPerSecond,
                pixelDelta,
                timeDelta,
                currentDuration: wordDuration
            })

            const proposedStart = dragState.word.start_time + timeDelta
            const proposedEnd = proposedStart + wordDuration

            // Ensure we stay within timeline bounds
            if (proposedStart < startTime || proposedEnd > endTime) return

            // Check for collisions
            if (checkCollision(proposedStart, proposedEnd, dragState.wordIndex, false)) return

            // If we get here, the move is valid
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
        if (!currentTime || !word.start_time || !word.end_time) return false
        return currentTime >= word.start_time && currentTime <= word.end_time
    }

    return (
        <TimelineContainer
            ref={containerRef}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        >
            <TimelineRuler>
                {generateTimelineMarks()}
            </TimelineRuler>
            {words.map((word, index) => {
                const leftPosition = timeToPosition(word.start_time)
                const rightPosition = timeToPosition(word.end_time)
                const width = rightPosition - leftPosition

                // Add visual padding only to right side (2% of total width)
                const visualPadding = 2 // percentage points
                const adjustedWidth = Math.max(0, width - visualPadding)

                return (
                    <TimelineWord
                        key={index}
                        className={isWordHighlighted(word) ? 'highlighted' : ''}
                        sx={{
                            left: `${leftPosition}%`,  // No adjustment to left position
                            width: `${adjustedWidth}%`,
                            // Ensure the last word doesn't overflow
                            maxWidth: `calc(${100 - leftPosition}% - 2px)`,
                        }}
                        onMouseDown={(e) => {
                            e.stopPropagation();  // Prevent the parent's mousedown from firing
                            handleMouseDown(e, index, 'move');
                        }}
                    >
                        {word.text}
                        <ResizeHandle
                            onMouseDown={(e) => {
                                e.stopPropagation();  // Prevent the parent's mousedown from firing
                                handleMouseDown(e, index, 'resize');
                            }}
                        />
                    </TimelineWord>
                )
            })}
        </TimelineContainer>
    )
} 