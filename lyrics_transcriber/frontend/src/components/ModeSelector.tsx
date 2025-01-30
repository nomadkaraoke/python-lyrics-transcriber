import { ToggleButton, ToggleButtonGroup, Box, Typography } from '@mui/material';
import HighlightIcon from '@mui/icons-material/Highlight';
import InfoIcon from '@mui/icons-material/Info';
import { InteractionMode } from '../types';

interface ModeSelectorProps {
    mode: InteractionMode;
    onChange: (mode: InteractionMode) => void;
}

export default function ModeSelector({ mode, onChange }: ModeSelectorProps) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
                Click Mode:
            </Typography>
            <ToggleButtonGroup
                value={mode}
                exclusive
                onChange={(_, newMode) => newMode && onChange(newMode)}
                size="small"
            >
                <ToggleButton value="highlight">
                    <HighlightIcon sx={{ mr: 1 }} />
                    Highlight
                </ToggleButton>
                <ToggleButton value="details">
                    <InfoIcon sx={{ mr: 1 }} />
                    Details
                </ToggleButton>
            </ToggleButtonGroup>
        </Box>
    );
} 