import { ToggleButton, ToggleButtonGroup, Box, Typography } from '@mui/material';
import HighlightIcon from '@mui/icons-material/Highlight';
import InfoIcon from '@mui/icons-material/Info';
import { InteractionMode } from '../types';

interface ModeSelectorProps {
    effectiveMode: InteractionMode;
    onChange: (mode: InteractionMode) => void;
}

export default function ModeSelector({ effectiveMode, onChange }: ModeSelectorProps) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
                Click Mode:
            </Typography>
            <ToggleButtonGroup
                value={effectiveMode}
                exclusive
                onChange={(_, newMode) => newMode && onChange(newMode)}
                size="small"
            >
                <ToggleButton value="details">
                    <InfoIcon sx={{ mr: 1 }} />
                    Details
                </ToggleButton>
                <ToggleButton value="highlight">
                    <HighlightIcon sx={{ mr: 1 }} />
                    Highlight
                </ToggleButton>
            </ToggleButtonGroup>
        </Box>
    );
} 