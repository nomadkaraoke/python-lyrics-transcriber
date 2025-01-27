import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Grid,
    Typography,
    Box,
    TextField,
    Button,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { ModalContent } from './LyricsAnalyzer'
import { WordCorrection } from '../types'
import { useState, useEffect } from 'react'

interface DetailsModalProps {
    open: boolean
    content: ModalContent | null
    onClose: () => void
    onUpdateCorrection?: (position: number, updatedWords: string[]) => void
    isReadOnly?: boolean
}

export default function DetailsModal({
    open,
    content,
    onClose,
    onUpdateCorrection,
    isReadOnly = true
}: DetailsModalProps) {
    const [editedWord, setEditedWord] = useState('')
    const [isEditing, setIsEditing] = useState(false)

    useEffect(() => {
        // Reset editing state when modal content changes
        if (content?.type === 'gap') {
            setEditedWord(content.data.word)
            setIsEditing(false)
        }
    }, [content])

    if (!content) return null

    const handleStartEdit = () => {
        console.group('DetailsModal Edit Debug')
        console.log('Starting edit for content:', JSON.stringify(content, null, 2))
        if (content.type === 'gap') {
            console.log('Setting edited word:', content.data.word)
            setEditedWord(content.data.word)
        }
        console.groupEnd()
        setIsEditing(true)
    }

    const handleSaveEdit = () => {
        console.group('DetailsModal Save Debug')
        console.log('Current content:', JSON.stringify(content, null, 2))
        console.log('Edited word:', editedWord)

        if (content?.type === 'gap' && onUpdateCorrection) {
            // Use the editedWord state instead of the original word
            console.log('Saving edit with new word:', editedWord)
            onUpdateCorrection(
                content.data.position,
                [editedWord]  // Use the edited word here
            )
        }
        console.groupEnd()
        onClose()
    }

    const handleCancelEdit = () => {
        if (content.type === 'gap') {
            setEditedWord(content.data.word)
            setIsEditing(false)
        }
    }

    const handleWordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        console.log('Word changed to:', event.target.value)
        setEditedWord(event.target.value)
    }

    const renderContent = () => {
        switch (content.type) {
            case 'anchor':
                return (
                    <Grid container spacing={2}>
                        <GridItem title="Text" value={`"${content.data.text}"`} />
                        <GridItem title="Words" value={content.data.words.join(' ')} />
                        <GridItem title="Position" value={content.data.position} />
                        <GridItem
                            title="Reference Positions"
                            value={
                                <Box component="pre" sx={{ margin: 0, fontSize: '0.875rem' }}>
                                    {JSON.stringify(content.data.reference_positions, null, 2)}
                                </Box>
                            }
                        />
                        <GridItem
                            title="Confidence"
                            value={`${(content.data.confidence * 100).toFixed(2)}%`}
                        />
                        <GridItem title="Length" value={`${content.data.length} words`} />
                        {content.data.phrase_score && (
                            <>
                                <GridItem title="Phrase Type" value={content.data.phrase_score.phrase_type} />
                                <GridItem
                                    title="Scores"
                                    value={
                                        <Box sx={{ pl: 2 }}>
                                            <Typography>
                                                Total: {content.data?.total_score?.toFixed(2) ?? 'N/A'}
                                            </Typography>
                                            <Typography>
                                                Natural Break: {content.data?.phrase_score?.natural_break_score?.toFixed(2) ?? 'N/A'}
                                            </Typography>
                                            <Typography>
                                                Length: {content.data.phrase_score.length_score.toFixed(2)}
                                            </Typography>
                                            <Typography>
                                                Phrase: {content.data.phrase_score.total_score.toFixed(2)}
                                            </Typography>
                                        </Box>
                                    }
                                />
                            </>
                        )}
                    </Grid>
                )

            case 'gap':
                return (
                    <Grid container spacing={2}>
                        <GridItem
                            title="Transcribed Text"
                            value={`"${content.data.text}"`}
                        />
                        <GridItem
                            title="Current Text"
                            value={
                                isEditing ? (
                                    <Box>
                                        <TextField
                                            value={editedWord}
                                            onChange={handleWordChange}
                                            fullWidth
                                            label="Edit word"
                                            variant="outlined"
                                            size="small"
                                        />
                                        <Box sx={{ display: 'flex', gap: 1 }}>
                                            <Button
                                                variant="contained"
                                                onClick={handleSaveEdit}
                                            >
                                                Save Changes
                                            </Button>
                                            <Button
                                                variant="outlined"
                                                onClick={handleCancelEdit}
                                            >
                                                Cancel
                                            </Button>
                                        </Box>
                                    </Box>
                                ) : (
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                        <Typography>
                                            "{content.data.words.map(word => {
                                                const correction = content.data.corrections.find(
                                                    c => c.original_word === word
                                                );
                                                return correction ? correction.corrected_word : word;
                                            }).join(' ')}"
                                        </Typography>
                                        {!isReadOnly && (
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                onClick={handleStartEdit}
                                            >
                                                Edit
                                            </Button>
                                        )}
                                    </Box>
                                )
                            }
                        />
                        <GridItem title="Position" value={content.data.position} />
                        <GridItem title="Length" value={`${content.data.length} words`} />
                        {content.data.corrections.length > 0 && (
                            <GridItem
                                title="Corrections"
                                value={
                                    <Box sx={{ pl: 2 }}>
                                        {content.data.corrections.map((correction: WordCorrection, i: number) => (
                                            <Box key={i} sx={{ mb: 2 }}>
                                                <Typography>
                                                    "{correction.original_word}" → "{correction.corrected_word}"
                                                </Typography>
                                                <Typography>
                                                    Confidence: {(correction.confidence * 100).toFixed(2)}%
                                                </Typography>
                                                <Typography>Source: {correction.source}</Typography>
                                                <Typography>Reason: {correction.reason}</Typography>
                                                {Object.keys(correction.alternatives).length > 0 && (
                                                    <Typography component="pre" sx={{ fontSize: '0.875rem' }}>
                                                        Alternatives: {JSON.stringify(correction.alternatives, null, 2)}
                                                    </Typography>
                                                )}
                                            </Box>
                                        ))}
                                    </Box>
                                }
                            />
                        )}
                        <GridItem
                            title="Reference Words"
                            value={
                                <Box component="pre" sx={{ margin: 0, fontSize: '0.875rem' }}>
                                    {JSON.stringify(content.data.reference_words, null, 2)}
                                </Box>
                            }
                        />
                        {content.data.preceding_anchor && (
                            <GridItem
                                title="Preceding Anchor"
                                value={`"${content.data.preceding_anchor.text}"`}
                            />
                        )}
                        {content.data.following_anchor && (
                            <GridItem
                                title="Following Anchor"
                                value={`"${content.data.following_anchor.text}"`}
                            />
                        )}
                    </Grid>
                )

            default:
                return null
        }
    }

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
                {content.type.charAt(0).toUpperCase() + content.type.slice(1)} Details
            </DialogTitle>
            <DialogContent dividers>{renderContent()}</DialogContent>
        </Dialog>
    )
}

interface GridItemProps {
    title: string
    value: string | number | React.ReactNode
}

function GridItem({ title, value }: GridItemProps) {
    return (
        <>
            <Grid item xs={4}>
                <Typography variant="subtitle1" fontWeight="bold">
                    {title}
                </Typography>
            </Grid>
            <Grid item xs={8}>
                {typeof value === 'string' || typeof value === 'number' ? (
                    <Typography>{value}</Typography>
                ) : (
                    value
                )}
            </Grid>
        </>
    )
} 