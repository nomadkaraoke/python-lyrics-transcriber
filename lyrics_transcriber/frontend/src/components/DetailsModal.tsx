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
import { WordCorrection, ReferenceSource, AnchorSequence } from '../types'
import { getWordsFromIds } from './shared/utils/wordUtils'

interface DetailsModalProps {
    open: boolean
    content: ModalContent | null
    onClose: () => void
    allCorrections: WordCorrection[]
    referenceLyrics?: Record<string, ReferenceSource>
}

function formatReferenceWords(content: ModalContent | null, referenceLyrics?: Record<string, ReferenceSource>): string {
    if (!content || !referenceLyrics) return ''

    return Object.entries(content.data.reference_word_ids)
        .map(([source, wordIds]) => {
            const words = getWordsFromIds(
                referenceLyrics[source]?.segments ?? [],
                wordIds
            )
            return `${source}: "${words.map(w => w.text).join(' ')}"`
        })
        .join('\n')
}

function getAnchorText(anchorId: string | null, anchors: AnchorSequence[], referenceLyrics?: Record<string, ReferenceSource>): string {
    if (!anchorId || !referenceLyrics) return anchorId || ''

    const anchor = anchors.find(a => a.id === anchorId)
    if (!anchor) return anchorId

    // Get the first source's words as representative text
    const firstSource = Object.entries(anchor.reference_word_ids)[0]
    if (!firstSource) return anchorId

    const [source, wordIds] = firstSource
    const words = getWordsFromIds(
        referenceLyrics[source]?.segments ?? [],
        wordIds
    )
    return `${anchorId} ("${words.map(w => w.text).join(' ')}")`
}

export default function DetailsModal({
    open,
    content,
    onClose,
    allCorrections,
    referenceLyrics
}: DetailsModalProps) {
    if (!content) return null

    const referenceWordsText = formatReferenceWords(content, referenceLyrics)
    const relevantCorrections = content.type === 'gap' ? allCorrections.filter(c =>
        c.word_id === content.data.wordId ||
        c.corrected_word_id === content.data.wordId ||
        content.data.transcribed_word_ids.includes(c.word_id)
    ) : []
    const isCorrected = content.type === 'gap' && relevantCorrections.length > 0

    const getCurrentWord = () => {
        if (content.type === 'gap') {
            return content.data.word
        } else if (content.type === 'anchor') {
            return content.data.word ?? ''
        }
        return ''
    }

    const renderContent = () => {
        const anchorWords = content.type === 'anchor' ? content.data.transcribed_word_ids?.length ?? 0 : 0

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
                            value={`"${content.data.word ?? ''}"`}
                        />
                        <GridItem title="Word ID" value={content.data.wordId} />
                        <GridItem
                            title="Length"
                            value={`${anchorWords} words`}
                        />
                        <GridItem
                            title="Reference Words"
                            value={
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{referenceWordsText}</pre>
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
                            title="Word ID"
                            value={content.data.wordId}
                        />
                        <GridItem
                            title="Length"
                            value={`${content.data.transcribed_word_ids?.length ?? 0} words`}
                        />
                        {content.data.preceding_anchor_id && (
                            <GridItem
                                title="Preceding Anchor"
                                value={getAnchorText(content.data.preceding_anchor_id, content.data.anchor_sequences, referenceLyrics)}
                            />
                        )}
                        {content.data.following_anchor_id && (
                            <GridItem
                                title="Following Anchor"
                                value={getAnchorText(content.data.following_anchor_id, content.data.anchor_sequences, referenceLyrics)}
                            />
                        )}
                        <GridItem
                            title="Reference Words"
                            value={
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{referenceWordsText}</pre>
                            }
                        />
                        {isCorrected && (
                            <GridItem
                                title="Correction Details"
                                value={
                                    <>
                                        {relevantCorrections.map((correction, index) => (
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
                                                                    "{word}": {(score || 0).toFixed(3)}
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
            maxWidth="md"
            fullWidth
        >
            <DialogTitle>
                {content.type === 'gap' && (
                    isCorrected ? 'Corrected ' : 'Uncorrected '
                )}
                {content.type.charAt(0).toUpperCase() + content.type.slice(1)} Details - "{getCurrentWord()}"
                <IconButton
                    aria-label="close"
                    onClick={onClose}
                    sx={{ position: 'absolute', right: 8, top: 8 }}
                >
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent>
                {renderContent()}
            </DialogContent>
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