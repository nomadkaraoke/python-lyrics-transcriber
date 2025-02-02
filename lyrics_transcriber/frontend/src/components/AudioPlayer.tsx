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

        // Create audio element with the API endpoint URL
        const audio = new Audio(apiClient.getAudioUrl())
        audioRef.current = audio

        // Set up event listeners
        audio.addEventListener('loadedmetadata', () => {
            setDuration(audio.duration)
        })

        audio.addEventListener('timeupdate', () => {
            const time = audio.currentTime
            setCurrentTime(time)
            onTimeUpdate?.(time)
        })

        audio.addEventListener('ended', () => {
            setIsPlaying(false)
            setCurrentTime(0)
        })

        return () => {
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
            gap: 2,
            p: 2,
            backgroundColor: 'background.paper',
            borderRadius: 1,
            boxShadow: 1
        }}>
            <IconButton
                onClick={handlePlayPause}
                size="large"
            >
                {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>

            <Typography sx={{ minWidth: 45 }}>
                {formatTime(currentTime)}
            </Typography>

            <Slider
                value={currentTime}
                min={0}
                max={duration}
                onChange={handleSeek}
                sx={{ mx: 2 }}
            />

            <Typography sx={{ minWidth: 45 }}>
                {formatTime(duration)}
            </Typography>
        </Box>
    )
} 