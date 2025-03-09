import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import StopIcon from '@mui/icons-material/Stop'
import { LyricsSegment, Word } from '../types'
import { useState, useEffect, useCallback } from 'react'
import { nanoid } from 'nanoid'
import useManualSync from '../hooks/useManualSync'
import EditTimelineSection from './EditTimelineSection'
import EditWordList from './EditWordList'
import EditActionBar from './EditActionBar'

interface EditModalProps {
    open: boolean
    onClose: () => void
    segment: LyricsSegment | null
    segmentIndex: number | null
    originalSegment: LyricsSegment | null
    onSave: (updatedSegment: LyricsSegment) => void
    onPlaySegment?: (startTime: number) => void
    currentTime?: number
    onDelete?: (segmentIndex: number) => void
    onAddSegment?: (segmentIndex: number) => void
    onSplitSegment?: (segmentIndex: number, afterWordIndex: number) => void
    onMergeSegment?: (segmentIndex: number, mergeWithNext: boolean) => void
    setModalSpacebarHandler: (handler: (() => (e: KeyboardEvent) => void) | undefined) => void
    originalTranscribedSegment?: LyricsSegment | null
    isGlobal?: boolean
}

export default function EditModal({
    open,
    onClose,
    segment,
    segmentIndex,
    originalSegment,
    onSave,
    onPlaySegment,
    currentTime = 0,
    onDelete,
    onAddSegment,
    onSplitSegment,
    onMergeSegment,
    setModalSpacebarHandler,
    originalTranscribedSegment,
    isGlobal = false
}: EditModalProps) {
    const [editedSegment, setEditedSegment] = useState<LyricsSegment | null>(segment)
    const [isPlaying, setIsPlaying] = useState(false)

    // Define updateSegment first since the hook depends on it
    const updateSegment = useCallback((newWords: Word[]) => {
        if (!editedSegment) return;

        const validStartTimes = newWords.map(w => w.start_time).filter((t): t is number => t !== null)
        const validEndTimes = newWords.map(w => w.end_time).filter((t): t is number => t !== null)

        const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
        const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

        setEditedSegment({
            ...editedSegment,
            words: newWords,
            text: newWords.map(w => w.text).join(' '),
            start_time: segmentStartTime,
            end_time: segmentEndTime
        })
    }, [editedSegment])

    // Use the manual sync hook
    const {
        isManualSyncing,
        syncWordIndex,
        startManualSync,
        cleanupManualSync,
        handleSpacebar,
        isSpacebarPressed
    } = useManualSync({
        editedSegment,
        currentTime,
        onPlaySegment,
        updateSegment
    })

    const handleClose = useCallback(() => {
        cleanupManualSync()
        onClose()
    }, [onClose, cleanupManualSync])

    // Update the spacebar handler when modal state changes
    useEffect(() => {
        const spacebarHandler = handleSpacebar // Capture the current handler

        if (open) {
            console.log('EditModal - Setting up modal spacebar handler', {
                hasPlaySegment: !!onPlaySegment,
                editedSegmentId: editedSegment?.id,
                handlerFunction: spacebarHandler.toString().slice(0, 100)
            })

            // Create a function that will be called by the global event listeners
            const handleKeyEvent = (e: KeyboardEvent) => {
                if (e.code === 'Space') {
                    spacebarHandler(e)
                }
            }

            setModalSpacebarHandler(() => handleKeyEvent)

            // Only cleanup when the effect is re-run or the modal is closed
            return () => {
                if (!open) {
                    console.log('EditModal - Cleanup: clearing modal spacebar handler')
                    setModalSpacebarHandler(undefined)
                }
            }
        }
    }, [
        open,
        handleSpacebar,
        setModalSpacebarHandler,
        editedSegment?.id,
        onPlaySegment
    ])

    // Update isPlaying when currentTime changes
    useEffect(() => {
        if (editedSegment) {
            const startTime = editedSegment.start_time ?? 0
            const endTime = editedSegment.end_time ?? 0
            const isWithinSegment = currentTime >= startTime && currentTime <= endTime

            setIsPlaying(isWithinSegment && window.isAudioPlaying === true)
        }
    }, [currentTime, editedSegment])

    // All useEffect hooks
    useEffect(() => {
        setEditedSegment(segment)
    }, [segment])

    // Auto-stop sync if we go past the end time
    useEffect(() => {
        if (!editedSegment) return

        const endTime = editedSegment.end_time ?? 0

        if (window.isAudioPlaying && currentTime > endTime) {
            console.log('Stopping playback: current time exceeded end time')
            window.toggleAudioPlayback?.()
            cleanupManualSync()
        }

    }, [isManualSyncing, editedSegment, currentTime, cleanupManualSync])

    // Add a function to get safe time values
    const getSafeTimeRange = (segment: LyricsSegment | null) => {
        if (!segment) return { start: 0, end: 1 }; // Default 1-second range
        const start = segment.start_time ?? 0;
        const end = segment.end_time ?? (start + 1);
        return { start, end };
    }

    // Early return after all hooks and function definitions
    if (!segment || segmentIndex === null || !editedSegment || !originalSegment) return null

    // Get safe time values for TimelineEditor
    const timeRange = getSafeTimeRange(editedSegment)

    const handleWordChange = (index: number, updates: Partial<Word>) => {
        const newWords = [...editedSegment.words]
        newWords[index] = {
            ...newWords[index],
            ...updates
        }
        updateSegment(newWords)
    }

    const handleAddWord = (index?: number) => {
        const newWords = [...editedSegment.words]
        let newWord: Word

        if (index === undefined) {
            // Add at end
            const lastWord = newWords[newWords.length - 1]
            const lastEndTime = lastWord.end_time ?? 0
            newWord = {
                id: nanoid(),
                text: '',
                start_time: lastEndTime,
                end_time: lastEndTime + 0.5,
                confidence: 1.0
            }
            newWords.push(newWord)
        } else {
            // Add between words
            const prevWord = newWords[index]
            const nextWord = newWords[index + 1]
            const midTime = prevWord ?
                (nextWord ?
                    ((prevWord.end_time ?? 0) + (nextWord.start_time ?? 0)) / 2 :
                    (prevWord.end_time ?? 0) + 0.5
                ) :
                (nextWord ? (nextWord.start_time ?? 0) - 0.5 : 0)

            newWord = {
                id: nanoid(),
                text: '',
                start_time: midTime - 0.25,
                end_time: midTime + 0.25,
                confidence: 1.0
            }
            newWords.splice(index + 1, 0, newWord)
        }

        updateSegment(newWords)
    }

    const handleSplitWord = (index: number) => {
        const word = editedSegment.words[index]
        const startTime = word.start_time ?? 0
        const endTime = word.end_time ?? startTime + 0.5
        const totalDuration = endTime - startTime

        // Split on any number of spaces and filter out empty strings
        const words = word.text.split(/\s+/).filter(w => w.length > 0)

        if (words.length <= 1) {
            // If no spaces found, split the word in half as before
            const firstHalf = word.text.slice(0, Math.ceil(word.text.length / 2))
            const secondHalf = word.text.slice(Math.ceil(word.text.length / 2))
            words[0] = firstHalf
            words[1] = secondHalf
        }

        // Calculate time per word
        const timePerWord = totalDuration / words.length

        // Create new word objects with evenly distributed times
        const newWords = words.map((text, i) => ({
            id: nanoid(),
            text,
            start_time: startTime + (i * timePerWord),
            end_time: startTime + ((i + 1) * timePerWord),
            confidence: 1.0
        }))

        // Replace the original word with the new words
        const allWords = [...editedSegment.words]
        allWords.splice(index, 1, ...newWords)

        updateSegment(allWords)
    }

    const handleMergeWords = (index: number) => {
        if (index >= editedSegment.words.length - 1) return

        const word1 = editedSegment.words[index]
        const word2 = editedSegment.words[index + 1]
        const newWords = [...editedSegment.words]

        newWords.splice(index, 2, {
            id: nanoid(),
            text: `${word1.text} ${word2.text}`.trim(),
            start_time: word1.start_time ?? null,
            end_time: word2.end_time ?? null,
            confidence: 1.0
        })

        updateSegment(newWords)
    }

    const handleRemoveWord = (index: number) => {
        const newWords = editedSegment.words.filter((_, i) => i !== index)
        updateSegment(newWords)
    }

    const handleReset = () => {
        setEditedSegment(JSON.parse(JSON.stringify(originalSegment)))
    }

    const handleRevertToOriginal = () => {
        if (originalTranscribedSegment) {
            setEditedSegment(JSON.parse(JSON.stringify(originalTranscribedSegment)))
        }
    }

    const handleSave = () => {
        if (editedSegment) {
            console.log('EditModal - Saving segment:', {
                segmentIndex,
                originalText: segment?.text,
                editedText: editedSegment.text,
                wordCount: editedSegment.words.length,
                timeRange: `${editedSegment.start_time?.toFixed(4) ?? 'N/A'} - ${editedSegment.end_time?.toFixed(4) ?? 'N/A'}`
            })
            onSave(editedSegment)
            onClose()
        }
    }

    const handleDelete = () => {
        if (segmentIndex !== null) {
            onDelete?.(segmentIndex)
            onClose()
        }
    }

    const handleSplitSegment = (wordIndex: number) => {
        if (segmentIndex !== null && editedSegment) {
            handleSave()  // Save current changes first
            onSplitSegment?.(segmentIndex, wordIndex)
        }
    }

    const handleMergeSegment = (mergeWithNext: boolean) => {
        if (segmentIndex !== null && editedSegment) {
            handleSave()  // Save current changes first
            onMergeSegment?.(segmentIndex, mergeWithNext)
            onClose()
        }
    }

    // Handle play/stop button click
    const handlePlayButtonClick = () => {
        if (!segment?.start_time || !onPlaySegment) return

        if (isPlaying) {
            // Stop playback
            if (window.toggleAudioPlayback) {
                window.toggleAudioPlayback()
            }
        } else {
            // Start playback
            onPlaySegment(segment.start_time)
        }
    }

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="md"
            fullWidth
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSave()
                }
            }}
            PaperProps={{
                sx: {
                    height: '90vh',
                    margin: '5vh 0'
                }
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    Edit {isGlobal ? 'All Words' : `Segment ${segmentIndex}`}
                    {segment?.start_time !== null && onPlaySegment && (
                        <IconButton
                            size="small"
                            onClick={handlePlayButtonClick}
                            sx={{ padding: '4px' }}
                        >
                            {isPlaying ? (
                                <StopIcon />
                            ) : (
                                <PlayCircleOutlineIcon />
                            )}
                        </IconButton>
                    )}
                </Box>
                <IconButton onClick={onClose} sx={{ ml: 'auto' }}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>

            <DialogContent
                dividers
                sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    flexGrow: 1,
                    overflow: 'hidden'
                }}
            >
                <EditTimelineSection
                    words={editedSegment.words}
                    startTime={timeRange.start}
                    endTime={timeRange.end}
                    originalStartTime={originalSegment.start_time}
                    originalEndTime={originalSegment.end_time}
                    currentStartTime={editedSegment.start_time}
                    currentEndTime={editedSegment.end_time}
                    currentTime={currentTime}
                    isManualSyncing={isManualSyncing}
                    syncWordIndex={syncWordIndex}
                    isSpacebarPressed={isSpacebarPressed}
                    onWordUpdate={handleWordChange}
                    onPlaySegment={onPlaySegment}
                    startManualSync={startManualSync}
                />

                <EditWordList
                    words={editedSegment.words}
                    onWordUpdate={handleWordChange}
                    onSplitWord={handleSplitWord}
                    onMergeWords={handleMergeWords}
                    onAddWord={handleAddWord}
                    onRemoveWord={handleRemoveWord}
                    onSplitSegment={handleSplitSegment}
                    onAddSegment={onAddSegment}
                    onMergeSegment={handleMergeSegment}
                    currentTime={currentTime}
                    isGlobal={isGlobal}
                />
            </DialogContent>

            <DialogActions>
                <EditActionBar
                    onReset={handleReset}
                    onRevertToOriginal={handleRevertToOriginal}
                    onDelete={handleDelete}
                    onClose={handleClose}
                    onSave={handleSave}
                    editedSegment={editedSegment}
                    originalTranscribedSegment={originalTranscribedSegment}
                    isGlobal={isGlobal}
                />
            </DialogActions>
        </Dialog>
    )
} 