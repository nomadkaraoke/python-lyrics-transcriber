import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Grid,
    Typography
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { ModalContent } from './LyricsAnalyzer'

interface DetailsModalProps {
    open: boolean
    content: ModalContent | null
    onClose: () => void
}

export default function DetailsModal({
    open,
    content,
    onClose,
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

    const renderContent = () => {
        // Move declaration outside of case block
        const correction = content.type === 'gap'
            ? content.data.corrections.find(c => c.original_word === content.data.word)
            : null

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
                            value={`"${content.data.text}"`}
                        />
                        <GridItem title="Position" value={content.data.position} />
                        <GridItem title="Length" value={`${content.data.length} words`} />
                        <GridItem
                            title="Reference Positions"
                            value={Object.entries(content.data.reference_positions).map(([source, pos]) => (
                                `${source}: ${pos}`
                            )).join(', ')}
                        />
                        <GridItem title="Confidence" value={content.data.confidence.toFixed(3)} />
                        <GridItem
                            title="Phrase Score Details"
                            value={
                                <>
                                    <Typography>Type: {content.data.phrase_score.phrase_type}</Typography>
                                    <Typography>Natural Break: {content.data.phrase_score.natural_break_score.toFixed(3)}</Typography>
                                    <Typography>Length: {content.data.phrase_score.length_score.toFixed(3)}</Typography>
                                    <Typography>Total: {content.data.phrase_score.total_score.toFixed(3)}</Typography>
                                </>
                            }
                        />
                        <GridItem title="Total Score" value={content.data.total_score.toFixed(3)} />
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
                            title="Transcribed Text"
                            value={`"${content.data.text}"`}
                        />
                        <GridItem
                            title="Current Text"
                            value={`"${content.data.words.map(word => {
                                const wordCorrection = content.data.corrections.find(
                                    c => c.original_word === word
                                )
                                return wordCorrection ? wordCorrection.corrected_word : word
                            }).join(' ')}"`}
                        />
                        <GridItem
                            title="Position"
                            value={content.data.position}
                        />
                        <GridItem
                            title="Length"
                            value={`${content.data.length} words`}
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
                        {content.data.reference_words && (
                            <GridItem
                                title="Reference Words"
                                value={
                                    <>
                                        {Object.entries(content.data.reference_words).map(([source, words]) => (
                                            <Typography key={source}>
                                                {source}: "{words.join(' ')}"
                                            </Typography>
                                        ))}
                                    </>
                                }
                            />
                        )}
                        {correction && (
                            <>
                                <GridItem
                                    title="Correction Details"
                                    value={
                                        <>
                                            <Typography>Original: "{correction.original_word}"</Typography>
                                            <Typography>Corrected: "{correction.corrected_word}"</Typography>
                                            <Typography>Confidence: {correction.confidence.toFixed(3)}</Typography>
                                            <Typography>Source: {correction.source}</Typography>
                                            <Typography>Reason: {correction.reason}</Typography>
                                            {correction.is_deletion && <Typography>Is Deletion: Yes</Typography>}
                                            {correction.split_total && (
                                                <Typography>Split: {correction.split_index} of {correction.split_total}</Typography>
                                            )}
                                        </>
                                    }
                                />
                                {Object.entries(correction.alternatives).length > 0 && (
                                    <GridItem
                                        title="Alternatives"
                                        value={
                                            <>
                                                {Object.entries(correction.alternatives).map(([word, score]) => (
                                                    <Typography key={word}>
                                                        "{word}": {score.toFixed(3)}
                                                    </Typography>
                                                ))}
                                            </>
                                        }
                                    />
                                )}
                            </>
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