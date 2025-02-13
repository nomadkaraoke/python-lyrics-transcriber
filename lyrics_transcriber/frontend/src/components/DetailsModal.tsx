import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Grid,
    Typography,
    Box
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { ModalContent } from './LyricsAnalyzer'
import { WordCorrection } from '@/types'

interface DetailsModalProps {
    open: boolean
    content: ModalContent | null
    onClose: () => void
    allCorrections?: WordCorrection[]
}

export default function DetailsModal({
    open,
    content,
    onClose,
    allCorrections = []
}: DetailsModalProps) {
    if (!content) return null

    const getCurrentWord = () => {
        if (content.type === 'gap') {
            return content.data.word
        } else if (content.type === 'anchor') {
            return content.data.word ?? content.data.words[0]
        }
        return ''
    }

    const isCorrected = content.type === 'gap' && (
        content.data.corrections?.length > 0 ||
        allCorrections.some(c => c.corrected_word_id === content.data.wordId)
    )

    const getAllCorrections = () => {
        if (content.type !== 'gap') return []

        return [
            ...(content.data.corrections || []),
            ...allCorrections.filter(c => c.corrected_word_id === content.data.wordId)
        ]
    }

    const renderContent = () => {
        switch (content.type) {
            case 'anchor':
                return (
                    <Grid container spacing={2}>
                        <GridItem
                            title="Selected Word"
                            value={`"${getCurrentWord()}"`}
                        />
                        <GridItem
                            title="Full Text"
                            value={`"${content.data.words.join(' ')}"`}
                        />
                        <GridItem title="Word ID" value={content.data.wordId} />
                        <GridItem
                            title="Length"
                            value={`${content.data.words.length} words`}
                        />
                        <GridItem
                            title="Reference Words"
                            value={content.data.reference_words ?
                                Object.entries(content.data.reference_words).map(([source, words]) => (
                                    `${source}: ${words.map(w => w.text).join(', ')}`
                                )).join('\n') : 'No reference words'
                            }
                        />
                        <GridItem title="Confidence" value={content.data.confidence?.toFixed(3) ?? 'N/A'} />
                        {content.data.phrase_score && (
                            <GridItem
                                title="Phrase Score Details"
                                value={
                                    <>
                                        <Typography>Type: {content.data.phrase_score.phrase_type}</Typography>
                                        <Typography>Natural Break: {content.data.phrase_score.natural_break_score?.toFixed(3) ?? 'N/A'}</Typography>
                                        <Typography>Length: {content.data.phrase_score.length_score?.toFixed(3) ?? 'N/A'}</Typography>
                                        <Typography>Total: {content.data.phrase_score.total_score?.toFixed(3) ?? 'N/A'}</Typography>
                                    </>
                                }
                            />
                        )}
                        <GridItem title="Total Score" value={content.data.total_score?.toFixed(3) ?? 'N/A'} />
                    </Grid>
                )

            case 'gap':
                return (
                    <Grid container spacing={2}>
                        <GridItem
                            title="Selected Word"
                            value={`"${getCurrentWord()}"`}
                        />
                        <GridItem
                            title="Current Text"
                            value={`"${content.data.words?.map(word => {
                                const wordCorrection = content.data.corrections?.find(
                                    c => c.original_word === word
                                )
                                return wordCorrection ? wordCorrection.corrected_word : word
                            }).join(' ') ?? content.data.word}"`}
                        />
                        <GridItem
                            title="Word ID"
                            value={content.data.wordId}
                        />
                        <GridItem
                            title="Length"
                            value={`${content.data.length} words`}
                        />
                        {content.data.preceding_anchor && (
                            <GridItem
                                title="Preceding Anchor"
                                value={`"${content.data.preceding_anchor.words.join(' ')}"`}
                            />
                        )}
                        <GridItem
                            title="Transcribed Text"
                            value={`"${content.data.text}"`}
                        />
                        {content.data.following_anchor && (
                            <GridItem
                                title="Following Anchor"
                                value={`"${content.data.following_anchor.words.join(' ')}"`}
                            />
                        )}
                        {content.data.reference_words && (
                            <GridItem
                                title="Reference Words"
                                value={
                                    <>
                                        {content.data.reference_words.spotify && (
                                            <Typography>
                                                Spotify: "{content.data.reference_words.spotify.map(w => w.text).join(' ')}"
                                            </Typography>
                                        )}
                                        {content.data.reference_words.genius && (
                                            <Typography>
                                                Genius: "{content.data.reference_words.genius.map(w => w.text).join(' ')}"
                                            </Typography>
                                        )}
                                    </>
                                }
                            />
                        )}
                        {isCorrected && (
                            <GridItem
                                title="Correction Details"
                                value={
                                    <>
                                        {getAllCorrections().map((correction, index) => (
                                            <Box key={index} sx={{ mb: 2, p: 1, border: '1px solid #ccc', borderRadius: '4px' }}>
                                                <Typography variant="subtitle2" fontWeight="bold">Correction {index + 1}</Typography>
                                                <Typography>Original: <strong>"{correction.original_word}"</strong></Typography>
                                                <Typography>Corrected: <strong>"{correction.corrected_word}"</strong></Typography>
                                                <Typography>Word ID: {correction.word_id}</Typography>
                                                <Typography>Confidence: {correction.confidence?.toFixed(3) ?? 'N/A'}</Typography>
                                                <Typography>Handler: {correction.handler}</Typography>
                                                <Typography>Source: {correction.source}</Typography>
                                                <Typography>Reason: {correction.reason}</Typography>
                                                {correction.is_deletion && <Typography>Is Deletion: Yes</Typography>}
                                                {correction.split_total && (
                                                    <Typography>Split: {correction.split_index} of {correction.split_total}</Typography>
                                                )}
                                                {correction.alternatives && Object.entries(correction.alternatives).length > 0 && (
                                                    <>
                                                        <Typography>Alternatives:</Typography>
                                                        <Box sx={{ pl: 2 }}>
                                                            {Object.entries(correction.alternatives).map(([word, score]) => (
                                                                <Typography key={word}>
                                                                    "{word}": {score?.toFixed(3) ?? 'N/A'}
                                                                </Typography>
                                                            ))}
                                                        </Box>
                                                    </>
                                                )}
                                            </Box>
                                        ))}
                                    </>
                                }
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
                {content.type === 'gap' && (isCorrected ? 'Corrected ' : 'Uncorrected ')}
                {content.type.charAt(0).toUpperCase() + content.type.slice(1)} Details - "{getCurrentWord()}"
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