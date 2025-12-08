import { Box, IconButton, Tooltip, useMediaQuery, useTheme } from '@mui/material'
import UndoIcon from '@mui/icons-material/Undo'
import EditIcon from '@mui/icons-material/Edit'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import { COLORS } from './shared/constants'
import { styled } from '@mui/material/styles'

interface CorrectionInfo {
    originalWord: string
    handler: string
    confidence: number
    source: string
    reason?: string
}

interface CorrectedWordWithActionsProps {
    word: string
    originalWord: string
    correction: CorrectionInfo
    onRevert: () => void
    onEdit: () => void
    onAccept: () => void
    onClick?: () => void
    backgroundColor?: string
    shouldFlash?: boolean
}

const WordContainer = styled(Box, {
    shouldForwardProp: (prop) => !['shouldFlash'].includes(prop as string)
})<{ shouldFlash?: boolean }>(({ shouldFlash }) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '2px',
    padding: '1px 3px',
    borderRadius: '2px',
    cursor: 'pointer',
    position: 'relative',
    backgroundColor: COLORS.corrected,
    animation: shouldFlash ? 'flash 1s ease-in-out infinite' : 'none',
    '@keyframes flash': {
        '0%, 100%': { opacity: 1 },
        '50%': { opacity: 0.5 }
    },
    '&:hover': {
        backgroundColor: '#c8e6c9'
    }
}))

const OriginalWordLabel = styled(Box)({
    position: 'absolute',
    top: '-14px',
    left: '0',
    fontSize: '0.6rem',
    color: '#666',
    textDecoration: 'line-through',
    opacity: 0.7,
    whiteSpace: 'nowrap',
    pointerEvents: 'none'
})

const ActionsContainer = styled(Box)({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '1px',
    marginLeft: '2px'
})

const ActionButton = styled(IconButton)(({ theme }) => ({
    padding: '2px',
    minWidth: '20px',
    minHeight: '20px',
    width: '20px',
    height: '20px',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    border: '1px solid rgba(0, 0, 0, 0.1)',
    '&:hover': {
        backgroundColor: 'rgba(255, 255, 255, 1)',
        transform: 'scale(1.1)'
    },
    '& .MuiSvgIcon-root': {
        fontSize: '0.875rem'
    },
    // Ensure minimum touch target on mobile
    [theme.breakpoints.down('sm')]: {
        minWidth: '28px',
        minHeight: '28px',
        width: '28px',
        height: '28px',
        padding: '4px'
    }
}))

export default function CorrectedWordWithActions({
    word,
    originalWord,
    onRevert,
    onEdit,
    onAccept,
    onClick,
    backgroundColor,
    shouldFlash
}: CorrectedWordWithActionsProps) {
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

    const handleAction = (e: React.MouseEvent, action: () => void) => {
        e.stopPropagation()
        action()
    }

    return (
        <WordContainer
            shouldFlash={shouldFlash}
            sx={{ backgroundColor: backgroundColor || COLORS.corrected }}
            onClick={onClick}
        >
            <OriginalWordLabel>{originalWord}</OriginalWordLabel>
            
            <Box
                component="span"
                sx={{
                    fontSize: '0.85rem',
                    lineHeight: 1.2,
                    fontWeight: 600
                }}
            >
                {word}
            </Box>

            <ActionsContainer>
                <Tooltip title="Revert to original" placement="top" arrow>
                    <ActionButton
                        size="small"
                        onClick={(e) => handleAction(e, onRevert)}
                        aria-label="revert correction"
                    >
                        <UndoIcon />
                    </ActionButton>
                </Tooltip>

                <Tooltip title="Edit correction" placement="top" arrow>
                    <ActionButton
                        size="small"
                        onClick={(e) => handleAction(e, onEdit)}
                        aria-label="edit correction"
                    >
                        <EditIcon />
                    </ActionButton>
                </Tooltip>

                {!isMobile && (
                    <Tooltip title="Accept correction" placement="top" arrow>
                        <ActionButton
                            size="small"
                            onClick={(e) => handleAction(e, onAccept)}
                            aria-label="accept correction"
                            sx={{ color: 'success.main' }}
                        >
                            <CheckCircleOutlineIcon />
                        </ActionButton>
                    </Tooltip>
                )}
            </ActionsContainer>
        </WordContainer>
    )
}

