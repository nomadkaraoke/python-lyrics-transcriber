import { useState, useCallback, useEffect, useRef } from 'react'
import { LyricsSegment, Word } from '../types'

interface UseManualSyncProps {
    editedSegment: LyricsSegment | null
    currentTime: number
    onPlaySegment?: (startTime: number) => void
    updateSegment: (words: Word[]) => void
}

export default function useManualSync({
    editedSegment,
    currentTime,
    onPlaySegment,
    updateSegment
}: UseManualSyncProps) {
    const [isManualSyncing, setIsManualSyncing] = useState(false)
    const [syncWordIndex, setSyncWordIndex] = useState<number>(-1)
    const currentTimeRef = useRef(currentTime)

    // Keep currentTimeRef up to date
    useEffect(() => {
        currentTimeRef.current = currentTime
    }, [currentTime])

    const cleanupManualSync = useCallback(() => {
        setIsManualSyncing(false)
        setSyncWordIndex(-1)
    }, [])

    const handleSpacebar = useCallback((e: KeyboardEvent) => {
        console.log('useManualSync - Spacebar pressed', {
            isManualSyncing,
            hasEditedSegment: !!editedSegment,
            syncWordIndex,
            currentTime: currentTimeRef.current
        })

        e.preventDefault()
        e.stopPropagation()

        if (isManualSyncing && editedSegment) {
            console.log('useManualSync - Handling manual sync mode')
            // Handle manual sync mode
            if (syncWordIndex < editedSegment.words.length) {
                const newWords = [...editedSegment.words]
                const currentWord = newWords[syncWordIndex]
                const prevWord = syncWordIndex > 0 ? newWords[syncWordIndex - 1] : null

                currentWord.start_time = currentTimeRef.current

                if (prevWord) {
                    prevWord.end_time = currentTimeRef.current - 0.01
                }

                if (syncWordIndex === editedSegment.words.length - 1) {
                    currentWord.end_time = editedSegment.end_time
                    setIsManualSyncing(false)
                    setSyncWordIndex(-1)
                    updateSegment(newWords)
                } else {
                    setSyncWordIndex(syncWordIndex + 1)
                    updateSegment(newWords)
                }
            }
        } else if (editedSegment && onPlaySegment) {
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
    }, [isManualSyncing, editedSegment, syncWordIndex, onPlaySegment, updateSegment])

    const startManualSync = useCallback(() => {
        if (isManualSyncing) {
            cleanupManualSync()
            return
        }

        if (!editedSegment || !onPlaySegment) return

        setIsManualSyncing(true)
        setSyncWordIndex(0)
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
        handleSpacebar
    }
} 