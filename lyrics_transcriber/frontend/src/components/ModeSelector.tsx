import { ToggleButton, ToggleButtonGroup, Box, Typography } from '@mui/material';
import HighlightIcon from '@mui/icons-material/Highlight';
import EditIcon from '@mui/icons-material/Edit';
import { InteractionMode } from '../types';

interface ModeSelectorProps {
    effectiveMode: InteractionMode;
    onChange: (mode: InteractionMode) => void;
}

export default function ModeSelector({ effectiveMode, onChange }: ModeSelectorProps) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, height: '32px' }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                Mode:
            </Typography>
            <ToggleButtonGroup
                value={effectiveMode}
                exclusive
                onChange={(_, newMode) => newMode && onChange(newMode)}
                size="small"
                sx={{ 
                    height: '32px',
                    '& .MuiToggleButton-root': {
                        padding: '3px 8px',
                        fontSize: '0.75rem',
                        height: '32px'
                    }
                }}
            >
                <ToggleButton 
                    value="edit"
                    title="Click to edit segments and make corrections in the transcription view"
                >
                    <EditIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                    Edit
                </ToggleButton>
                <ToggleButton 
                    value="highlight"
                    title="Click words in the transcription view to highlight the matching anchor sequence in the reference lyrics. You can also hold SHIFT to temporarily activate this mode."
                >
                    <HighlightIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                    Highlight
                </ToggleButton>
            </ToggleButtonGroup>
        </Box>
    );
} 