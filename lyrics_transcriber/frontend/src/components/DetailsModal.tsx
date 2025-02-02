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
                        {/* ... rest of anchor details rendering ... */}
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
                                const correction = content.data.corrections.find(
                                    c => c.original_word === word
                                )
                                return correction ? correction.corrected_word : word
                            }).join(' ')}"`}
                        />
                        {/* ... rest of gap details rendering ... */}
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