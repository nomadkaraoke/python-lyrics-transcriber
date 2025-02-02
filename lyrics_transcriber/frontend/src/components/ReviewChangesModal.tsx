import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Box,
    Typography,
    Paper,
    Collapse,
    IconButton,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { CorrectionData } from '../types'
import { useMemo, useState } from 'react'

interface ReviewChangesModalProps {
    open: boolean
    onClose: () => void
    originalData: CorrectionData
    updatedData: CorrectionData
    onSubmit: () => void
}

interface DiffResult {
    type: 'added' | 'removed' | 'modified'
    path: string
    segmentIndex?: number
    oldValue?: any
    newValue?: any
    wordChanges?: DiffResult[]
}

export default function ReviewChangesModal({
    open,
    onClose,
    originalData,
    updatedData,
    onSubmit
}: ReviewChangesModalProps) {
    const [expandedSegments, setExpandedSegments] = useState<number[]>([])

    const differences = useMemo(() => {
        const diffs: DiffResult[] = []

        // Compare corrected segments
        originalData.corrected_segments.forEach((segment, index) => {
            const updatedSegment = updatedData.corrected_segments[index]
            if (!updatedSegment) {
                diffs.push({
                    type: 'removed',
                    path: `Segment ${index}`,
                    segmentIndex: index,
                    oldValue: segment.text
                })
                return
            }

            const wordChanges: DiffResult[] = []

            // Compare word-level changes
            segment.words.forEach((word, wordIndex) => {
                const updatedWord = updatedSegment.words[wordIndex]
                if (!updatedWord) {
                    wordChanges.push({
                        type: 'removed',
                        path: `Word ${wordIndex}`,
                        oldValue: `"${word.text}" (${word.start_time.toFixed(4)} - ${word.end_time.toFixed(4)})`
                    })
                    return
                }

                if (word.text !== updatedWord.text ||
                    Math.abs(word.start_time - updatedWord.start_time) > 0.0001 ||
                    Math.abs(word.end_time - updatedWord.end_time) > 0.0001) {
                    wordChanges.push({
                        type: 'modified',
                        path: `Word ${wordIndex}`,
                        oldValue: `"${word.text}" (${word.start_time.toFixed(4)} - ${word.end_time.toFixed(4)})`,
                        newValue: `"${updatedWord.text}" (${updatedWord.start_time.toFixed(4)} - ${updatedWord.end_time.toFixed(4)})`
                    })
                }
            })

            // Check for added words
            if (updatedSegment.words.length > segment.words.length) {
                for (let i = segment.words.length; i < updatedSegment.words.length; i++) {
                    const word = updatedSegment.words[i]
                    wordChanges.push({
                        type: 'added',
                        path: `Word ${i}`,
                        newValue: `"${word.text}" (${word.start_time.toFixed(4)} - ${word.end_time.toFixed(4)})`
                    })
                }
            }

            if (segment.text !== updatedSegment.text ||
                segment.start_time !== updatedSegment.start_time ||
                segment.end_time !== updatedSegment.end_time ||
                wordChanges.length > 0) {
                diffs.push({
                    type: 'modified',
                    path: `Segment ${index}`,
                    segmentIndex: index,
                    oldValue: `"${segment.text}" (${segment.start_time.toFixed(4)} - ${segment.end_time.toFixed(4)})`,
                    newValue: `"${updatedSegment.text}" (${updatedSegment.start_time.toFixed(4)} - ${updatedSegment.end_time.toFixed(4)})`,
                    wordChanges: wordChanges.length > 0 ? wordChanges : undefined
                })
            }
        })

        return diffs
    }, [originalData, updatedData])

    const handleToggleSegment = (segmentIndex: number) => {
        setExpandedSegments(prev =>
            prev.includes(segmentIndex)
                ? prev.filter(i => i !== segmentIndex)
                : [...prev, segmentIndex]
        )
    }

    const renderDiff = (diff: DiffResult) => {
        const getColor = () => {
            switch (diff.type) {
                case 'added': return 'success.main'
                case 'removed': return 'error.main'
                case 'modified': return 'warning.main'
                default: return 'text.primary'
            }
        }

        const isExpanded = diff.segmentIndex !== undefined &&
            expandedSegments.includes(diff.segmentIndex)

        return (
            <Paper key={diff.path} sx={{ p: 2, mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                        <Typography color={getColor()} sx={{ fontWeight: 'bold' }}>
                            {diff.type.toUpperCase()}: {diff.path}
                        </Typography>
                        {diff.oldValue && (
                            <Typography color="error.main" sx={{ ml: 2 }}>
                                - {diff.oldValue}
                            </Typography>
                        )}
                        {diff.newValue && (
                            <Typography color="success.main" sx={{ ml: 2 }}>
                                + {diff.newValue}
                            </Typography>
                        )}
                    </Box>
                    {diff.wordChanges && (
                        <IconButton
                            onClick={() => handleToggleSegment(diff.segmentIndex!)}
                            sx={{
                                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                transition: 'transform 0.2s'
                            }}
                        >
                            <ExpandMoreIcon />
                        </IconButton>
                    )}
                </Box>

                {diff.wordChanges && (
                    <Collapse in={isExpanded}>
                        <Box sx={{ mt: 2, ml: 4 }}>
                            {diff.wordChanges.map((wordDiff, index) => (
                                <Box key={index}>
                                    <Typography color={getColor()} variant="body2">
                                        {wordDiff.type.toUpperCase()}: {wordDiff.path}
                                    </Typography>
                                    {wordDiff.oldValue && (
                                        <Typography color="error.main" variant="body2" sx={{ ml: 2 }}>
                                            - {wordDiff.oldValue}
                                        </Typography>
                                    )}
                                    {wordDiff.newValue && (
                                        <Typography color="success.main" variant="body2" sx={{ ml: 2 }}>
                                            + {wordDiff.newValue}
                                        </Typography>
                                    )}
                                </Box>
                            ))}
                        </Box>
                    </Collapse>
                )}
            </Paper>
        )
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
        >
            <DialogTitle>Review Changes</DialogTitle>
            <DialogContent dividers>
                {differences.length === 0 ? (
                    <Box>
                        <Typography color="text.secondary" sx={{ mb: 2 }}>
                            No changes detected. You can still submit to continue processing.
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Total segments: {updatedData.corrected_segments.length}
                        </Typography>
                    </Box>
                ) : (
                    <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {differences.length} change{differences.length !== 1 ? 's' : ''} detected:
                        </Typography>
                        {differences.map(renderDiff)}
                    </Box>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button
                    onClick={onSubmit}
                    variant="contained"
                >
                    Submit to Server
                </Button>
            </DialogActions>
        </Dialog>
    )
} 