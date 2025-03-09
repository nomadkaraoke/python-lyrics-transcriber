import { Box, Button, Typography } from '@mui/material'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import CancelIcon from '@mui/icons-material/Cancel'
import TimelineEditor from './TimelineEditor'
import { Word } from '../types'

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
}: EditTimelineSectionProps) {
    return (
        <>
            <Box sx={{ mb: 0 }}>
                <TimelineEditor
                    words={words}
                    startTime={startTime}
                    endTime={endTime}
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

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
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
                </Box>
            </Box>
        </>
    )
} 