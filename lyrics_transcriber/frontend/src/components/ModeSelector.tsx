import { ToggleButton, ToggleButtonGroup, Box, Typography, Tooltip } from '@mui/material';
import HighlightIcon from '@mui/icons-material/Highlight';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
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
                onChange={(_, newMode) => newMode === 'edit' && onChange(newMode)}
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
                <Tooltip title="Default mode; click words to edit that lyrics segment">
                    <ToggleButton 
                        value="edit"
                    >
                        <EditIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                        Edit
                    </ToggleButton>
                </Tooltip>
                
                <Tooltip title="Hold SHIFT and click words to highlight the matching anchor sequence in the reference lyrics">
                    <span>
                        <ToggleButton 
                            value="highlight"
                            disabled
                        >
                            <HighlightIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                            Highlight
                        </ToggleButton>
                    </span>
                </Tooltip>
                
                <Tooltip title="Hold CTRL and click words to delete them">
                    <span>
                        <ToggleButton 
                            value="delete_word"
                            disabled
                        >
                            <DeleteIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                            Delete
                        </ToggleButton>
                    </span>
                </Tooltip>
            </ToggleButtonGroup>
        </Box>
    );
} 