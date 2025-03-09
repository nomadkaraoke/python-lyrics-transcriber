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
const DEFAULT_WORD_DURATION = 1.0 // Default duration in seconds when tapping
const OVERLAP_BUFFER = 0.01 // Buffer to prevent word overlap (10ms)

export default function useManualSync({
    editedSegment,
    currentTime,
    onPlaySegment,
    updateSegment
}: UseManualSyncProps) {
    const [isManualSyncing, setIsManualSyncing] = useState(false)
    const [syncWordIndex, setSyncWordIndex] = useState<number>(-1)
    const currentTimeRef = useRef(currentTime)
    const [isSpacebarPressed, setIsSpacebarPressed] = useState(false)
    const wordStartTimeRef = useRef<number | null>(null)
    const wordsRef = useRef<Word[]>([])
    const spacebarPressTimeRef = useRef<number | null>(null)

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

    const cleanupManualSync = useCallback(() => {
        setIsManualSyncing(false)
        setSyncWordIndex(-1)
        setIsSpacebarPressed(false)
        wordStartTimeRef.current = null
        spacebarPressTimeRef.current = null
    }, [])

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

        if (isManualSyncing && editedSegment && !isSpacebarPressed) {
            const currentWord = syncWordIndex < editedSegment.words.length ? editedSegment.words[syncWordIndex] : null
            console.log('useManualSync - Recording word start time', {
                wordIndex: syncWordIndex,
                wordText: currentWord?.text,
                time: currentTimeRef.current
            })
            
            setIsSpacebarPressed(true)
            
            // Record the start time of the current word
            wordStartTimeRef.current = currentTimeRef.current
            
            // Record when the spacebar was pressed (for tap detection)
            spacebarPressTimeRef.current = Date.now()
            
            // Update the word's start time immediately
            if (syncWordIndex < editedSegment.words.length) {
                const newWords = [...wordsRef.current]
                const currentWord = newWords[syncWordIndex]
                
                // Set the start time for the current word
                currentWord.start_time = currentTimeRef.current
                
                // Update our ref
                wordsRef.current = newWords
                
                // Update the segment
                updateSegment(newWords)
            }
        } else if (!isManualSyncing && editedSegment && onPlaySegment) {
            console.log('useManualSync - Handling segment playback')
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
    }, [isManualSyncing, editedSegment, syncWordIndex, onPlaySegment, updateSegment, isSpacebarPressed])

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

        if (isManualSyncing && editedSegment && isSpacebarPressed) {
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
                        defaultEndTime,
                        duration: DEFAULT_WORD_DURATION
                    })
                } else {
                    // For a hold, use the current time as the end time
                    currentWord.end_time = currentTimeRef.current
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
                
                // Update the segment
                updateSegment(newWords)
            }
        }
    }, [isManualSyncing, editedSegment, syncWordIndex, updateSegment, isSpacebarPressed])

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
                
                // Update the segment
                updateSegment(newWords)
            }
        }
    }, [syncWordIndex, isManualSyncing, editedSegment, updateSegment])

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
        
        setIsManualSyncing(true)
        setSyncWordIndex(0)
        setIsSpacebarPressed(false)
        wordStartTimeRef.current = null
        spacebarPressTimeRef.current = null
        // Start playing 3 seconds before segment start
        onPlaySegment((editedSegment.start_time ?? 0) - 3)
    }, [isManualSyncing, editedSegment, onPlaySegment, cleanupManualSync])

    // Auto-stop sync if we go past the end time
    useEffect(() => {
        if (!editedSegment) return

        const endTime = editedSegment.end_time ?? 0

        if (window.isAudioPlaying && currentTimeRef.current > endTime) {
            console.log('Stopping playback: current time exceeded end time')
            window.toggleAudioPlayback?.()
            cleanupManualSync()
        }
    }, [isManualSyncing, editedSegment, currentTimeRef, cleanupManualSync])

    return {
        isManualSyncing,
        syncWordIndex,
        startManualSync,
        cleanupManualSync,
        handleSpacebar,
        isSpacebarPressed
    }
} 