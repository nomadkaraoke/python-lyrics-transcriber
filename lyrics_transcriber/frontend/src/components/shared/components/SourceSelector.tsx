import { Box, Button } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'

export interface SourceSelectorProps {
    currentSource: string
    onSourceChange: (source: string) => void
    availableSources: string[]
    onAddLyrics?: () => void
}

export function SourceSelector({ currentSource, onSourceChange, availableSources, onAddLyrics }: SourceSelectorProps) {
    return (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.3, alignItems: 'center' }}>
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
            {onAddLyrics && (
                <Button
                    size="small"
                    variant="outlined"
                    onClick={onAddLyrics}
                    startIcon={<AddIcon sx={{ fontSize: '0.9rem' }} />}
                    sx={{
                        mr: 0,
                        py: 0.2,
                        px: 0.8,
                        minWidth: 'auto',
                        fontSize: '0.7rem',
                        lineHeight: 1.2,
                        '& .MuiButton-startIcon': {
                            marginLeft: '-5px',
                            marginRight: '1px',
                            marginTop: '-1px'
                        }
                    }}
                >New</Button>
            )}
        </Box>
    )
} 