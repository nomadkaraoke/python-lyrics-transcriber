import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Grid,
    Typography,
    Box,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { ModalContent } from './LyricsAnalyzer'
import { Correction } from '../types'

interface DetailsModalProps {
    open: boolean
    content: ModalContent | null
    onClose: () => void
}

export default function DetailsModal({ open, content, onClose }: DetailsModalProps) {
    if (!content) return null

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
                                                Total: {content.data.total_score.toFixed(2)}
                                            </Typography>
                                            <Typography>
                                                Natural Break: {content.data.phrase_score.natural_break_score.toFixed(2)}
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
                            title="Corrected Text"
                            value={`"${content.data.words.map(word => {
                                const correction = content.data.corrections.find(c => c.original_word === word);
                                return correction ? correction.corrected_word : word;
                            }).join(' ')}"`}
                        />
                        <GridItem title="Position" value={content.data.position} />
                        <GridItem title="Length" value={`${content.data.length} words`} />
                        {content.data.corrections.length > 0 && (
                            <GridItem
                                title="Corrections"
                                value={
                                    <Box sx={{ pl: 2 }}>
                                        {content.data.corrections.map((correction: Correction, i: number) => (
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
    value: React.ReactNode
}

function GridItem({ title, value }: GridItemProps) {
    return (
        <>
            <Grid item xs={4}>
                <Typography color="text.secondary" fontWeight="medium">
                    {title}
                </Typography>
            </Grid>
            <Grid item xs={8}>
                <Typography>{value}</Typography>
            </Grid>
        </>
    )
} 