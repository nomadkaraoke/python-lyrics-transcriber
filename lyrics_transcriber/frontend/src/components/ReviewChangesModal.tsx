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
    oldValue?: string
    newValue?: string
    wordChanges?: DiffResult[]
}

// Add interfaces for the word and segment structures
interface Word {
    text: string
    start_time: number | null
    end_time: number | null
    id?: string
}

interface Segment {
    text: string
    start_time: number | null
    end_time: number | null
    words: Word[]
    id?: string
}

const normalizeWordForComparison = (word: Word): Omit<Word, 'id'> => ({
    text: word.text,
    start_time: word.start_time ?? 0,  // Default to 0 for comparison
    end_time: word.end_time ?? 0       // Default to 0 for comparison
})

const normalizeSegmentForComparison = (segment: Segment): Omit<Segment, 'id'> => ({
    text: segment.text,
    start_time: segment.start_time ?? 0,  // Default to 0 for comparison
    end_time: segment.end_time ?? 0,      // Default to 0 for comparison
    words: segment.words.map(normalizeWordForComparison)
})

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

        originalData.corrected_segments.forEach((originalSegment, index) => {
            const updatedSegment = updatedData.corrected_segments[index]
            if (!updatedSegment) {
                diffs.push({
                    type: 'removed',
                    path: `Segment ${index}`,
                    segmentIndex: index,
                    oldValue: originalSegment.text
                })
                return
            }

            const normalizedOriginal = normalizeSegmentForComparison(originalSegment)
            const normalizedUpdated = normalizeSegmentForComparison(updatedSegment)
            const wordChanges: DiffResult[] = []

            // Compare word-level changes
            normalizedOriginal.words.forEach((word, wordIndex) => {
                const updatedWord = normalizedUpdated.words[wordIndex]
                if (!updatedWord) {
                    wordChanges.push({
                        type: 'removed',
                        path: `Word ${wordIndex}`,
                        oldValue: `"${word.text}" (${word.start_time?.toFixed(4) ?? 'N/A'} - ${word.end_time?.toFixed(4) ?? 'N/A'})`
                    })
                    return
                }

                if (word.text !== updatedWord.text ||
                    Math.abs((word.start_time ?? 0) - (updatedWord.start_time ?? 0)) > 0.0001 ||
                    Math.abs((word.end_time ?? 0) - (updatedWord.end_time ?? 0)) > 0.0001) {
                    wordChanges.push({
                        type: 'modified',
                        path: `Word ${wordIndex}`,
                        oldValue: `"${word.text}" (${word.start_time?.toFixed(4) ?? 'N/A'} - ${word.end_time?.toFixed(4) ?? 'N/A'})`,
                        newValue: `"${updatedWord.text}" (${updatedWord.start_time?.toFixed(4) ?? 'N/A'} - ${updatedWord.end_time?.toFixed(4) ?? 'N/A'})`
                    })
                }
            })

            // Check for added words
            if (normalizedUpdated.words.length > normalizedOriginal.words.length) {
                for (let i = normalizedOriginal.words.length; i < normalizedUpdated.words.length; i++) {
                    const word = normalizedUpdated.words[i]
                    wordChanges.push({
                        type: 'added',
                        path: `Word ${i}`,
                        newValue: `"${word.text}" (${word.start_time?.toFixed(4) ?? 'N/A'} - ${word.end_time?.toFixed(4) ?? 'N/A'})`
                    })
                }
            }

            // Compare segment-level changes
            if (normalizedOriginal.text !== normalizedUpdated.text ||
                Math.abs((normalizedOriginal.start_time ?? 0) - (normalizedUpdated.start_time ?? 0)) > 0.0001 ||
                Math.abs((normalizedOriginal.end_time ?? 0) - (normalizedUpdated.end_time ?? 0)) > 0.0001 ||
                wordChanges.length > 0) {
                diffs.push({
                    type: 'modified',
                    path: `Segment ${index}`,
                    segmentIndex: index,
                    oldValue: `"${normalizedOriginal.text}" (${normalizedOriginal.start_time?.toFixed(4) ?? 'N/A'} - ${normalizedOriginal.end_time?.toFixed(4) ?? 'N/A'})`,
                    newValue: `"${normalizedUpdated.text}" (${normalizedUpdated.start_time?.toFixed(4) ?? 'N/A'} - ${normalizedUpdated.end_time?.toFixed(4) ?? 'N/A'})`,
                    wordChanges: wordChanges.length > 0 ? wordChanges : undefined
                })
            }
        })

        // Check for added segments
        if (updatedData.corrected_segments.length > originalData.corrected_segments.length) {
            for (let i = originalData.corrected_segments.length; i < updatedData.corrected_segments.length; i++) {
                const segment = updatedData.corrected_segments[i]
                diffs.push({
                    type: 'added',
                    path: `Segment ${i}`,
                    segmentIndex: i,
                    newValue: `"${segment.text}" (${segment.start_time?.toFixed(4) ?? 'N/A'} - ${segment.end_time?.toFixed(4) ?? 'N/A'})`
                })
            }
        }

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