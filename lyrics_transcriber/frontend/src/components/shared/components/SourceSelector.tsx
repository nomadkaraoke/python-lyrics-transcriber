import { Box, Button } from '@mui/material'

interface SourceSelectorProps {
    currentSource: 'genius' | 'spotify'
    onSourceChange: (source: 'genius' | 'spotify') => void
}

export function SourceSelector({ currentSource, onSourceChange }: SourceSelectorProps) {
    return (
        <Box>
            <Button
                size="small"
                variant={currentSource === 'genius' ? 'contained' : 'outlined'}
                onClick={() => onSourceChange('genius')}
                sx={{ mr: 1 }}
            >
                Genius
            </Button>
            <Button
                size="small"
                variant={currentSource === 'spotify' ? 'contained' : 'outlined'}
                onClick={() => onSourceChange('spotify')}
            >
                Spotify
            </Button>
        </Box>
    )
} 