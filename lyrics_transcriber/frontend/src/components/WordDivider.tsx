import { Box, Button, Typography } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import MergeIcon from '@mui/icons-material/CallMerge'
import CallSplitIcon from '@mui/icons-material/CallSplit'
import { SxProps, Theme } from '@mui/material/styles'

interface WordDividerProps {
    onAddWord: () => void
    onMergeWords?: () => void
    onAddSegmentBefore?: () => void
    onAddSegmentAfter?: () => void
    onSplitSegment?: () => void
    onMergeSegment?: () => void
    canMerge?: boolean
    isFirst?: boolean
    isLast?: boolean
    sx?: SxProps<Theme>
}

const buttonTextStyle = {
    color: 'rgba(0, 0, 0, 0.6)',
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    fontWeight: 400,
    fontSize: '0.7rem',
    lineHeight: '1.4375em',
    textTransform: 'none'
}

const buttonBaseStyle = {
    minHeight: 0,
    padding: '2px 8px',
    '& .MuiButton-startIcon': {
        marginRight: 0.5
    },
    '& .MuiSvgIcon-root': {
        fontSize: '1.2rem'
    }
}

export default function WordDivider({
    onAddWord,
    onMergeWords,
    onAddSegmentBefore,
    onAddSegmentAfter,
    onSplitSegment,
    onMergeSegment,
    canMerge = false,
    isFirst = false,
    isLast = false,
    sx = {}
}: WordDividerProps) {
    return (
        <Box
            sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '20px',
                my: -0.5,
                width: '50%',
                backgroundColor: '#fff',
                ...sx
            }}
        >
            <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                backgroundColor: '#fff',
                padding: '0 8px',
                zIndex: 1
            }}>
                <Button
                    onClick={onAddWord}
                    title="Add Word"
                    size="small"
                    startIcon={<AddIcon />}
                    sx={{
                        ...buttonBaseStyle,
                        color: 'primary.main',
                    }}
                >
                    <Typography sx={buttonTextStyle}>
                        Add Word
                    </Typography>
                </Button>
                {isFirst && onAddSegmentBefore && onMergeSegment && (
                    <>
                        <Button
                            onClick={onAddSegmentBefore}
                            title="Add Segment"
                            size="small"
                            startIcon={<AddIcon sx={{ transform: 'rotate(90deg)' }} />}
                            sx={{
                                ...buttonBaseStyle,
                                color: 'success.main',
                            }}
                        >
                            <Typography sx={buttonTextStyle}>
                                Add Segment
                            </Typography>
                        </Button>
                        <Button
                            onClick={onMergeSegment}
                            title="Merge with Previous Segment"
                            size="small"
                            startIcon={<MergeIcon sx={{ transform: 'rotate(90deg)' }} />}
                            sx={{
                                ...buttonBaseStyle,
                                color: 'warning.main',
                            }}
                        >
                            <Typography sx={buttonTextStyle}>
                                Merge Segment
                            </Typography>
                        </Button>
                    </>
                )}
                {onMergeWords && !isLast && (
                    <Button
                        onClick={onMergeWords}
                        title="Merge Words"
                        size="small"
                        startIcon={<MergeIcon sx={{ transform: 'rotate(90deg)' }} />}
                        disabled={!canMerge}
                        sx={{
                            ...buttonBaseStyle,
                            color: 'primary.main',
                        }}
                    >
                        <Typography sx={buttonTextStyle}>
                            Merge Words
                        </Typography>
                    </Button>
                )}
                {onSplitSegment && !isLast && (
                    <Button
                        onClick={onSplitSegment}
                        title="Split Segment"
                        size="small"
                        startIcon={<CallSplitIcon sx={{ transform: 'rotate(90deg)' }} />}
                        sx={{
                            ...buttonBaseStyle,
                            color: 'warning.main',
                        }}
                    >
                        <Typography sx={buttonTextStyle}>
                            Split Segment
                        </Typography>
                    </Button>
                )}
                {isLast && onAddSegmentAfter && onMergeSegment && (
                    <>
                        <Button
                            onClick={onAddSegmentAfter}
                            title="Add Segment"
                            size="small"
                            startIcon={<AddIcon sx={{ transform: 'rotate(90deg)' }} />}
                            sx={{
                                ...buttonBaseStyle,
                                color: 'success.main',
                            }}
                        >
                            <Typography sx={buttonTextStyle}>
                                Add Segment
                            </Typography>
                        </Button>
                        <Button
                            onClick={onMergeSegment}
                            title="Merge with Next Segment"
                            size="small"
                            startIcon={<MergeIcon sx={{ transform: 'rotate(90deg)' }} />}
                            sx={{
                                ...buttonBaseStyle,
                                color: 'warning.main',
                            }}
                        >
                            <Typography sx={buttonTextStyle}>
                                Merge Segment
                            </Typography>
                        </Button>
                    </>
                )}
            </Box>
        </Box>
    )
} 