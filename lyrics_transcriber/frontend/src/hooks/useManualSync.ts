import { useState, useCallback, useEffect, useRef } from 'react'
import { LyricsSegment, Word } from '../types'

interface UseManualSyncProps {
    editedSegment: LyricsSegment | null
    currentTime: number
    onPlaySegment?: (startTime: number) => void
    updateSegment: (words: Word[]) => void
}

// Constants for tap detection
const TAP_THRESHOLD_MS = 200 // If spacebar is pressed for less than this time, it's considered a tap
const DEFAULT_WORD_DURATION = 0.5 // Default duration in seconds when tapping (500ms)
const OVERLAP_BUFFER = 0.01 // Buffer to prevent word overlap (10ms)

export default function useManualSync({
    editedSegment,
    currentTime,
    onPlaySegment,
    updateSegment
}: UseManualSyncProps) {
    const [isManualSyncing, setIsManualSyncing] = useState(false)
    const [isPaused, setIsPaused] = useState(false)
    const [syncWordIndex, setSyncWordIndex] = useState<number>(-1)
    const currentTimeRef = useRef(currentTime)
    const [isSpacebarPressed, setIsSpacebarPressed] = useState(false)
    const wordStartTimeRef = useRef<number | null>(null)
    const wordsRef = useRef<Word[]>([])
    const spacebarPressTimeRef = useRef<number | null>(null)
    
    // Use ref to track if we need to update segment to avoid calling it too frequently
    const needsSegmentUpdateRef = useRef(false)

    // Keep currentTimeRef up to date
    useEffect(() => {
        currentTimeRef.current = currentTime
    }, [currentTime])

    // Keep wordsRef up to date
    useEffect(() => {
        if (editedSegment) {
            wordsRef.current = [...editedSegment.words]
        }
    }, [editedSegment])

    // Debounced segment update to batch multiple word changes
    useEffect(() => {
        if (needsSegmentUpdateRef.current) {
            needsSegmentUpdateRef.current = false
            updateSegment(wordsRef.current)
        }
    }, [updateSegment, syncWordIndex]) // Only update when syncWordIndex changes

    const cleanupManualSync = useCallback(() => {
        setIsManualSyncing(false)
        setIsPaused(false)
        setSyncWordIndex(-1)
        setIsSpacebarPressed(false)
        wordStartTimeRef.current = null
        spacebarPressTimeRef.current = null
        needsSegmentUpdateRef.current = false
        
        // Stop audio playback when cleaning up manual sync
        if (window.toggleAudioPlayback && window.isAudioPlaying) {
            window.toggleAudioPlayback()
        }
    }, [])

    const pauseManualSync = useCallback(() => {
        if (isManualSyncing && !isPaused) {
            console.log('useManualSync - Pausing manual sync')
            setIsPaused(true)
            // Pause audio playback
            if (window.toggleAudioPlayback && window.isAudioPlaying) {
                window.toggleAudioPlayback()
            }
        }
    }, [isManualSyncing, isPaused])

    const resumeManualSync = useCallback(() => {
        if (isManualSyncing && isPaused) {
            console.log('useManualSync - Resuming manual sync')
            setIsPaused(false)
            
            // Find the first unsynced word and resume from there
            if (editedSegment) {
                const firstUnsyncedIndex = editedSegment.words.findIndex(word => 
                    word.start_time === null || word.end_time === null
                )
                
                if (firstUnsyncedIndex !== -1 && firstUnsyncedIndex !== syncWordIndex) {
                    console.log('useManualSync - Resuming from first unsynced word', {
                        previousIndex: syncWordIndex,
                        newIndex: firstUnsyncedIndex,
                        wordText: editedSegment.words[firstUnsyncedIndex]?.text
                    })
                    setSyncWordIndex(firstUnsyncedIndex)
                } else {
                    console.log('useManualSync - Resuming from current position', { syncWordIndex })
                }
            }
            
            // Resume audio playback if we have an onPlaySegment function
            if (onPlaySegment && currentTimeRef.current !== undefined) {
                onPlaySegment(currentTimeRef.current)
            }
        }
    }, [isManualSyncing, isPaused, onPlaySegment, editedSegment, syncWordIndex])

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.code !== 'Space') return
        
        console.log('useManualSync - Spacebar pressed down', {
            isManualSyncing,
            hasEditedSegment: !!editedSegment,
            syncWordIndex,
            currentTime: currentTimeRef.current
        })

        e.preventDefault()
        e.stopPropagation()

        if (isManualSyncing && editedSegment && !isSpacebarPressed && !isPaused) {
            setIsSpacebarPressed(true)
            
            // Record the start time of the current word
            wordStartTimeRef.current = currentTimeRef.current
            
            // Record when the spacebar was pressed (for tap detection)
            spacebarPressTimeRef.current = Date.now()
            
            // Update the word's start time immediately
            if (syncWordIndex < editedSegment.words.length) {
                const newWords = [...wordsRef.current]
                const currentWord = newWords[syncWordIndex]
                const currentStartTime = currentTimeRef.current
                
                // Set the start time for the current word
                currentWord.start_time = currentStartTime
                
                // Handle the end time of the previous word (if it exists)
                if (syncWordIndex > 0) {
                    const previousWord = newWords[syncWordIndex - 1]
                    if (previousWord.start_time !== null) {
                        const timeSincePreviousStart = currentStartTime - previousWord.start_time
                        
                        // Only adjust previous word's end time if:
                        // 1. It doesn't have an end time set yet (was never released), OR
                        // 2. The current start would overlap with existing end time
                        const needsAdjustment = previousWord.end_time === null || 
                                              (previousWord.end_time !== null && previousWord.end_time > currentStartTime)
                        
                        if (needsAdjustment) {
                            if (timeSincePreviousStart > 1.0) {
                                // Gap of over 1 second - set previous word's end time to 500ms after its start
                                previousWord.end_time = previousWord.start_time + 0.5
                                console.log('useManualSync - Gap detected, setting previous word end time to +500ms', {
                                    previousWordIndex: syncWordIndex - 1,
                                    previousWordText: previousWord.text,
                                    previousStartTime: previousWord.start_time,
                                    previousEndTime: previousWord.end_time,
                                    gap: timeSincePreviousStart.toFixed(2) + 's',
                                    reason: 'gap > 1s'
                                })
                            } else {
                                // Normal flow - set previous word's end time to current word's start time minus 5ms
                                previousWord.end_time = currentStartTime - 0.005
                                console.log('useManualSync - Setting previous word end time to current start - 5ms', {
                                    previousWordIndex: syncWordIndex - 1,
                                    previousWordText: previousWord.text,
                                    previousEndTime: previousWord.end_time,
                                    currentStartTime: currentStartTime,
                                    gap: timeSincePreviousStart.toFixed(2) + 's',
                                    reason: 'normal flow'
                                })
                            }
                        } else {
                            console.log('useManualSync - Preserving previous word timing (manually set)', {
                                previousWordIndex: syncWordIndex - 1,
                                previousWordText: previousWord.text,
                                previousStartTime: previousWord.start_time,
                                previousEndTime: previousWord.end_time,
                                preservedDuration: previousWord.end_time !== null ? 
                                    (previousWord.end_time - previousWord.start_time).toFixed(2) + 's' : 'N/A',
                                reason: 'already timed correctly'
                            })
                        }
                    }
                }
                
                console.log('useManualSync - Recording word start time', {
                    wordIndex: syncWordIndex,
                    wordText: currentWord?.text,
                    time: currentStartTime
                })
                
                // Update our ref
                wordsRef.current = newWords
                
                // Mark that we need to update the segment
                needsSegmentUpdateRef.current = true
            }
        } else if (!isManualSyncing && editedSegment && onPlaySegment) {
            console.log('useManualSync - Handling segment playback', {
                editedSegmentId: editedSegment.id,
                isGlobalReplacement: editedSegment.id === 'global-replacement'
            })
            
            // For global replacement segments, don't handle general playback
            // since we want the user to use Manual Sync instead
            if (editedSegment.id === 'global-replacement') {
                console.log('useManualSync - Ignoring playback for global replacement - please use Manual Sync')
                return
            }
            
            // Toggle segment playback when not in manual sync mode
            const startTime = editedSegment.start_time ?? 0
            const endTime = editedSegment.end_time ?? 0

            if (currentTimeRef.current >= startTime && currentTimeRef.current <= endTime) {
                if (window.toggleAudioPlayback) {
                    window.toggleAudioPlayback()
                }
            } else {
                onPlaySegment(startTime)
            }
        }
    }, [isManualSyncing, editedSegment, syncWordIndex, onPlaySegment, isSpacebarPressed, isPaused])

    const handleKeyUp = useCallback((e: KeyboardEvent) => {
        if (e.code !== 'Space') return
        
        console.log('useManualSync - Spacebar released', {
            isManualSyncing,
            hasEditedSegment: !!editedSegment,
            syncWordIndex,
            currentTime: currentTimeRef.current,
            wordStartTime: wordStartTimeRef.current
        })

        e.preventDefault()
        e.stopPropagation()

        if (isManualSyncing && editedSegment && isSpacebarPressed && !isPaused) {
            const currentWord = syncWordIndex < editedSegment.words.length ? editedSegment.words[syncWordIndex] : null
            const pressDuration = spacebarPressTimeRef.current ? Date.now() - spacebarPressTimeRef.current : 0
            const isTap = pressDuration < TAP_THRESHOLD_MS
            
            console.log('useManualSync - Recording word end time', {
                wordIndex: syncWordIndex,
                wordText: currentWord?.text,
                startTime: wordStartTimeRef.current,
                endTime: currentTimeRef.current,
                pressDuration: `${pressDuration}ms`,
                isTap,
                tapThreshold: TAP_THRESHOLD_MS,
                duration: currentWord ? (currentTimeRef.current - (wordStartTimeRef.current || 0)).toFixed(2) + 's' : 'N/A'
            })
            
            setIsSpacebarPressed(false)
            
            if (syncWordIndex < editedSegment.words.length) {
                const newWords = [...wordsRef.current]
                const currentWord = newWords[syncWordIndex]
                
                // Set the end time for the current word based on whether it was a tap or hold
                if (isTap) {
                    // For a tap, set a default duration
                    const defaultEndTime = (wordStartTimeRef.current || currentTimeRef.current) + DEFAULT_WORD_DURATION
                    currentWord.end_time = defaultEndTime
                    console.log('useManualSync - Tap detected, setting default duration', {
                        wordText: currentWord.text,
                        startTime: wordStartTimeRef.current,
                        defaultEndTime,
                        duration: DEFAULT_WORD_DURATION
                    })
                } else {
                    // For a hold, use the current time as the end time
                    currentWord.end_time = currentTimeRef.current
                    console.log('useManualSync - Hold detected, using actual timing', {
                        wordText: currentWord.text,
                        startTime: wordStartTimeRef.current,
                        endTime: currentTimeRef.current,
                        actualDuration: (currentTimeRef.current - (wordStartTimeRef.current || 0)).toFixed(2) + 's'
                    })
                }
                
                // Update our ref
                wordsRef.current = newWords
                
                // Move to the next word
                if (syncWordIndex === editedSegment.words.length - 1) {
                    // If this was the last word, finish manual sync
                    console.log('useManualSync - Completed manual sync for all words')
                    setIsManualSyncing(false)
                    setSyncWordIndex(-1)
                    wordStartTimeRef.current = null
                    spacebarPressTimeRef.current = null
                } else {
                    // Otherwise, move to the next word
                    const nextWord = editedSegment.words[syncWordIndex + 1]
                    console.log('useManualSync - Moving to next word', {
                        nextWordIndex: syncWordIndex + 1,
                        nextWordText: nextWord?.text
                    })
                    setSyncWordIndex(syncWordIndex + 1)
                }
                
                // Mark that we need to update the segment
                needsSegmentUpdateRef.current = true
            }
        }
    }, [isManualSyncing, editedSegment, syncWordIndex, isSpacebarPressed, isPaused])

    // Add a handler for when the next word starts to adjust previous word's end time if needed
    useEffect(() => {
        if (isManualSyncing && editedSegment && syncWordIndex > 0) {
            const newWords = [...wordsRef.current]
            const prevWord = newWords[syncWordIndex - 1]
            const currentWord = newWords[syncWordIndex]
            
            // If the previous word's end time overlaps with the current word's start time,
            // adjust the previous word's end time
            if (prevWord && currentWord && 
                prevWord.end_time !== null && currentWord.start_time !== null &&
                prevWord.end_time > currentWord.start_time) {
                
                console.log('useManualSync - Adjusting previous word end time to prevent overlap', {
                    prevWordIndex: syncWordIndex - 1,
                    prevWordText: prevWord.text,
                    prevWordEndTime: prevWord.end_time,
                    currentWordStartTime: currentWord.start_time,
                    newEndTime: currentWord.start_time - OVERLAP_BUFFER
                })
                
                prevWord.end_time = currentWord.start_time - OVERLAP_BUFFER
                
                // Update our ref
                wordsRef.current = newWords
                
                // Mark that we need to update the segment
                needsSegmentUpdateRef.current = true
            }
        }
    }, [syncWordIndex, isManualSyncing, editedSegment])

    // Combine the key handlers into a single function for external use
    const handleSpacebar = useCallback((e: KeyboardEvent) => {
        if (e.type === 'keydown') {
            handleKeyDown(e)
        } else if (e.type === 'keyup') {
            handleKeyUp(e)
        }
    }, [handleKeyDown, handleKeyUp])

    const startManualSync = useCallback(() => {
        if (isManualSyncing) {
            cleanupManualSync()
            return
        }

        if (!editedSegment || !onPlaySegment) return

        // Make sure we have the latest words
        wordsRef.current = [...editedSegment.words]
        
        // Find the first unsynced word to start from
        const firstUnsyncedIndex = editedSegment.words.findIndex(word => 
            word.start_time === null || word.end_time === null
        )
        
        const startIndex = firstUnsyncedIndex !== -1 ? firstUnsyncedIndex : 0
        
        console.log('useManualSync - Starting manual sync', {
            totalWords: editedSegment.words.length,
            startingFromIndex: startIndex,
            startingWord: editedSegment.words[startIndex]?.text
        })
        
        setIsManualSyncing(true)
        setSyncWordIndex(startIndex)
        setIsSpacebarPressed(false)
        wordStartTimeRef.current = null
        spacebarPressTimeRef.current = null
        needsSegmentUpdateRef.current = false
        // Start playing 3 seconds before segment start
        onPlaySegment((editedSegment.start_time ?? 0) - 3)
    }, [isManualSyncing, editedSegment, onPlaySegment, cleanupManualSync])

    // Auto-stop sync if we go past the end time (but not for global replacement segments)
    useEffect(() => {
        if (!editedSegment || !isManualSyncing) return

        // Don't auto-stop for global replacement segments - let user manually finish
        if (editedSegment.id === 'global-replacement') {
            console.log('useManualSync - Skipping auto-stop for global replacement segment')
            return
        }

        // Set up an interval to check if we should auto-stop
        const checkAutoStop = () => {
            const endTime = editedSegment.end_time ?? 0
            
            if (window.isAudioPlaying && currentTimeRef.current > endTime) {
                console.log('useManualSync - Auto-stopping: current time exceeded end time', {
                    currentTime: currentTimeRef.current,
                    endTime,
                    segmentId: editedSegment.id
                })
                window.toggleAudioPlayback?.()
                cleanupManualSync()
            }
        }

        // Check immediately and then every 100ms
        checkAutoStop()
        const intervalId = setInterval(checkAutoStop, 100)

        return () => {
            clearInterval(intervalId)
        }
    }, [isManualSyncing, editedSegment, cleanupManualSync])

    return {
        isManualSyncing,
        isPaused,
        syncWordIndex,
        startManualSync,
        pauseManualSync,
        resumeManualSync,
        cleanupManualSync,
        handleSpacebar,
        isSpacebarPressed
    }
} 