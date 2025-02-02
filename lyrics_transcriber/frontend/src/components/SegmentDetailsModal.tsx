import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton, Box
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { LyricsSegment } from '../types'

interface SegmentDetailsModalProps {
    open: boolean
    onClose: () => void
    segment: LyricsSegment | null
    segmentIndex: number | null
}

export default function SegmentDetailsModal({
    open,
    onClose,
    segment,
    segmentIndex
}: SegmentDetailsModalProps) {
    if (!segment || segmentIndex === null) return null

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{
                sx: { position: 'relative' },
            }}
        >
            <IconButton
                onClick={onClose}
                sx={{
                    position: 'absolute',
                    right: 8,
                    top: 8,
                }}
            >
                <CloseIcon />
            </IconButton>
            <DialogTitle>
                Segment {segmentIndex} Details
            </DialogTitle>
            <DialogContent dividers>
                <Box
                    component="pre"
                    sx={{
                        margin: 0,
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                    }}
                >
                    {JSON.stringify(segment, null, 2)}
                </Box>
            </DialogContent>
        </Dialog>
    )
} 