import { Button, Box, TextField } from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import { useState, useEffect } from 'react'
import { ModalContent } from './LyricsAnalyzer'

interface WordEditControlsProps {
    content: ModalContent
    onUpdateCorrection?: (wordId: string, updatedWords: string[]) => void
    onClose: () => void
}

export function useWordEdit(content: ModalContent | null) {
    const [editedWord, setEditedWord] = useState('')
    const [isEditing, setIsEditing] = useState(false)

    useEffect(() => {
        if (content) {
            setEditedWord(content.data.word || '')
            setIsEditing(false)
        }
    }, [content])

    return {
        editedWord,
        setEditedWord,
        isEditing,
        setIsEditing
    }
}

export default function WordEditControls({ content, onUpdateCorrection, onClose }: WordEditControlsProps) {
    const {
        editedWord,
        setEditedWord,
        isEditing,
        setIsEditing
    } = useWordEdit(content)

    const handleStartEdit = () => {
        setEditedWord(content.data.word || '')
        setIsEditing(true)
    }

    const handleDelete = () => {
        if (!onUpdateCorrection) return
        onUpdateCorrection(content.data.wordId, [])
        onClose()
    }

    const handleSaveEdit = () => {
        if (onUpdateCorrection) {
            onUpdateCorrection(content.data.wordId, [editedWord])
        }
        onClose()
    }

    const handleCancelEdit = () => {
        setEditedWord(content.data.word || '')
        setIsEditing(false)
    }

    const handleWordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setEditedWord(event.target.value)
    }

    return isEditing ? (
        <Box>
            <TextField
                value={editedWord}
                onChange={handleWordChange}
                fullWidth
                label="Edit word"
                variant="outlined"
                size="small"
                sx={{ mb: 1 }}
            />
            <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="contained" onClick={handleSaveEdit}>
                    Save Changes
                </Button>
                <Button variant="outlined" onClick={handleCancelEdit}>
                    Cancel
                </Button>
                <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={handleDelete}
                >
                    Delete
                </Button>
            </Box>
        </Box>
    ) : (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button variant="outlined" size="small" onClick={handleStartEdit}>
                Edit
            </Button>
            <Button
                variant="outlined"
                size="small"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleDelete}
            >
                Delete
            </Button>
        </Box>
    )
} 