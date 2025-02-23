import { ToggleButton, ToggleButtonGroup, Box, Typography } from '@mui/material';
import HighlightIcon from '@mui/icons-material/Highlight';
import InfoIcon from '@mui/icons-material/Info';
import EditIcon from '@mui/icons-material/Edit';
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
                <ToggleButton 
                    value="edit"
                    title="Click to edit segments and make corrections in the transcription view"
                >
                    <EditIcon sx={{ mr: 1 }} />
                    Edit
                </ToggleButton>
                <ToggleButton 
                    value="details"
                    title="Click words to view detailed information about anchors and gaps. You can also hold CTRL to temporarily activate this mode."
                >
                    <InfoIcon sx={{ mr: 1 }} />
                    Details
                </ToggleButton>
                <ToggleButton 
                    value="highlight"
                    title="Click words in the transcription view to highlight the matching anchor sequence in the reference lyrics. You can also hold SHIFT to temporarily activate this mode."
                >
                    <HighlightIcon sx={{ mr: 1 }} />
                    Highlight
                </ToggleButton>
            </ToggleButtonGroup>
        </Box>
    );
} 