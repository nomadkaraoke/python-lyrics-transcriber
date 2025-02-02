import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
    TextField,
    Button,
    Typography,
    Menu,
    MenuItem,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import MergeIcon from '@mui/icons-material/CallMerge'
import SplitIcon from '@mui/icons-material/CallSplit'
import RestoreIcon from '@mui/icons-material/RestoreFromTrash'
import MoreVertIcon from '@mui/icons-material/MoreVert'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import { LyricsSegment, Word } from '../types'
import { useState, useEffect } from 'react'
import TimelineEditor from './TimelineEditor'

interface EditModalProps {
    open: boolean
    onClose: () => void
    segment: LyricsSegment | null
    segmentIndex: number | null
    originalSegment: LyricsSegment | null
    onSave: (updatedSegment: LyricsSegment) => void
    onPlaySegment?: (startTime: number) => void
    currentTime?: number
    onDelete?: (segmentIndex: number) => void
}

export default function EditModal({
    open,
    onClose,
    segment,
    segmentIndex,
    originalSegment,
    onSave,
    onPlaySegment,
    currentTime = 0,
    onDelete,
}: EditModalProps) {
    const [editedSegment, setEditedSegment] = useState<LyricsSegment | null>(segment)
    const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null)
    const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(null)
    const [replacementText, setReplacementText] = useState('')

    // Reset edited segment when modal opens with new segment
    useEffect(() => {
        setEditedSegment(segment)
    }, [segment])

    if (!segment || segmentIndex === null || !editedSegment || !originalSegment) return null

    const handleWordChange = (index: number, field: keyof Word, value: string | number) => {
        const newWords = [...editedSegment.words]
        newWords[index] = {
            ...newWords[index],
            [field]: field === 'start_time' || field === 'end_time'
                ? parseFloat(Number(value).toFixed(4))
                : value
        }
        updateSegment(newWords)
    }

    const updateSegment = (newWords: Word[]) => {
        const segmentStartTime = Math.min(...newWords.map(w => w.start_time))
        const segmentEndTime = Math.max(...newWords.map(w => w.end_time))

        setEditedSegment({
            ...editedSegment,
            words: newWords,
            text: newWords.map(w => w.text).join(' '),
            start_time: segmentStartTime,
            end_time: segmentEndTime
        })
    }

    const handleAddWord = (index?: number) => {
        const newWords = [...editedSegment.words]
        let newWord: Word

        if (index === undefined) {
            // Add at end
            const lastWord = newWords[newWords.length - 1]
            newWord = {
                text: '',
                start_time: lastWord.end_time,
                end_time: lastWord.end_time + 0.5,
                confidence: 1.0
            }
            newWords.push(newWord)
        } else {
            // Add between words
            const prevWord = newWords[index]
            const nextWord = newWords[index + 1]
            const midTime = prevWord ?
                (nextWord ? (prevWord.end_time + nextWord.start_time) / 2 : prevWord.end_time + 0.5) :
                (nextWord ? nextWord.start_time - 0.5 : 0)

            newWord = {
                text: '',
                start_time: midTime - 0.25,
                end_time: midTime + 0.25,
                confidence: 1.0
            }
            newWords.splice(index + 1, 0, newWord)
        }

        updateSegment(newWords)
    }

    const handleSplitWord = (index: number) => {
        const word = editedSegment.words[index]
        const midTime = (word.start_time + word.end_time) / 2
        const words = word.text.split(/\s+/)

        if (words.length <= 1) {
            // Split single word in half
            const firstHalf = word.text.slice(0, Math.ceil(word.text.length / 2))
            const secondHalf = word.text.slice(Math.ceil(word.text.length / 2))
            words[0] = firstHalf
            words[1] = secondHalf
        }

        const newWords = [...editedSegment.words]
        newWords.splice(index, 1,
            {
                text: words[0],
                start_time: word.start_time,
                end_time: midTime,
                confidence: 1.0
            },
            {
                text: words[1],
                start_time: midTime,
                end_time: word.end_time,
                confidence: 1.0
            }
        )

        updateSegment(newWords)
    }

    const handleMergeWords = (index: number) => {
        if (index >= editedSegment.words.length - 1) return

        const word1 = editedSegment.words[index]
        const word2 = editedSegment.words[index + 1]
        const newWords = [...editedSegment.words]

        newWords.splice(index, 2, {
            text: `${word1.text} ${word2.text}`.trim(),
            start_time: word1.start_time,
            end_time: word2.end_time,
            confidence: 1.0
        })

        updateSegment(newWords)
    }

    const handleRemoveWord = (index: number) => {
        const newWords = editedSegment.words.filter((_, i) => i !== index)
        updateSegment(newWords)
    }

    const handleReset = () => {
        setEditedSegment(JSON.parse(JSON.stringify(originalSegment)))
    }

    const handleWordMenu = (event: React.MouseEvent<HTMLElement>, index: number) => {
        setMenuAnchorEl(event.currentTarget)
        setSelectedWordIndex(index)
    }

    const handleMenuClose = () => {
        setMenuAnchorEl(null)
        setSelectedWordIndex(null)
    }

    const handleSave = () => {
        if (editedSegment) {
            console.log('EditModal - Saving segment:', {
                segmentIndex,
                originalText: segment?.text,
                editedText: editedSegment.text,
                wordCount: editedSegment.words.length,
                timeRange: `${editedSegment.start_time.toFixed(4)} - ${editedSegment.end_time.toFixed(4)}`
            })
            onSave(editedSegment)
            onClose()
        }
    }

    const handleReplaceAllWords = () => {
        if (!editedSegment) return

        const newWords = replacementText.trim().split(/\s+/)
        const segmentDuration = editedSegment.end_time - editedSegment.start_time

        let updatedWords: Word[]

        if (newWords.length === editedSegment.words.length) {
            // If word count matches, keep original timestamps
            updatedWords = editedSegment.words.map((word, index) => ({
                text: newWords[index],
                start_time: word.start_time,
                end_time: word.end_time,
                confidence: 1.0
            }))
        } else {
            // If word count differs, distribute time evenly
            const avgWordDuration = segmentDuration / newWords.length
            updatedWords = newWords.map((text, index) => ({
                text,
                start_time: editedSegment.start_time + (index * avgWordDuration),
                end_time: editedSegment.start_time + ((index + 1) * avgWordDuration),
                confidence: 1.0
            }))
        }

        updateSegment(updatedWords)
        setReplacementText('') // Clear the input after replacing
    }

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            handleSave()
        }
    }

    const handleDelete = () => {
        if (segmentIndex !== null) {
            onDelete?.(segmentIndex)
            onClose()
        }
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            onKeyDown={handleKeyDown}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    Edit Segment {segmentIndex}
                    {segment?.start_time !== undefined && onPlaySegment && (
                        <IconButton
                            size="small"
                            onClick={() => onPlaySegment(segment.start_time)}
                            sx={{ padding: '4px' }}
                        >
                            <PlayCircleOutlineIcon />
                        </IconButton>
                    )}
                </Box>
                <IconButton onClick={onClose} sx={{ ml: 'auto' }}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers>
                <Box sx={{ mb: 2 }}>
                    <TimelineEditor
                        words={editedSegment.words}
                        startTime={editedSegment.start_time}
                        endTime={editedSegment.end_time}
                        onWordUpdate={(index, updates) => {
                            const newWords = [...editedSegment.words]
                            newWords[index] = { ...newWords[index], ...updates }
                            updateSegment(newWords)
                        }}
                        currentTime={currentTime}
                    />
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Original Time Range: {originalSegment.start_time.toFixed(2)} - {originalSegment.end_time.toFixed(2)}
                    <br />
                    Current Time Range: {editedSegment.start_time.toFixed(2)} - {editedSegment.end_time.toFixed(2)}
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
                    {editedSegment.words.map((word, index) => (
                        <Box key={index} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                            <TextField
                                label={`Word ${index}`}
                                value={word.text}
                                onChange={(e) => handleWordChange(index, 'text', e.target.value)}
                                fullWidth
                                size="small"
                            />
                            <TextField
                                label="Start Time"
                                value={word.start_time.toFixed(2)}
                                onChange={(e) => handleWordChange(index, 'start_time', parseFloat(e.target.value))}
                                type="number"
                                inputProps={{ step: 0.01 }}
                                sx={{ width: '150px' }}
                                size="small"
                            />
                            <TextField
                                label="End Time"
                                value={word.end_time.toFixed(2)}
                                onChange={(e) => handleWordChange(index, 'end_time', parseFloat(e.target.value))}
                                type="number"
                                inputProps={{ step: 0.01 }}
                                sx={{ width: '150px' }}
                                size="small"
                            />
                            <IconButton onClick={(e) => handleWordMenu(e, index)}>
                                <MoreVertIcon />
                            </IconButton>
                        </Box>
                    ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 2 }}>
                    <TextField
                        label="Replace all words"
                        value={replacementText}
                        onChange={(e) => setReplacementText(e.target.value)}
                        fullWidth
                        placeholder="Type or paste replacement words here"
                        size="small"
                    />
                    <Button
                        variant="contained"
                        startIcon={<AutoFixHighIcon />}
                        onClick={handleReplaceAllWords}
                        disabled={!replacementText.trim()}
                    >
                        Replace All
                    </Button>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button
                    startIcon={<RestoreIcon />}
                    onClick={handleReset}
                    color="warning"
                >
                    Reset
                </Button>
                <Button
                    startIcon={<DeleteIcon />}
                    onClick={handleDelete}
                    color="error"
                    sx={{ mr: 'auto' }}
                >
                    Delete Segment
                </Button>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleSave} variant="contained">
                    Save Changes
                </Button>
            </DialogActions>

            <Menu
                anchorEl={menuAnchorEl}
                open={Boolean(menuAnchorEl)}
                onClose={handleMenuClose}
            >
                <MenuItem onClick={() => {
                    handleAddWord(selectedWordIndex!)
                    handleMenuClose()
                }}>
                    <AddIcon sx={{ mr: 1 }} /> Add Word After
                </MenuItem>
                <MenuItem onClick={() => {
                    handleSplitWord(selectedWordIndex!)
                    handleMenuClose()
                }}>
                    <SplitIcon sx={{ mr: 1 }} /> Split Word
                </MenuItem>
                <MenuItem
                    onClick={() => {
                        handleMergeWords(selectedWordIndex!)
                        handleMenuClose()
                    }}
                    disabled={selectedWordIndex === editedSegment.words.length - 1}
                >
                    <MergeIcon sx={{ mr: 1 }} /> Merge with Next
                </MenuItem>
                <MenuItem
                    onClick={() => {
                        handleRemoveWord(selectedWordIndex!)
                        handleMenuClose()
                    }}
                    disabled={editedSegment.words.length <= 1}
                >
                    <DeleteIcon sx={{ mr: 1 }} color="error" /> Remove
                </MenuItem>
            </Menu>
        </Dialog>
    )
} 