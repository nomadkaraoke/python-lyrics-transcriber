import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Box,
    Typography,
    Paper
} from '@mui/material'
import { CorrectionData } from '../types'
import { useMemo, useRef, useEffect } from 'react'
import { ApiClient } from '../api'
import PreviewVideoSection from './PreviewVideoSection'
import { CloudUpload, ArrowBack } from '@mui/icons-material'

interface ReviewChangesModalProps {
    open: boolean
    onClose: () => void
    originalData: CorrectionData
    updatedData: CorrectionData
    onSubmit: () => void
    apiClient: ApiClient | null
    setModalSpacebarHandler: (handler: (() => (e: KeyboardEvent) => void) | undefined) => void
    timingOffsetMs?: number
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
    onSubmit,
    apiClient,
    setModalSpacebarHandler,
    timingOffsetMs = 0
}: ReviewChangesModalProps) {
    // Add ref to video element
    const videoRef = useRef<HTMLVideoElement>(null)

    // Stop audio playback when modal opens
    useEffect(() => {
        if (open && window.isAudioPlaying && window.toggleAudioPlayback) {
            window.toggleAudioPlayback()
        }
    }, [open])

    // Add effect to handle spacebar
    useEffect(() => {
        if (open) {
            setModalSpacebarHandler(() => (e: KeyboardEvent) => {
                if (e.type === 'keydown') {
                    e.preventDefault()
                    e.stopPropagation()

                    if (videoRef.current) {
                        if (videoRef.current.paused) {
                            videoRef.current.play()
                        } else {
                            videoRef.current.pause()
                        }
                    }
                }
            })
        } else {
            setModalSpacebarHandler(undefined)
        }

        return () => {
            setModalSpacebarHandler(undefined)
        }
    }, [open, setModalSpacebarHandler])

    // Debug logging for timing offset
    useEffect(() => {
        if (open) {
            console.log(`[TIMING] ReviewChangesModal opened - timingOffsetMs: ${timingOffsetMs}ms`);
        }
    }, [open, timingOffsetMs]);

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

    const renderCompactDiff = (diff: DiffResult) => {
        if (diff.type !== 'modified') {
            // For added/removed segments, show them as before but in a single line
            return (
                <Typography
                    key={diff.path}
                    color={diff.type === 'added' ? 'success.main' : 'error.main'}
                    sx={{ mb: 0.5 }}
                >
                    {diff.segmentIndex}: {diff.type === 'added' ? '+ ' : '- '}
                    {diff.type === 'added' ? diff.newValue : diff.oldValue}
                </Typography>
            )
        }

        // For modified segments, create a unified inline diff view
        const oldText = diff.oldValue?.split('"')[1] || ''
        const newText = diff.newValue?.split('"')[1] || ''
        const oldWords = oldText.split(' ')
        const newWords = newText.split(' ')

        // Extract timing info and format with 2 decimal places
        const timingMatch = diff.newValue?.match(/\(([\d.]+) - ([\d.]+)\)/)
        const timing = timingMatch ?
            `(${parseFloat(timingMatch[1]).toFixed(2)} - ${parseFloat(timingMatch[2]).toFixed(2)})` :
            ''

        // Create unified diff of words
        const unifiedDiff = []
        let i = 0, j = 0

        while (i < oldWords.length || j < newWords.length) {
            if (i < oldWords.length && j < newWords.length && oldWords[i] === newWords[j]) {
                // Unchanged word
                unifiedDiff.push({ type: 'unchanged', text: oldWords[i] })
                i++
                j++
            } else if (i < oldWords.length && (!newWords[j] || oldWords[i] !== newWords[j])) {
                // Deleted word
                unifiedDiff.push({ type: 'deleted', text: oldWords[i] })
                i++
            } else if (j < newWords.length) {
                // Added word
                unifiedDiff.push({ type: 'added', text: newWords[j] })
                j++
            }
        }

        return (
            <Box key={diff.path} sx={{ mb: 0.5, display: 'flex', alignItems: 'center' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mr: 1, minWidth: '30px' }}>
                    {diff.segmentIndex}:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', flexGrow: 1, alignItems: 'center' }}>
                    {unifiedDiff.map((word, idx) => (
                        <Typography
                            key={idx}
                            component="span"
                            color={
                                word.type === 'unchanged' ? 'text.primary' :
                                    word.type === 'deleted' ? 'error.main' : 'success.main'
                            }
                            sx={{
                                textDecoration: word.type === 'deleted' ? 'line-through' : 'none',
                                mr: 0.5
                            }}
                        >
                            {word.text}
                        </Typography>
                    ))}
                    <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                        {timing}
                    </Typography>
                </Box>
            </Box>
        )
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
        >
            <DialogTitle>Preview Video (With Vocals)</DialogTitle>
            <DialogContent
                dividers
                sx={{
                    p: 0,  // Remove default padding
                    '&:first-of-type': { pt: 0 }  // Remove default top padding
                }}
            >
                <PreviewVideoSection
                    apiClient={apiClient}
                    isModalOpen={open}
                    updatedData={updatedData}
                    videoRef={videoRef}  // Pass the ref to PreviewVideoSection
                    timingOffsetMs={timingOffsetMs}
                />

                <Box sx={{ p: 2, mt: 0 }}>
                    {timingOffsetMs !== 0 && (
                        <Typography variant="body2" fontWeight="bold" sx={{ mt: 1 }}>
                            Global Timing Offset applied to all words: {timingOffsetMs > 0 ? '+' : ''}{timingOffsetMs}ms
                        </Typography>
                    )}
                    {differences.length === 0 ? (
                        <Box>
                            <Typography color="text.secondary">
                                No manual corrections detected. If everything looks good in the preview, click submit and the server will generate the final karaoke video.
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total segments: {updatedData.corrected_segments.length}
                            </Typography>
                        </Box>
                    ) : (
                        <Box>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                {differences.length} segment{differences.length !== 1 ? 's' : ''} modified:
                            </Typography>
                            <Paper sx={{ p: 2 }}>
                                {differences.map(renderCompactDiff)}
                            </Paper>
                        </Box>
                    )}
                </Box>
            </DialogContent>
            <DialogActions>
                <Button 
                    onClick={onClose}
                    color="warning"
                    startIcon={<ArrowBack />}
                    sx={{ mr: 'auto' }}
                >
                    Cancel
                </Button>
                <Button
                    onClick={onSubmit}
                    variant="contained"
                    color="success"
                    endIcon={<CloudUpload />}
                >
                    Complete Review
                </Button>
            </DialogActions>
        </Dialog>
    )
} 