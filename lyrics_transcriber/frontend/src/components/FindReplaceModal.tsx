import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
    TextField,
    Button,
    Typography
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useState } from 'react'

interface FindReplaceModalProps {
    open: boolean
    onClose: () => void
    onReplace: (findText: string, replaceText: string) => void
}

export default function FindReplaceModal({
    open,
    onClose,
    onReplace
}: FindReplaceModalProps) {
    const [findText, setFindText] = useState('')
    const [replaceText, setReplaceText] = useState('')

    const handleReplace = () => {
        if (!findText) return
        onReplace(findText, replaceText)
        onClose()
    }

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            handleReplace()
        }
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            onKeyDown={handleKeyDown}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1 }}>Find and Replace</Box>
                <IconButton onClick={onClose}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                        Enter text to find and replace across all lyrics segments.
                    </Typography>
                    <TextField
                        label="Find"
                        value={findText}
                        onChange={(e) => setFindText(e.target.value)}
                        fullWidth
                        size="small"
                        autoFocus
                    />
                    <TextField
                        label="Replace with"
                        value={replaceText}
                        onChange={(e) => setReplaceText(e.target.value)}
                        fullWidth
                        size="small"
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button 
                    onClick={handleReplace}
                    disabled={!findText}
                    variant="contained"
                >
                    Replace All
                </Button>
            </DialogActions>
        </Dialog>
    )
} 