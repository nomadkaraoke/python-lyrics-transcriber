import { Box, Button } from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import RestoreIcon from '@mui/icons-material/RestoreFromTrash'
import HistoryIcon from '@mui/icons-material/History'
import { LyricsSegment } from '../types'

interface EditActionBarProps {
    onReset: () => void
    onRevertToOriginal?: () => void
    onDelete?: () => void
    onClose: () => void
    onSave: () => void
    editedSegment: LyricsSegment | null
    originalTranscribedSegment?: LyricsSegment | null
    isGlobal?: boolean
}

export default function EditActionBar({
    onReset,
    onRevertToOriginal,
    onDelete,
    onClose,
    onSave,
    editedSegment,
    originalTranscribedSegment,
    isGlobal = false
}: EditActionBarProps) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Button
                    startIcon={<RestoreIcon />}
                    onClick={onReset}
                    color="warning"
                >
                    Reset
                </Button>
                {originalTranscribedSegment && (
                    <Button
                        onClick={onRevertToOriginal}
                        startIcon={<HistoryIcon />}
                    >
                        Un-Correct
                    </Button>
                )}
                {!isGlobal && onDelete && (
                    <Button
                        startIcon={<DeleteIcon />}
                        onClick={onDelete}
                        color="error"
                    >
                        Delete Segment
                    </Button>
                )}
            </Box>
            <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
                <Button onClick={onClose}>Cancel</Button>
                <Button
                    onClick={onSave}
                    variant="contained"
                    disabled={!editedSegment || editedSegment.words.length === 0}
                >
                    Save
                </Button>
            </Box>
        </Box>
    )
} 