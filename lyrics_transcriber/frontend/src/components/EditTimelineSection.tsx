import {
    Box,
    Button,
    Typography,
    IconButton,
    Tooltip,
    Stack
} from '@mui/material'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import CancelIcon from '@mui/icons-material/Cancel'
import ZoomInIcon from '@mui/icons-material/ZoomIn'
import ZoomOutIcon from '@mui/icons-material/ZoomOut'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import AutorenewIcon from '@mui/icons-material/Autorenew'
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutline'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'
import TimelineEditor from './TimelineEditor'
import { Word } from '../types'
import { useState, useEffect, useCallback, useRef } from 'react'

interface EditTimelineSectionProps {
    words: Word[]
    startTime: number
    endTime: number
    originalStartTime: number | null
    originalEndTime: number | null
    currentStartTime: number | null
    currentEndTime: number | null
    currentTime?: number
    isManualSyncing: boolean
    syncWordIndex: number
    isSpacebarPressed: boolean
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    onPlaySegment?: (time: number) => void
    startManualSync: () => void
    isGlobal?: boolean
}

export default function EditTimelineSection({
    words,
    startTime,
    endTime,
    originalStartTime,
    originalEndTime,
    currentStartTime,
    currentEndTime,
    currentTime,
    isManualSyncing,
    syncWordIndex,
    isSpacebarPressed,
    onWordUpdate,
    onPlaySegment,
    startManualSync,
    isGlobal = false
}: EditTimelineSectionProps) {
    // Add state for zoom level
    const [zoomLevel, setZoomLevel] = useState(10) // Default 10 seconds visible
    const [visibleStartTime, setVisibleStartTime] = useState(startTime)
    const [visibleEndTime, setVisibleEndTime] = useState(Math.min(startTime + zoomLevel, endTime))
    const [autoScrollEnabled, setAutoScrollEnabled] = useState(true) // Default to enabled
    const timelineRef = useRef<HTMLDivElement>(null)

    // Initial setup of visible time range
    useEffect(() => {
        if (isGlobal) {
            // For global mode, start at the beginning
            setVisibleStartTime(startTime)
            setVisibleEndTime(Math.min(startTime + zoomLevel, endTime))
        } else {
            // For segment mode, always show the full segment
            setVisibleStartTime(startTime)
            setVisibleEndTime(endTime)
        }
    }, [startTime, endTime, zoomLevel, isGlobal])

    // Handle playback scrolling with "page turning" approach
    useEffect(() => {
        // Skip if not in global mode, no current time, or auto-scroll is disabled
        if (!isGlobal || !currentTime || !autoScrollEnabled) return

        // Only scroll when current time is outside or near the edge of the visible window
        if (currentTime < visibleStartTime) {
            // If current time is before visible window, jump to show it at the start
            const newStart = Math.max(startTime, currentTime)
            const newEnd = Math.min(endTime, newStart + zoomLevel)
            setVisibleStartTime(newStart)
            setVisibleEndTime(newEnd)
        } else if (currentTime > visibleEndTime - (zoomLevel * 0.05)) {
            // If current time is near the end of visible window (within 5% of zoom level from the end),
            // jump to the next "page" with current time at 5% from the left
            const pageOffset = zoomLevel * 0.05 // Position current time 5% from the left edge
            const newStart = Math.max(startTime, currentTime - pageOffset)
            const newEnd = Math.min(endTime, newStart + zoomLevel)
            
            // Only update if we're actually moving forward
            if (newStart > visibleStartTime) {
                setVisibleStartTime(newStart)
                setVisibleEndTime(newEnd)
            }
        }
    }, [currentTime, visibleStartTime, visibleEndTime, startTime, endTime, zoomLevel, isGlobal, autoScrollEnabled])

    // Update visible time range when zoom level changes - but don't auto-center on current time
    useEffect(() => {
        if (isGlobal) {
            // Don't auto-center on current time, just adjust the visible window based on zoom level
            // while keeping the left edge fixed (unless it would go out of bounds)
            const newEnd = Math.min(endTime, visibleStartTime + zoomLevel)

            // If the new end would exceed the total range, adjust the start time
            if (newEnd === endTime) {
                const newStart = Math.max(startTime, endTime - zoomLevel)
                setVisibleStartTime(newStart)
            }

            setVisibleEndTime(newEnd)
        } else {
            // For segment mode, always show the full segment
            setVisibleStartTime(startTime)
            setVisibleEndTime(endTime)
        }
    }, [zoomLevel, startTime, endTime, isGlobal, visibleStartTime])

    // Toggle auto-scroll
    const toggleAutoScroll = () => {
        setAutoScrollEnabled(!autoScrollEnabled)
    }

    // Jump to current playback position
    const jumpToCurrentTime = useCallback(() => {
        if (!isGlobal || !currentTime) return

        // Center the view around the current time
        const halfZoom = zoomLevel / 2
        let newStart = Math.max(startTime, currentTime - halfZoom)
        const newEnd = Math.min(endTime, newStart + zoomLevel)

        // Adjust start time if end time hits the boundary
        if (newEnd === endTime) {
            newStart = Math.max(startTime, endTime - zoomLevel)
        }

        setVisibleStartTime(newStart)
        setVisibleEndTime(newEnd)
    }, [currentTime, zoomLevel, startTime, endTime, isGlobal])

    // Add keyboard shortcut for toggling auto-scroll
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (isGlobal) {
                // Alt+A to toggle auto-scroll
                if (e.altKey && e.key === 'a') {
                    e.preventDefault()
                    toggleAutoScroll()
                }

                // Alt+J to jump to current time
                if (e.altKey && e.key === 'j') {
                    e.preventDefault()
                    jumpToCurrentTime()
                }
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => {
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [isGlobal, toggleAutoScroll, jumpToCurrentTime])

    // Handle zoom in
    const handleZoomIn = () => {
        if (zoomLevel > 2) { // Minimum zoom level of 2 seconds
            setZoomLevel(zoomLevel - 2)
        }
    }

    // Handle zoom out
    const handleZoomOut = () => {
        if (zoomLevel < (endTime - startTime)) { // Maximum zoom is the full range
            setZoomLevel(zoomLevel + 2)
        }
    }

    // Handle horizontal scrolling
    const handleScroll = useCallback((event: React.WheelEvent<HTMLDivElement>) => {
        if (isGlobal && event.deltaX !== 0) {
            event.preventDefault()

            // Disable auto-scroll when user manually scrolls
            setAutoScrollEnabled(false)

            // Calculate scroll amount in seconds (scale based on zoom level)
            const scrollAmount = (event.deltaX / 100) * (zoomLevel / 10)

            // Update visible time range
            let newStart = visibleStartTime + scrollAmount
            let newEnd = visibleEndTime + scrollAmount

            // Ensure we don't scroll beyond the boundaries
            if (newStart < startTime) {
                newStart = startTime
                newEnd = newStart + zoomLevel
            }

            if (newEnd > endTime) {
                newEnd = endTime
                newStart = Math.max(startTime, newEnd - zoomLevel)
            }

            setVisibleStartTime(newStart)
            setVisibleEndTime(newEnd)
        }
    }, [isGlobal, visibleStartTime, visibleEndTime, startTime, endTime, zoomLevel])

    // Handle scroll left button
    const handleScrollLeft = () => {
        if (!isGlobal) return

        // Disable auto-scroll when user manually scrolls
        setAutoScrollEnabled(false)

        // Scroll left by 25% of the current visible range
        const scrollAmount = zoomLevel * 0.25
        const newStart = Math.max(startTime, visibleStartTime - scrollAmount)
        const newEnd = newStart + zoomLevel

        setVisibleStartTime(newStart)
        setVisibleEndTime(newEnd)
    }

    // Handle scroll right button
    const handleScrollRight = () => {
        if (!isGlobal) return

        // Disable auto-scroll when user manually scrolls
        setAutoScrollEnabled(false)

        // Scroll right by 25% of the current visible range
        const scrollAmount = zoomLevel * 0.25
        const newEnd = Math.min(endTime, visibleEndTime + scrollAmount)
        let newStart = newEnd - zoomLevel

        // Ensure we don't scroll beyond the start boundary
        if (newStart < startTime) {
            newStart = startTime
            const adjustedNewEnd = Math.min(endTime, newStart + zoomLevel)
            setVisibleEndTime(adjustedNewEnd)
        } else {
            setVisibleEndTime(newEnd)
        }

        setVisibleStartTime(newStart)
    }

    // Get the effective time range to display
    const effectiveStartTime = isGlobal ? visibleStartTime : startTime
    const effectiveEndTime = isGlobal ? visibleEndTime : endTime

    return (
        <>
            <Box
                sx={{ height: '120px', mb: 2 }}
                ref={timelineRef}
                onWheel={handleScroll}
            >
                <TimelineEditor
                    words={words}
                    startTime={effectiveStartTime}
                    endTime={effectiveEndTime}
                    onWordUpdate={onWordUpdate}
                    currentTime={currentTime}
                    onPlaySegment={onPlaySegment}
                />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">
                    Original Time Range: {originalStartTime?.toFixed(2) ?? 'N/A'} - {originalEndTime?.toFixed(2) ?? 'N/A'}
                    <br />
                    Current Time Range: {currentStartTime?.toFixed(2) ?? 'N/A'} - {currentEndTime?.toFixed(2) ?? 'N/A'}
                </Typography>

                <Stack direction="row" spacing={1} alignItems="center">
                    {isGlobal && (
                        <>
                            <Tooltip title="Scroll Left">
                                <IconButton
                                    onClick={handleScrollLeft}
                                    disabled={visibleStartTime <= startTime}
                                    size="small"
                                >
                                    <ArrowBackIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Zoom Out (Show More Time)">
                                <IconButton
                                    onClick={handleZoomOut}
                                    disabled={zoomLevel >= (endTime - startTime)}
                                    size="small"
                                >
                                    <ZoomOutIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Zoom In (Show Less Time)">
                                <IconButton
                                    onClick={handleZoomIn}
                                    disabled={zoomLevel <= 2}
                                    size="small"
                                >
                                    <ZoomInIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Scroll Right">
                                <IconButton
                                    onClick={handleScrollRight}
                                    disabled={visibleEndTime >= endTime}
                                    size="small"
                                >
                                    <ArrowForwardIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip
                                title={autoScrollEnabled ?
                                    "Disable Auto-Page Turn During Playback (Alt+A)" :
                                    "Enable Auto-Page Turn During Playback (Alt+A)"}
                            >
                                <IconButton
                                    onClick={toggleAutoScroll}
                                    color={autoScrollEnabled ? "primary" : "default"}
                                    size="small"
                                >
                                    {autoScrollEnabled ? <AutorenewIcon /> : <PauseCircleOutlineIcon />}
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Jump to Current Playback Position (Alt+J)">
                                <IconButton
                                    onClick={jumpToCurrentTime}
                                    disabled={!currentTime}
                                    size="small"
                                >
                                    <CenterFocusStrongIcon />
                                </IconButton>
                            </Tooltip>
                        </>
                    )}
                    <Button
                        variant={isManualSyncing ? "outlined" : "contained"}
                        onClick={startManualSync}
                        disabled={!onPlaySegment}
                        startIcon={isManualSyncing ? <CancelIcon /> : <PlayCircleOutlineIcon />}
                        color={isManualSyncing ? "error" : "primary"}
                    >
                        {isManualSyncing ? "Cancel Sync" : "Manual Sync"}
                    </Button>
                    {isManualSyncing && (
                        <Box>
                            <Typography variant="body2">
                                Word {syncWordIndex + 1} of {words.length}: <strong>{words[syncWordIndex]?.text || ''}</strong>
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {isSpacebarPressed ?
                                    "Holding spacebar... Release when word ends" :
                                    "Press spacebar when word starts (tap for short words, hold for long words)"}
                            </Typography>
                        </Box>
                    )}
                </Stack>
            </Box>
        </>
    )
} 