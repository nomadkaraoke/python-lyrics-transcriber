import { useState, useEffect } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    TextField,
    Slider,
    Typography,
    Box,
    Paper,
    Chip,
    Alert,
    SelectChangeEvent
} from '@mui/material'
import { CorrectionAnnotation, CorrectionAnnotationType, CorrectionAction } from '../types'

interface CorrectionAnnotationModalProps {
    open: boolean
    onClose: () => void
    onSave: (annotation: Omit<CorrectionAnnotation, 'annotation_id' | 'timestamp'>) => void
    onSkip: () => void
    // Context about the correction being made
    originalText: string
    correctedText: string
    wordIdsAffected: string[]
    // Optional: What the AI suggested
    agenticProposal?: {
        action: string
        replacement_text?: string
        confidence: number
        reason: string
        gap_category?: string
    }
    // Reference lyrics that were consulted
    referenceSources: string[]
    // Song metadata
    audioHash: string
    artist: string
    title: string
    sessionId: string
    gapId?: string
}

const ANNOTATION_TYPES: { value: CorrectionAnnotationType; label: string; description: string }[] = [
    { 
        value: 'SOUND_ALIKE' as CorrectionAnnotationType, 
        label: 'Sound-Alike Error', 
        description: 'Homophones or similar-sounding words (e.g., "out" vs "now")' 
    },
    { 
        value: 'BACKGROUND_VOCALS' as CorrectionAnnotationType, 
        label: 'Background Vocals', 
        description: 'Backing vocals that should be removed from karaoke' 
    },
    { 
        value: 'EXTRA_WORDS' as CorrectionAnnotationType, 
        label: 'Extra Filler Words', 
        description: 'Transcription added words like "And", "But", "Well"' 
    },
    { 
        value: 'PUNCTUATION_ONLY' as CorrectionAnnotationType, 
        label: 'Punctuation/Style Only', 
        description: 'Only punctuation or capitalization differences' 
    },
    { 
        value: 'REPEATED_SECTION' as CorrectionAnnotationType, 
        label: 'Repeated Section', 
        description: 'Chorus or verse repetition not in condensed references' 
    },
    { 
        value: 'COMPLEX_MULTI_ERROR' as CorrectionAnnotationType, 
        label: 'Complex Multi-Error', 
        description: 'Multiple different error types in one section' 
    },
    { 
        value: 'AMBIGUOUS' as CorrectionAnnotationType, 
        label: 'Ambiguous', 
        description: 'Unclear without listening to audio' 
    },
    { 
        value: 'NO_ERROR' as CorrectionAnnotationType, 
        label: 'No Error', 
        description: 'Transcription matches at least one reference source' 
    },
    { 
        value: 'MANUAL_EDIT' as CorrectionAnnotationType, 
        label: 'Manual Edit', 
        description: 'Human-initiated correction not from detected gap' 
    }
]

const CONFIDENCE_LABELS: { [key: number]: string } = {
    1: '1 - Very Uncertain',
    2: '2 - Somewhat Uncertain',
    3: '3 - Neutral',
    4: '4 - Fairly Confident',
    5: '5 - Very Confident'
}

export default function CorrectionAnnotationModal({
    open,
    onClose,
    onSave,
    onSkip,
    originalText,
    correctedText,
    wordIdsAffected,
    agenticProposal,
    referenceSources,
    audioHash,
    artist,
    title,
    sessionId,
    gapId
}: CorrectionAnnotationModalProps) {
    const [annotationType, setAnnotationType] = useState<CorrectionAnnotationType>('MANUAL_EDIT' as CorrectionAnnotationType)
    const [actionTaken, setActionTaken] = useState<CorrectionAction>('REPLACE' as CorrectionAction)
    const [confidence, setConfidence] = useState<number>(3)
    const [reasoning, setReasoning] = useState<string>('')
    const [agenticAgreed, setAgenticAgreed] = useState<boolean>(false)
    const [error, setError] = useState<string>('')

    // Pre-fill if we have an agentic proposal
    useEffect(() => {
        if (agenticProposal && agenticProposal.gap_category) {
            setAnnotationType(agenticProposal.gap_category as CorrectionAnnotationType)
            // Check if human correction matches AI suggestion
            const agreed = agenticProposal.replacement_text 
                ? correctedText.toLowerCase().includes(agenticProposal.replacement_text.toLowerCase())
                : false
            setAgenticAgreed(agreed)
        }
    }, [agenticProposal, correctedText])

    // Determine action type based on correction
    useEffect(() => {
        if (originalText === correctedText) {
            setActionTaken('NO_ACTION' as CorrectionAction)
        } else if (correctedText === '') {
            setActionTaken('DELETE' as CorrectionAction)
        } else if (originalText === '') {
            setActionTaken('INSERT' as CorrectionAction)
        } else {
            setActionTaken('REPLACE' as CorrectionAction)
        }
    }, [originalText, correctedText])

    const handleSave = () => {
        // Validate
        if (reasoning.length < 10) {
            setError('Reasoning must be at least 10 characters')
            return
        }

        const annotation: Omit<CorrectionAnnotation, 'annotation_id' | 'timestamp'> = {
            audio_hash: audioHash,
            gap_id: gapId || null,
            annotation_type: annotationType,
            action_taken: actionTaken,
            original_text: originalText,
            corrected_text: correctedText,
            confidence,
            reasoning,
            word_ids_affected: wordIdsAffected,
            agentic_proposal: agenticProposal || null,
            agentic_category: agenticProposal?.gap_category || null,
            agentic_agreed: agenticAgreed,
            reference_sources_consulted: referenceSources,
            artist,
            title,
            session_id: sessionId
        }

        onSave(annotation)
        handleClose()
    }

    const handleClose = () => {
        // Reset form
        setAnnotationType('MANUAL_EDIT' as CorrectionAnnotationType)
        setConfidence(3)
        setReasoning('')
        setError('')
        setAgenticAgreed(false)
        onClose()
    }

    const handleSkipAndClose = () => {
        handleClose()
        onSkip()
    }

    return (
        <Dialog 
            open={open} 
            onClose={handleClose}
            maxWidth="md"
            fullWidth
        >
            <DialogTitle>
                <Typography variant="h6">Annotate Your Correction</Typography>
                <Typography variant="caption" color="text.secondary">
                    Help improve the AI by explaining your correction
                </Typography>
            </DialogTitle>

            <DialogContent dividers>
                {/* Show what changed */}
                <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Your Correction:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <Box sx={{ flex: 1 }}>
                            <Typography variant="caption" color="error">Original:</Typography>
                            <Typography 
                                sx={{ 
                                    textDecoration: 'line-through', 
                                    color: 'error.main',
                                    fontFamily: 'monospace'
                                }}
                            >
                                {originalText || '(empty)'}
                            </Typography>
                        </Box>
                        <Typography variant="h6">→</Typography>
                        <Box sx={{ flex: 1 }}>
                            <Typography variant="caption" color="success.main">Corrected:</Typography>
                            <Typography 
                                sx={{ 
                                    color: 'success.main',
                                    fontWeight: 'bold',
                                    fontFamily: 'monospace'
                                }}
                            >
                                {correctedText || '(empty)'}
                            </Typography>
                        </Box>
                    </Box>
                </Paper>

                {/* Show AI suggestion if available */}
                {agenticProposal && (
                    <Alert 
                        severity={agenticAgreed ? "success" : "info"} 
                        sx={{ mb: 3 }}
                    >
                        <Typography variant="subtitle2" gutterBottom>
                            AI Suggestion:
                        </Typography>
                        <Typography variant="body2">
                            Category: <strong>{agenticProposal.gap_category}</strong>
                        </Typography>
                        <Typography variant="body2">
                            Action: <strong>{agenticProposal.action}</strong>
                            {agenticProposal.replacement_text && ` → "${agenticProposal.replacement_text}"`}
                        </Typography>
                        <Typography variant="body2">
                            Reason: {agenticProposal.reason}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                            {agenticAgreed 
                                ? '✓ Your correction matches the AI suggestion' 
                                : '✗ Your correction differs from the AI suggestion'}
                        </Typography>
                    </Alert>
                )}

                {/* Reference sources */}
                {referenceSources.length > 0 && (
                    <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                            Reference Sources Consulted:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {referenceSources.map(source => (
                                <Chip key={source} label={source} size="small" />
                            ))}
                        </Box>
                    </Box>
                )}

                {/* Annotation type */}
                <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel>Correction Type *</InputLabel>
                    <Select
                        value={annotationType}
                        label="Correction Type *"
                        onChange={(e: SelectChangeEvent) => setAnnotationType(e.target.value as CorrectionAnnotationType)}
                    >
                        {ANNOTATION_TYPES.map(type => (
                            <MenuItem key={type.value} value={type.value}>
                                <Box>
                                    <Typography variant="body1">{type.label}</Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {type.description}
                                    </Typography>
                                </Box>
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>

                {/* Confidence slider */}
                <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Confidence in Your Correction *
                    </Typography>
                    <Slider
                        value={confidence}
                        onChange={(_, newValue) => setConfidence(newValue as number)}
                        min={1}
                        max={5}
                        step={1}
                        marks
                        valueLabelDisplay="auto"
                        valueLabelFormat={(value) => CONFIDENCE_LABELS[value]}
                    />
                    <Typography variant="caption" color="text.secondary">
                        {CONFIDENCE_LABELS[confidence]}
                    </Typography>
                </Box>

                {/* Reasoning text area */}
                <TextField
                    fullWidth
                    multiline
                    rows={4}
                    label="Reasoning *"
                    placeholder="Explain why this correction is needed (minimum 10 characters)..."
                    value={reasoning}
                    onChange={(e) => {
                        setReasoning(e.target.value)
                        setError('')
                    }}
                    error={!!error}
                    helperText={error || `${reasoning.length}/10 minimum characters`}
                    required
                />
            </DialogContent>

            <DialogActions>
                <Button onClick={handleSkipAndClose} color="inherit">
                    Skip
                </Button>
                <Button onClick={handleSave} variant="contained" color="primary">
                    Save & Continue
                </Button>
            </DialogActions>
        </Dialog>
    )
}

