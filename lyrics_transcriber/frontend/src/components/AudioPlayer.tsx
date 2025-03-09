import { Box, IconButton, Slider, Typography } from '@mui/material'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import { useEffect, useRef, useState, useCallback } from 'react'
import { ApiClient } from '../api'

interface AudioPlayerProps {
    apiClient: ApiClient | null,
    onTimeUpdate?: (time: number) => void,
    audioHash: string
}

export default function AudioPlayer({ apiClient, onTimeUpdate, audioHash }: AudioPlayerProps) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    useEffect(() => {
        if (!apiClient) return

        const audio = new Audio(apiClient.getAudioUrl(audioHash))
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
            setIsPlaying(true)
            window.isAudioPlaying = true
            updateTime()
        })

        audio.addEventListener('pause', () => {
            setIsPlaying(false)
            window.isAudioPlaying = false
            cancelAnimationFrame(animationFrameId)
        })

        audio.addEventListener('ended', () => {
            cancelAnimationFrame(animationFrameId)
            setIsPlaying(false)
            window.isAudioPlaying = false
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
            window.isAudioPlaying = false
        }
    }, [apiClient, onTimeUpdate, audioHash])

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

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
            gap: 0.5,
            backgroundColor: 'background.paper',
            borderRadius: 1,
            height: '32px',
        }}>
            <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5, fontSize: '0.75rem' }}>
                Playback:
            </Typography>

            <IconButton
                onClick={handlePlayPause}
                size="small"
                sx={{ p: 0.5 }}
            >
                {isPlaying ? <PauseIcon fontSize="small" /> : <PlayArrowIcon fontSize="small" />}
            </IconButton>

            <Typography variant="body2" sx={{ minWidth: 32, fontSize: '0.75rem' }}>
                {formatTime(currentTime)}
            </Typography>

            <Slider
                value={currentTime}
                min={0}
                max={duration}
                onChange={handleSeek}
                size="small"
                sx={{
                    width: 150,
                    mx: 0.5,
                    '& .MuiSlider-thumb': {
                        width: 10,
                        height: 10,
                    },
                    '& .MuiSlider-rail, & .MuiSlider-track': {
                        height: 3
                    }
                }}
            />

            <Typography variant="body2" sx={{ minWidth: 32, fontSize: '0.75rem' }}>
                {formatTime(duration)}
            </Typography>
        </Box>
    )
} 