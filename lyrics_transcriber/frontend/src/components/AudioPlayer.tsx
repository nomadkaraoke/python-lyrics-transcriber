import { Box, IconButton, Slider, Typography } from '@mui/material'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import { useEffect, useRef, useState, useCallback } from 'react'
import { ApiClient } from '../api'

interface AudioPlayerProps {
    apiClient: ApiClient | null,
    onTimeUpdate?: (time: number) => void
}

export default function AudioPlayer({ apiClient, onTimeUpdate }: AudioPlayerProps) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    useEffect(() => {
        if (!apiClient) return

        const audio = new Audio(apiClient.getAudioUrl())
        audioRef.current = audio

        // Add requestAnimationFrame for smoother updates
        let animationFrameId: number

        const updateTime = () => {
            const time = audio.currentTime
            setCurrentTime(time)
            onTimeUpdate?.(time)
            animationFrameId = requestAnimationFrame(updateTime)
        }

        audio.addEventListener('play', () => {
            updateTime()
        })

        audio.addEventListener('pause', () => {
            cancelAnimationFrame(animationFrameId)
        })

        audio.addEventListener('ended', () => {
            cancelAnimationFrame(animationFrameId)
            setIsPlaying(false)
            setCurrentTime(0)
        })

        audio.addEventListener('loadedmetadata', () => {
            setDuration(audio.duration)
        })

        return () => {
            cancelAnimationFrame(animationFrameId)
            audio.pause()
            audio.src = ''
            audioRef.current = null
        }
    }, [apiClient, onTimeUpdate])

    const handlePlayPause = () => {
        if (!audioRef.current) return

        if (isPlaying) {
            audioRef.current.pause()
        } else {
            audioRef.current.play()
        }
        setIsPlaying(!isPlaying)
    }

    const handleSeek = (_: Event, newValue: number | number[]) => {
        if (!audioRef.current) return
        const time = newValue as number
        audioRef.current.currentTime = time
        setCurrentTime(time)
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    // Add this method to expose seeking functionality
    const seekAndPlay = (time: number) => {
        if (!audioRef.current) return

        audioRef.current.currentTime = time
        setCurrentTime(time)
        audioRef.current.play()
        setIsPlaying(true)
    }

    const togglePlayback = useCallback(() => {
        if (!audioRef.current) return

        if (isPlaying) {
            audioRef.current.pause()
        } else {
            audioRef.current.play()
        }
        setIsPlaying(!isPlaying)
    }, [isPlaying])

    // Expose both methods globally
    useEffect(() => {
        if (!apiClient) return

        const win = window as any
        win.seekAndPlayAudio = seekAndPlay
        win.toggleAudioPlayback = togglePlayback

        return () => {
            delete win.seekAndPlayAudio
            delete win.toggleAudioPlayback
        }
    }, [apiClient, togglePlayback])

    if (!apiClient) return null

    return (
        <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            backgroundColor: 'background.paper',
            borderRadius: 1,
            height: 40, // Match ToggleButtonGroup height
        }}>
            <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
                Playback:
            </Typography>
            
            <IconButton
                onClick={handlePlayPause}
                size="small"
            >
                {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>

            <Typography variant="body2" sx={{ minWidth: 40 }}>
                {formatTime(currentTime)}
            </Typography>

            <Slider
                value={currentTime}
                min={0}
                max={duration}
                onChange={handleSeek}
                size="small"
                sx={{ 
                    width: 200,
                    mx: 1,
                    '& .MuiSlider-thumb': {
                        width: 12,
                        height: 12,
                    }
                }}
            />

            <Typography variant="body2" sx={{ minWidth: 40 }}>
                {formatTime(duration)}
            </Typography>
        </Box>
    )
} 