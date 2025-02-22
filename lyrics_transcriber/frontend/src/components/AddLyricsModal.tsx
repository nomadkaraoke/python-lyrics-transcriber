import { useState } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    CircularProgress,
    Typography
} from '@mui/material'

interface AddLyricsModalProps {
    open: boolean
    onClose: () => void
    onSubmit: (source: string, lyrics: string) => Promise<void>
    isSubmitting: boolean
}

export default function AddLyricsModal({
    open,
    onClose,
    onSubmit,
    isSubmitting
}: AddLyricsModalProps) {
    const [source, setSource] = useState('')
    const [lyrics, setLyrics] = useState('')
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async () => {
        if (!source.trim()) {
            setError('Please enter a source name')
            return
        }
        if (!lyrics.trim()) {
            setError('Please enter lyrics text')
            return
        }

        try {
            await onSubmit(source.trim(), lyrics.trim())
            // Reset form on success
            setSource('')
            setLyrics('')
            setError(null)
            onClose()
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add lyrics')
        }
    }

    const handleClose = () => {
        // Don't allow closing if currently submitting
        if (isSubmitting) return

        setSource('')
        setLyrics('')
        setError(null)
        onClose()
    }

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="md"
            fullWidth
            disableEscapeKeyDown={isSubmitting}
        >
            <DialogTitle>Add Reference Lyrics</DialogTitle>
            <DialogContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                    {error && (
                        <Typography color="error" variant="body2">
                            {error}
                        </Typography>
                    )}
                    <TextField
                        label="Source Name"
                        value={source}
                        onChange={(e) => setSource(e.target.value)}
                        disabled={isSubmitting}
                        fullWidth
                        placeholder="e.g., Official Lyrics, Album Booklet"
                    />
                    <TextField
                        label="Lyrics"
                        value={lyrics}
                        onChange={(e) => setLyrics(e.target.value)}
                        disabled={isSubmitting}
                        fullWidth
                        multiline
                        rows={10}
                        placeholder="Paste lyrics text here (one line per segment)"
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={handleClose} disabled={isSubmitting}>
                    Cancel
                </Button>
                <Button
                    onClick={handleSubmit}
                    variant="contained"
                    disabled={isSubmitting}
                    startIcon={isSubmitting ? <CircularProgress size={20} /> : undefined}
                >
                    {isSubmitting ? 'Adding...' : 'Add Lyrics'}
                </Button>
            </DialogActions>
        </Dialog>
    )
} 