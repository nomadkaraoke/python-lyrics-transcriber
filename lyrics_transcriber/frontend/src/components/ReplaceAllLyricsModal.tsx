import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
    Button,
    Typography,
    TextField,
    Paper,
    Divider
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import ContentPasteIcon from '@mui/icons-material/ContentPaste'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import { LyricsSegment, Word } from '../types'
import { useState, useEffect, useCallback, useMemo, useRef, memo } from 'react'
import { nanoid } from 'nanoid'
import useManualSync from '../hooks/useManualSync'
import EditTimelineSection from './EditTimelineSection'
import EditActionBar from './EditActionBar'

// Augment window type for audio functions
declare global {
    interface Window {
        getAudioDuration?: () => number;
        toggleAudioPlayback?: () => void;
        isAudioPlaying?: boolean;
    }
}

interface ReplaceAllLyricsModalProps {
    open: boolean
    onClose: () => void
    onSave: (newSegments: LyricsSegment[]) => void
    onPlaySegment?: (startTime: number) => void
    currentTime?: number
    setModalSpacebarHandler: (handler: (() => (e: KeyboardEvent) => void) | undefined) => void
}

export default function ReplaceAllLyricsModal({
    open,
    onClose,
    onSave,
    onPlaySegment,
    currentTime = 0,
    setModalSpacebarHandler
}: ReplaceAllLyricsModalProps) {
    const [inputText, setInputText] = useState('')
    const [isReplaced, setIsReplaced] = useState(false)
    const [globalSegment, setGlobalSegment] = useState<LyricsSegment | null>(null)
    const [originalSegments, setOriginalSegments] = useState<LyricsSegment[]>([])
    const [currentSegments, setCurrentSegments] = useState<LyricsSegment[]>([])

    // Get the real audio duration, with fallback
    const getAudioDuration = useCallback(() => {
        if (window.getAudioDuration) {
            const duration = window.getAudioDuration()
            return duration > 0 ? duration : 600 // Use real duration or 10 min fallback
        }
        return 600 // 10 minute fallback if audio not loaded
    }, [])

    // Parse the input text to get line and word counts
    const parseInfo = useMemo(() => {
        if (!inputText.trim()) return { lines: 0, words: 0 }
        
        const lines = inputText.trim().split('\n').filter(line => line.trim().length > 0)
        const totalWords = lines.reduce((count, line) => {
            return count + line.trim().split(/\s+/).length
        }, 0)
        
        return { lines: lines.length, words: totalWords }
    }, [inputText])

    // Process the input text into segments and words
    const processLyrics = useCallback(() => {
        if (!inputText.trim()) return

        const lines = inputText.trim().split('\n').filter(line => line.trim().length > 0)
        const newSegments: LyricsSegment[] = []
        const allWords: Word[] = []

        lines.forEach((line) => {
            const words = line.trim().split(/\s+/).filter(word => word.length > 0)
            const segmentWords: Word[] = []

            words.forEach((wordText) => {
                const word: Word = {
                    id: nanoid(),
                    text: wordText,
                    start_time: null,
                    end_time: null,
                    confidence: 1.0,
                    created_during_correction: true
                }
                segmentWords.push(word)
                allWords.push(word)
            })

            const segment: LyricsSegment = {
                id: nanoid(),
                text: line.trim(),
                words: segmentWords,
                start_time: null,
                end_time: null
            }

            newSegments.push(segment)
        })

        // Create a global segment with all words for manual sync
        // Set a very large end time to ensure manual sync doesn't stop prematurely
        const audioDuration = getAudioDuration()
        const endTime = Math.max(audioDuration, 3600) // At least 1 hour to prevent auto-stop
        
        console.log('ReplaceAllLyricsModal - Creating global segment', {
            audioDuration,
            endTime,
            wordCount: allWords.length
        })
        
        const globalSegment: LyricsSegment = {
            id: 'global-replacement',
            text: allWords.map(w => w.text).join(' '),
            words: allWords,
            start_time: 0,
            end_time: endTime
        }

        setCurrentSegments(newSegments)
        setOriginalSegments(JSON.parse(JSON.stringify(newSegments)))
        setGlobalSegment(globalSegment)
        setIsReplaced(true)
    }, [inputText, getAudioDuration])

    // Handle paste from clipboard
    const handlePasteFromClipboard = useCallback(async () => {
        try {
            const text = await navigator.clipboard.readText()
            setInputText(text)
        } catch (error) {
            console.error('Failed to read from clipboard:', error)
            alert('Failed to read from clipboard. Please paste manually.')
        }
    }, [])

    // Update segment when words change during manual sync
    const updateSegment = useCallback((newWords: Word[]) => {
        if (!globalSegment) return

        const validStartTimes = newWords.map(w => w.start_time).filter((t): t is number => t !== null)
        const validEndTimes = newWords.map(w => w.end_time).filter((t): t is number => t !== null)

        const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
        const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

        const updatedGlobalSegment = {
            ...globalSegment,
            words: newWords,
            text: newWords.map(w => w.text).join(' '),
            start_time: segmentStartTime,
            end_time: segmentEndTime
        }

        // Batch state updates to prevent multiple re-renders
        setGlobalSegment(updatedGlobalSegment)

        // Update individual segment timing as words get synced - but only calculate when needed
        const updatedSegments = currentSegments.map(segment => {
            // Find words that belong to this segment and have been timed
            const segmentWordsWithTiming = segment.words.map(segmentWord => {
                const globalWord = newWords.find(w => w.id === segmentWord.id)
                return globalWord || segmentWord
            })

            // Calculate segment timing if all words have timing
            const wordsWithTiming = segmentWordsWithTiming.filter(w => 
                w.start_time !== null && w.end_time !== null
            )

            if (wordsWithTiming.length === segmentWordsWithTiming.length && wordsWithTiming.length > 0) {
                // All words in this segment have timing - update segment timing
                const segmentStart = Math.min(...wordsWithTiming.map(w => w.start_time!))
                const segmentEnd = Math.max(...wordsWithTiming.map(w => w.end_time!))

                return {
                    ...segment,
                    words: segmentWordsWithTiming,
                    start_time: segmentStart,
                    end_time: segmentEnd
                }
            } else {
                // Some words still don't have timing - just update the words
                return {
                    ...segment,
                    words: segmentWordsWithTiming
                }
            }
        })

        setCurrentSegments(updatedSegments)
    }, [globalSegment, currentSegments])

    // Use the manual sync hook
    const {
        isManualSyncing,
        isPaused,
        syncWordIndex,
        startManualSync,
        pauseManualSync,
        resumeManualSync,
        cleanupManualSync,
        handleSpacebar,
        isSpacebarPressed
    } = useManualSync({
        editedSegment: globalSegment,
        currentTime,
        onPlaySegment,
        updateSegment
    })

    // Handle manual word updates (drag/resize in timeline)
    const handleWordUpdate = useCallback((wordIndex: number, updates: Partial<Word>) => {
        if (!globalSegment) return

        // Only allow manual adjustments when manual sync is paused or not active
        if (isManualSyncing && !isPaused) {
            console.log('ReplaceAllLyricsModal - Ignoring word update during active manual sync')
            return
        }

        console.log('ReplaceAllLyricsModal - Manual word update', {
            wordIndex,
            wordText: globalSegment.words[wordIndex]?.text,
            updates,
            isManualSyncing,
            isPaused
        })

        // Update the word in the global segment
        const newWords = [...globalSegment.words]
        newWords[wordIndex] = {
            ...newWords[wordIndex],
            ...updates
        }

        // Update the global segment through the existing updateSegment function
        updateSegment(newWords)
    }, [globalSegment, updateSegment, isManualSyncing, isPaused])

    // Handle un-syncing a word (right-click context menu)
    const handleUnsyncWord = useCallback((wordIndex: number) => {
        if (!globalSegment) return

        console.log('ReplaceAllLyricsModal - Un-syncing word', {
            wordIndex,
            wordText: globalSegment.words[wordIndex]?.text
        })

        // Update the word to remove timing
        const newWords = [...globalSegment.words]
        newWords[wordIndex] = {
            ...newWords[wordIndex],
            start_time: null,
            end_time: null
        }

        // Update the global segment through the existing updateSegment function
        updateSegment(newWords)
    }, [globalSegment, updateSegment])

    // Handle modal close
    const handleClose = useCallback(() => {
        cleanupManualSync()
        setInputText('')
        setIsReplaced(false)
        setGlobalSegment(null)
        setOriginalSegments([])
        setCurrentSegments([])
        onClose()
    }, [onClose, cleanupManualSync])

    // Handle save
    const handleSave = useCallback(() => {
        if (!globalSegment || !currentSegments.length) return

        // Distribute the timed words back to their original segments
        const finalSegments: LyricsSegment[] = []
        let wordIndex = 0

        currentSegments.forEach((segment) => {
            const originalWordCount = segment.words.length
            const segmentWords = globalSegment.words.slice(wordIndex, wordIndex + originalWordCount)
            wordIndex += originalWordCount

            if (segmentWords.length > 0) {
                // Recalculate segment start and end times
                const validStartTimes = segmentWords.map(w => w.start_time).filter((t): t is number => t !== null)
                const validEndTimes = segmentWords.map(w => w.end_time).filter((t): t is number => t !== null)

                const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
                const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

                finalSegments.push({
                    ...segment,
                    words: segmentWords,
                    text: segmentWords.map(w => w.text).join(' '),
                    start_time: segmentStartTime,
                    end_time: segmentEndTime
                })
            }
        })

        console.log('ReplaceAllLyricsModal - Saving new segments:', {
            originalSegmentCount: currentSegments.length,
            finalSegmentCount: finalSegments.length,
            totalWords: finalSegments.reduce((count, seg) => count + seg.words.length, 0)
        })

        onSave(finalSegments)
        handleClose()
    }, [globalSegment, currentSegments, onSave, handleClose])

    // Handle reset
    const handleReset = useCallback(() => {
        if (!originalSegments.length) return

        console.log('ReplaceAllLyricsModal - Resetting to original state')
        
        // Reset all words to have null timing (ready for fresh manual sync)
        const resetWords = originalSegments.flatMap(segment => 
            segment.words.map(word => ({
                ...word,
                start_time: null,
                end_time: null
            }))
        )
        
        const audioDuration = getAudioDuration()
        const resetGlobalSegment: LyricsSegment = {
            id: 'global-replacement',
            text: resetWords.map(w => w.text).join(' '),
            words: resetWords,
            start_time: 0,
            end_time: Math.max(audioDuration, 3600) // At least 1 hour to prevent auto-stop
        }

        // Also reset the current segments to have null timing
        const resetCurrentSegments = originalSegments.map(segment => ({
            ...segment,
            words: segment.words.map(word => ({
                ...word,
                start_time: null,
                end_time: null
            })),
            start_time: null,
            end_time: null
        }))

        setGlobalSegment(resetGlobalSegment)
        setCurrentSegments(resetCurrentSegments)
    }, [originalSegments, getAudioDuration])

    // Keep a ref to the current spacebar handler to avoid closure issues
    const spacebarHandlerRef = useRef(handleSpacebar)
    spacebarHandlerRef.current = handleSpacebar

    // Update the spacebar handler when modal state changes
    useEffect(() => {
        if (open && isReplaced) {
            console.log('ReplaceAllLyricsModal - Setting up spacebar handler')

            const handleKeyEvent = (e: KeyboardEvent) => {
                if (e.code === 'Space') {
                    console.log('ReplaceAllLyricsModal - Spacebar captured in modal')
                    e.preventDefault()
                    e.stopPropagation()
                    // Use the ref to get the current handler
                    spacebarHandlerRef.current(e)
                }
            }

            setModalSpacebarHandler(() => handleKeyEvent)

            return () => {
                if (!open) {
                    console.log('ReplaceAllLyricsModal - Clearing spacebar handler')
                    setModalSpacebarHandler(undefined)
                }
            }
        } else if (open) {
            // Clear handler when not in replaced state
            setModalSpacebarHandler(undefined)
        }
    }, [open, isReplaced, setModalSpacebarHandler])

    // Memoize timeline range to prevent recalculation
    const timeRange = useMemo(() => {
        const audioDuration = getAudioDuration()
        // Always use full song duration for replace-all mode
        return { start: 0, end: audioDuration }
    }, [getAudioDuration])

    // Memoize the segment progress props to prevent unnecessary re-renders
    const segmentProgressProps = useMemo(() => ({
        currentSegments,
        globalSegment,
        syncWordIndex
    }), [currentSegments, globalSegment, syncWordIndex])

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth={false}
            fullWidth={true}
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && isReplaced) {
                    e.preventDefault()
                    handleSave()
                }
            }}
            PaperProps={{
                sx: {
                    height: '90vh',
                    margin: '5vh 2vh',
                    maxWidth: 'calc(100vw - 4vh)',
                    width: 'calc(100vw - 4vh)'
                }
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1 }}>
                    Replace All Lyrics
                </Box>
                <IconButton onClick={handleClose} sx={{ ml: 'auto' }}>
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
                {!isReplaced ? (
                    // Step 1: Input new lyrics
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
                        <Typography variant="h6" gutterBottom>
                            Paste your new lyrics below:
                        </Typography>
                        
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                            Each line will become a separate segment. Words will be separated by spaces.
                        </Typography>

                        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                            <Button
                                variant="outlined"
                                onClick={handlePasteFromClipboard}
                                startIcon={<ContentPasteIcon />}
                                size="small"
                            >
                                Paste from Clipboard
                            </Button>
                            <Typography variant="body2" sx={{ 
                                alignSelf: 'center', 
                                color: 'text.secondary',
                                fontWeight: 'medium'
                            }}>
                                {parseInfo.lines} lines, {parseInfo.words} words
                            </Typography>
                        </Box>

                        <TextField
                            multiline
                            rows={15}
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            placeholder="Paste your lyrics here...&#10;Each line will become a segment&#10;Words will be separated by spaces"
                            sx={{ 
                                flexGrow: 1,
                                '& .MuiInputBase-root': {
                                    height: '100%',
                                    alignItems: 'flex-start'
                                }
                            }}
                        />

                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                            <Button
                                variant="contained"
                                onClick={processLyrics}
                                disabled={!inputText.trim()}
                                startIcon={<AutoFixHighIcon />}
                            >
                                Replace All Lyrics
                            </Button>
                        </Box>
                    </Box>
                ) : (
                    // Step 2: Manual sync interface
                    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 2 }}>
                        <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                            <Typography variant="h6" gutterBottom>
                                Lyrics Replaced Successfully
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Created {currentSegments.length} segments with {globalSegment?.words.length} words total.
                                Use Manual Sync to set timing for all words.
                            </Typography>
                        </Paper>

                        <Divider />

                        {globalSegment && (
                            <Box sx={{ display: 'flex', gap: 2, flexGrow: 1, minHeight: 0 }}>
                                {/* Timeline Section */}
                                <Box sx={{ flex: 2, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                                    <EditTimelineSection
                                        words={globalSegment.words}
                                        startTime={timeRange.start}
                                        endTime={timeRange.end}
                                        originalStartTime={0}
                                        originalEndTime={getAudioDuration()}
                                        currentStartTime={globalSegment.start_time}
                                        currentEndTime={globalSegment.end_time}
                                        currentTime={currentTime}
                                        isManualSyncing={isManualSyncing}
                                        syncWordIndex={syncWordIndex}
                                        isSpacebarPressed={isSpacebarPressed}
                                        onWordUpdate={handleWordUpdate}
                                        onUnsyncWord={handleUnsyncWord}
                                        onPlaySegment={onPlaySegment}
                                        onStopAudio={() => {
                                            // Stop audio playback using global function
                                            if (window.toggleAudioPlayback && window.isAudioPlaying) {
                                                window.toggleAudioPlayback()
                                            }
                                        }}
                                        startManualSync={startManualSync}
                                        pauseManualSync={pauseManualSync}
                                        resumeManualSync={resumeManualSync}
                                        isPaused={isPaused}
                                        isGlobal={true}
                                        defaultZoomLevel={10} // Show 10 seconds by default
                                        isReplaceAllMode={true} // Prevent zoom changes during sync
                                    />
                                </Box>

                                {/* Segment Progress Section */}
                                <SegmentProgressPanel
                                    currentSegments={segmentProgressProps.currentSegments}
                                    globalSegment={segmentProgressProps.globalSegment}
                                    syncWordIndex={segmentProgressProps.syncWordIndex}
                                />
                            </Box>
                        )}
                    </Box>
                )}
            </DialogContent>

            <DialogActions>
                {isReplaced && (
                    <EditActionBar
                        onReset={handleReset}
                        onClose={handleClose}
                        onSave={handleSave}
                        editedSegment={globalSegment}
                        isGlobal={true}
                    />
                )}
            </DialogActions>
        </Dialog>
    )
} 

// Memoized Segment Progress Item to prevent unnecessary re-renders
const SegmentProgressItem = memo(({ 
    segment, 
    index, 
    isActive
}: {
    segment: LyricsSegment
    index: number
    isActive: boolean
}) => {
    const wordsWithTiming = segment.words.filter(w => 
        w.start_time !== null && w.end_time !== null
    ).length
    const totalWords = segment.words.length
    const isComplete = wordsWithTiming === totalWords

    return (
        <Paper 
            key={segment.id}
            ref={isActive ? (el) => {
                // Auto-scroll to active segment
                if (el) {
                    el.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    })
                }
            } : undefined}
            sx={{ 
                p: 1, 
                mb: 1, 
                bgcolor: isActive ? 'primary.light' : 
                        isComplete ? 'success.light' : 'background.paper',
                border: isActive ? 2 : 1,
                borderColor: isActive ? 'primary.main' : 'divider'
            }}
        >
            <Typography 
                variant="body2" 
                sx={{ 
                    fontWeight: isActive ? 'bold' : 'normal',
                    mb: 0.5 
                }}
            >
                Segment {index + 1}: {segment.text.slice(0, 50)}
                {segment.text.length > 50 ? '...' : ''}
            </Typography>
            <Typography variant="caption" color="text.secondary">
                {wordsWithTiming}/{totalWords} words synced
                {isComplete && segment.start_time !== null && segment.end_time !== null && (
                    <>
                        <br />
                        {segment.start_time.toFixed(2)}s - {segment.end_time.toFixed(2)}s
                    </>
                )}
            </Typography>
        </Paper>
    )
})

// Memoized Segment Progress Panel
const SegmentProgressPanel = memo(({ 
    currentSegments, 
    globalSegment, 
    syncWordIndex 
}: {
    currentSegments: LyricsSegment[]
    globalSegment: LyricsSegment | null
    syncWordIndex: number
}) => {
    return (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <Typography variant="h6" gutterBottom>
                Segment Progress
            </Typography>
            <Box sx={{ 
                overflow: 'auto', 
                flexGrow: 1,
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                p: 1
            }}>
                {currentSegments.map((segment, index) => {
                    const isActive = Boolean(
                        globalSegment && 
                        syncWordIndex >= 0 && 
                        syncWordIndex < globalSegment.words.length &&
                        globalSegment.words[syncWordIndex] && 
                        segment.words.some(w => w.id === globalSegment.words[syncWordIndex].id)
                    )

                    return (
                        <SegmentProgressItem
                            key={segment.id}
                            segment={segment}
                            index={index}
                            isActive={isActive}
                        />
                    )
                })}
            </Box>
        </Box>
    )
}) 