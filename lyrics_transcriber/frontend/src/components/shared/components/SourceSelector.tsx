import { Box, Button } from '@mui/material'

export interface SourceSelectorProps {
    currentSource: string
    onSourceChange: (source: string) => void
    availableSources: string[]
}

export function SourceSelector({ currentSource, onSourceChange, availableSources }: SourceSelectorProps) {
    return (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.3 }}>
            {availableSources.map((source) => (
                <Button
                    key={source}
                    size="small"
                    variant={currentSource === source ? 'contained' : 'outlined'}
                    onClick={() => onSourceChange(source)}
                    sx={{ 
                        mr: 0,
                        py: 0.2,
                        px: 0.8,
                        minWidth: 'auto',
                        fontSize: '0.7rem',
                        lineHeight: 1.2
                    }}
                >
                    {/* Capitalize first letter of source */}
                    {source.charAt(0).toUpperCase() + source.slice(1)}
                </Button>
            ))}
        </Box>
    )
} 