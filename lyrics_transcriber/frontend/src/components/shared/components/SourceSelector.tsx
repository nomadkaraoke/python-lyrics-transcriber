import { Box, Button } from '@mui/material'

export interface SourceSelectorProps {
    currentSource: string
    onSourceChange: (source: string) => void
    availableSources: string[]
}

export function SourceSelector({ currentSource, onSourceChange, availableSources }: SourceSelectorProps) {
    return (
        <Box>
            {availableSources.map((source) => (
                <Button
                    key={source}
                    size="small"
                    variant={currentSource === source ? 'contained' : 'outlined'}
                    onClick={() => onSourceChange(source)}
                    sx={{ mr: 1 }}
                >
                    {/* Capitalize first letter of source */}
                    {source.charAt(0).toUpperCase() + source.slice(1)}
                </Button>
            ))}
        </Box>
    )
} 