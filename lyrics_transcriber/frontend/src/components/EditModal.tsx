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
import CancelIcon from '@mui/icons-material/Cancel'
import StopIcon from '@mui/icons-material/Stop'
import { LyricsSegment, Word } from '../types'
import { useState, useEffect, useCallback } from 'react'
import TimelineEditor from './TimelineEditor'
import { nanoid } from 'nanoid'

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
    onAddSegment?: (segmentIndex: number) => void
    onSplitSegment?: (segmentIndex: number, afterWordIndex: number) => void
    setModalSpacebarHandler: (handler: (() => (e: KeyboardEvent) => void) | undefined) => void
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
    onAddSegment,
    onSplitSegment,
    setModalSpacebarHandler,
}: EditModalProps) {
    // All useState hooks
    const [editedSegment, setEditedSegment] = useState<LyricsSegment | null>(segment)
    const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null)
    const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(null)
    const [replacementText, setReplacementText] = useState('')
    const [isManualSyncing, setIsManualSyncing] = useState(false)
    const [syncWordIndex, setSyncWordIndex] = useState<number>(-1)
    const [isPlaying, setIsPlaying] = useState(false)

    // Define updateSegment first since other hooks depend on it
    const updateSegment = useCallback((newWords: Word[]) => {
        if (!editedSegment) return;

        const validStartTimes = newWords.map(w => w.start_time).filter((t): t is number => t !== null)
        const validEndTimes = newWords.map(w => w.end_time).filter((t): t is number => t !== null)

        const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null
        const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null

        setEditedSegment({
            ...editedSegment,
            words: newWords,
            text: newWords.map(w => w.text).join(' '),
            start_time: segmentStartTime,
            end_time: segmentEndTime
        })
    }, [editedSegment])

    // Other useCallback hooks
    const cleanupManualSync = useCallback(() => {
        setIsManualSyncing(false)
        setSyncWordIndex(-1)
    }, [])

    const handleClose = useCallback(() => {
        cleanupManualSync()
        onClose()
    }, [onClose, cleanupManualSync])

    // All useEffect hooks
    useEffect(() => {
        setEditedSegment(segment)
    }, [segment])

    // Update the spacebar handler when modal state changes
    useEffect(() => {
        if (open) {
            setModalSpacebarHandler(() => (e: KeyboardEvent) => {
                e.preventDefault()
                e.stopPropagation()

                if (isManualSyncing && editedSegment) {
                    // Handle manual sync mode
                    if (syncWordIndex < editedSegment.words.length) {
                        const newWords = [...editedSegment.words]
                        const currentWord = newWords[syncWordIndex]
                        const prevWord = syncWordIndex > 0 ? newWords[syncWordIndex - 1] : null

                        currentWord.start_time = currentTime

                        if (prevWord) {
                            prevWord.end_time = currentTime - 0.01
                        }

                        if (syncWordIndex === editedSegment.words.length - 1) {
                            currentWord.end_time = editedSegment.end_time
                            setIsManualSyncing(false)
                            setSyncWordIndex(-1)
                            updateSegment(newWords)
                        } else {
                            setSyncWordIndex(syncWordIndex + 1)
                            updateSegment(newWords)
                        }
                    }
                } else if (editedSegment && onPlaySegment) {
                    // Toggle segment playback when not in manual sync mode
                    const startTime = editedSegment.start_time ?? 0
                    const endTime = editedSegment.end_time ?? 0

                    if (currentTime >= startTime && currentTime <= endTime) {
                        if (window.toggleAudioPlayback) {
                            window.toggleAudioPlayback()
                        }
                    } else {
                        onPlaySegment(startTime)
                    }
                }
            })
        } else {
            setModalSpacebarHandler(undefined)
        }

        return () => {
            setModalSpacebarHandler(undefined)
        }
    }, [
        open,
        isManualSyncing,
        editedSegment,
        syncWordIndex,
        currentTime,
        onPlaySegment,
        updateSegment,
        setModalSpacebarHandler
    ])

    // Auto-stop sync if we go past the end time
    useEffect(() => {
        if (!editedSegment) return

        const endTime = editedSegment.end_time ?? 0

        if (window.isAudioPlaying && currentTime > endTime) {
            console.log('Stopping playback: current time exceeded end time')
            window.toggleAudioPlayback?.()
            setIsManualSyncing(false)
            setSyncWordIndex(-1)
        }

    }, [isManualSyncing, editedSegment, currentTime, setSyncWordIndex])

    // Update isPlaying when currentTime changes
    useEffect(() => {
        if (editedSegment) {
            const startTime = editedSegment.start_time ?? 0
            const endTime = editedSegment.end_time ?? 0
            const isWithinSegment = currentTime >= startTime && currentTime <= endTime

            // Only consider it playing if it's within the segment AND audio is actually playing
            setIsPlaying(isWithinSegment && window.isAudioPlaying === true)
        }
    }, [currentTime, editedSegment])

    // Add a function to get safe time values
    const getSafeTimeRange = (segment: LyricsSegment | null) => {
        if (!segment) return { start: 0, end: 1 }; // Default 1-second range
        const start = segment.start_time ?? 0;
        const end = segment.end_time ?? (start + 1);
        return { start, end };
    }

    // Early return after all hooks and function definitions
    if (!segment || segmentIndex === null || !editedSegment || !originalSegment) return null

    // Get safe time values for TimelineEditor
    const timeRange = getSafeTimeRange(editedSegment)

    const handleWordChange = (index: number, updates: Partial<Word>) => {
        const newWords = [...editedSegment.words]
        newWords[index] = {
            ...newWords[index],
            ...updates
        }
        updateSegment(newWords)
    }

    const handleAddWord = (index?: number) => {
        const newWords = [...editedSegment.words]
        let newWord: Word

        if (index === undefined) {
            // Add at end
            const lastWord = newWords[newWords.length - 1]
            const lastEndTime = lastWord.end_time ?? 0
            newWord = {
                id: nanoid(),
                text: '',
                start_time: lastEndTime,
                end_time: lastEndTime + 0.5,
                confidence: 1.0
            }
            newWords.push(newWord)
        } else {
            // Add between words
            const prevWord = newWords[index]
            const nextWord = newWords[index + 1]
            const midTime = prevWord ?
                (nextWord ?
                    ((prevWord.end_time ?? 0) + (nextWord.start_time ?? 0)) / 2 :
                    (prevWord.end_time ?? 0) + 0.5
                ) :
                (nextWord ? (nextWord.start_time ?? 0) - 0.5 : 0)

            newWord = {
                id: nanoid(),
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
        const startTime = word.start_time ?? 0
        const endTime = word.end_time ?? startTime + 0.5
        const midTime = (startTime + endTime) / 2
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
                id: nanoid(),
                text: words[0],
                start_time: startTime,
                end_time: midTime,
                confidence: 1.0
            },
            {
                id: nanoid(),
                text: words[1],
                start_time: midTime,
                end_time: endTime,
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
            id: nanoid(),
            text: `${word1.text} ${word2.text}`.trim(),
            start_time: word1.start_time ?? null,
            end_time: word2.end_time ?? null,
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
                timeRange: `${editedSegment.start_time?.toFixed(4) ?? 'N/A'} - ${editedSegment.end_time?.toFixed(4) ?? 'N/A'}`
            })
            onSave(editedSegment)
            onClose()
        }
    }

    const handleReplaceAllWords = () => {
        if (!editedSegment) return

        const newWords = replacementText.trim().split(/\s+/)
        const startTime = editedSegment.start_time ?? 0
        const endTime = editedSegment.end_time ?? (startTime + newWords.length) // Default to 1 second per word
        const segmentDuration = endTime - startTime

        let updatedWords: Word[]

        if (newWords.length === editedSegment.words.length) {
            // If word count matches, keep original timestamps and IDs
            updatedWords = editedSegment.words.map((word, index) => ({
                id: word.id,  // Keep original ID
                text: newWords[index],
                start_time: word.start_time,
                end_time: word.end_time,
                confidence: 1.0
            }))
        } else {
            // If word count differs, distribute time evenly and generate new IDs
            const avgWordDuration = segmentDuration / newWords.length
            updatedWords = newWords.map((text, index) => ({
                id: nanoid(),  // Generate new ID
                text,
                start_time: startTime + (index * avgWordDuration),
                end_time: startTime + ((index + 1) * avgWordDuration),
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

    const handleSplitSegment = (wordIndex: number) => {
        if (segmentIndex !== null && editedSegment) {
            handleSave()  // Save current changes first
            onSplitSegment?.(segmentIndex, wordIndex)
        }
    }

    // Add this new function to handle manual sync
    const startManualSync = () => {
        if (isManualSyncing) {
            setIsManualSyncing(false)
            setSyncWordIndex(-1)
            return
        }

        if (!editedSegment || !onPlaySegment) return

        setIsManualSyncing(true)
        setSyncWordIndex(0)
        // Start playing 3 seconds before segment start
        const startTime = (editedSegment.start_time ?? 0) - 3
        onPlaySegment(startTime)
    }

    // Handle play/stop button click
    const handlePlayButtonClick = () => {
        if (!segment?.start_time || !onPlaySegment) return

        if (isPlaying) {
            // Stop playback
            if (window.toggleAudioPlayback) {
                window.toggleAudioPlayback()
            }
        } else {
            // Start playback
            onPlaySegment(segment.start_time)
        }
    }

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="md"
            fullWidth
            onKeyDown={handleKeyDown}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    Edit Segment {segmentIndex}
                    {segment?.start_time !== null && onPlaySegment && (
                        <IconButton
                            size="small"
                            onClick={handlePlayButtonClick}
                            sx={{ padding: '4px' }}
                        >
                            {isPlaying ? (
                                <StopIcon />
                            ) : (
                                <PlayCircleOutlineIcon />
                            )}
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
                        startTime={timeRange.start}
                        endTime={timeRange.end}
                        onWordUpdate={handleWordChange}
                        currentTime={currentTime}
                        onPlaySegment={onPlaySegment}
                    />
                </Box>

                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">
                        Original Time Range: {originalSegment.start_time?.toFixed(2) ?? 'N/A'} - {originalSegment.end_time?.toFixed(2) ?? 'N/A'}
                        <br />
                        Current Time Range: {editedSegment.start_time?.toFixed(2) ?? 'N/A'} - {editedSegment.end_time?.toFixed(2) ?? 'N/A'}
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
                            <Typography variant="body2">
                                Press spacebar for word {syncWordIndex + 1} of {editedSegment?.words.length}
                            </Typography>
                        )}
                    </Box>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
                    {editedSegment.words.map((word, index) => (
                        <Box key={index} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                            <TextField
                                label={`Word ${index}`}
                                value={word.text}
                                onChange={(e) => handleWordChange(index, { text: e.target.value })}
                                fullWidth
                                size="small"
                            />
                            <TextField
                                label="Start Time"
                                value={word.start_time?.toFixed(2) ?? ''}
                                onChange={(e) => handleWordChange(index, { start_time: parseFloat(e.target.value) })}
                                type="number"
                                inputProps={{ step: 0.01 }}
                                sx={{ width: '150px' }}
                                size="small"
                            />
                            <TextField
                                label="End Time"
                                value={word.end_time?.toFixed(2) ?? ''}
                                onChange={(e) => handleWordChange(index, { end_time: parseFloat(e.target.value) })}
                                type="number"
                                inputProps={{ step: 0.01 }}
                                sx={{ width: '150px' }}
                                size="small"
                            />
                            <IconButton
                                onClick={() => handleRemoveWord(index)}
                                disabled={editedSegment.words.length <= 1}
                                sx={{ color: 'error.main' }}
                            >
                                <DeleteIcon fontSize="small" />
                            </IconButton>
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
                <Box sx={{ mr: 'auto', display: 'flex', gap: 1 }}>
                    <Button
                        startIcon={<AddIcon />}
                        onClick={() => segmentIndex !== null && onAddSegment?.(segmentIndex)}
                        color="primary"
                    >
                        Add Segment Before
                    </Button>
                    <Button
                        startIcon={<DeleteIcon />}
                        onClick={handleDelete}
                        color="error"
                    >
                        Delete Segment
                    </Button>
                </Box>
                <Button onClick={handleClose}>Cancel</Button>
                <Button onClick={() => {
                    cleanupManualSync()
                    onSave(editedSegment)
                }}>
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
                <MenuItem onClick={() => {
                    handleSplitSegment(selectedWordIndex!)
                    handleMenuClose()
                }}>
                    <SplitIcon sx={{ mr: 1 }} /> Split Segment After Word
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