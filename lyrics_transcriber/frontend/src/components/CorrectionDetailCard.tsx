import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Box,
    Typography,
    Chip,
    LinearProgress,
    IconButton,
    useMediaQuery,
    useTheme,
    Slide
} from '@mui/material'
import { TransitionProps } from '@mui/material/transitions'
import CloseIcon from '@mui/icons-material/Close'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { forwardRef } from 'react'

interface CorrectionDetailCardProps {
    open: boolean
    onClose: () => void
    originalWord: string
    correctedWord: string
    category: string | null
    confidence: number
    reason: string
    handler: string
    source: string
    onRevert: () => void
    onEdit: () => void
    onAccept: () => void
}

// Slide transition for mobile
const Transition = forwardRef(function Transition(
    props: TransitionProps & {
        children: React.ReactElement<any, any>
    },
    ref: React.Ref<unknown>
) {
    return <Slide direction="up" ref={ref} {...props} />
})

// Format category name for display
const formatCategory = (category: string | null): string => {
    if (!category) return 'Unknown'
    return category
        .split('_')
        .map(word => word.charAt(0) + word.slice(1).toLowerCase())
        .join(' ')
}

// Get emoji/icon for category
const getCategoryIcon = (category: string | null): string => {
    if (!category) return '📝'
    const icons: Record<string, string> = {
        'SOUND_ALIKE': '🎵',
        'PUNCTUATION_ONLY': '✏️',
        'BACKGROUND_VOCALS': '🎤',
        'EXTRA_WORDS': '➕',
        'REPEATED_SECTION': '🔁',
        'COMPLEX_MULTI_ERROR': '🔧',
        'AMBIGUOUS': '❓',
        'NO_ERROR': '✅'
    }
    return icons[category] || '📝'
}

// Get confidence color
const getConfidenceColor = (confidence: number): 'error' | 'warning' | 'success' => {
    if (confidence < 0.6) return 'error'
    if (confidence < 0.8) return 'warning'
    return 'success'
}

export default function CorrectionDetailCard({
    open,
    onClose,
    originalWord,
    correctedWord,
    category,
    confidence,
    reason,
    handler,
    source,
    onRevert,
    onEdit,
    onAccept
}: CorrectionDetailCardProps) {
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
    const fullScreen = isMobile

    return (
        <Dialog
            open={open}
            onClose={onClose}
            fullScreen={fullScreen}
            maxWidth="sm"
            fullWidth
            TransitionComponent={isMobile ? Transition : undefined}
            PaperProps={{
                sx: {
                    ...(isMobile && {
                        position: 'fixed',
                        bottom: 0,
                        m: 0,
                        borderRadius: '16px 16px 0 0',
                        maxHeight: '85vh'
                    })
                }
            }}
        >
            <DialogTitle sx={{ pb: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6" sx={{ fontSize: '1.1rem', fontWeight: 600 }}>
                        Correction Details
                    </Typography>
                    <IconButton
                        aria-label="close"
                        onClick={onClose}
                        size="small"
                    >
                        <CloseIcon />
                    </IconButton>
                </Box>
            </DialogTitle>

            <DialogContent>
                {/* Original → Corrected */}
                <Box sx={{ mb: 3 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                        Change
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box
                            sx={{
                                px: 2,
                                py: 1,
                                bgcolor: 'error.lighter',
                                borderRadius: 1,
                                textDecoration: 'line-through',
                                flex: 1,
                                textAlign: 'center'
                            }}
                        >
                            <Typography variant="body1" sx={{ fontWeight: 500 }}>
                                {originalWord}
                            </Typography>
                        </Box>
                        <ArrowForwardIcon color="action" />
                        <Box
                            sx={{
                                px: 2,
                                py: 1,
                                bgcolor: 'success.lighter',
                                borderRadius: 1,
                                flex: 1,
                                textAlign: 'center'
                            }}
                        >
                            <Typography variant="body1" sx={{ fontWeight: 600 }}>
                                {correctedWord}
                            </Typography>
                        </Box>
                    </Box>
                </Box>

                {/* Category */}
                {category && (
                    <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                            Category
                        </Typography>
                        <Chip
                            label={`${getCategoryIcon(category)} ${formatCategory(category)}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.875rem' }}
                        />
                    </Box>
                )}

                {/* Confidence */}
                <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                            Confidence
                        </Typography>
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            {(confidence * 100).toFixed(0)}%
                        </Typography>
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={confidence * 100}
                        color={getConfidenceColor(confidence)}
                        sx={{ height: 8, borderRadius: 1 }}
                    />
                </Box>

                {/* Reasoning */}
                <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                        Reasoning
                    </Typography>
                    <Typography
                        variant="body2"
                        sx={{
                            p: 1.5,
                            bgcolor: 'grey.50',
                            borderRadius: 1,
                            border: '1px solid',
                            borderColor: 'grey.200',
                            lineHeight: 1.6
                        }}
                    >
                        {reason}
                    </Typography>
                </Box>

                {/* Metadata */}
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                        label={`Handler: ${handler}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                    />
                    <Chip
                        label={`Source: ${source}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                    />
                </Box>
            </DialogContent>

            <DialogActions sx={{ p: 2, gap: 1, flexDirection: isMobile ? 'column' : 'row' }}>
                <Button
                    onClick={() => {
                        onRevert()
                        onClose()
                    }}
                    variant="outlined"
                    color="error"
                    fullWidth={isMobile}
                    sx={{ minHeight: isMobile ? '44px' : '36px' }}
                >
                    Revert to Original
                </Button>
                <Button
                    onClick={() => {
                        onEdit()
                        onClose()
                    }}
                    variant="outlined"
                    fullWidth={isMobile}
                    sx={{ minHeight: isMobile ? '44px' : '36px' }}
                >
                    Edit Correction
                </Button>
                <Button
                    onClick={() => {
                        onAccept()
                        onClose()
                    }}
                    variant="contained"
                    color="success"
                    fullWidth={isMobile}
                    sx={{ minHeight: isMobile ? '44px' : '36px' }}
                >
                    Mark as Correct
                </Button>
            </DialogActions>
        </Dialog>
    )
}

