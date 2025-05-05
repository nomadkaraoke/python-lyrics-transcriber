import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    Typography,
    ButtonGroup,
    IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { useState, useEffect } from 'react';

interface TimingOffsetModalProps {
    open: boolean;
    onClose: () => void;
    currentOffset: number;
    onApply: (offsetMs: number) => void;
}

export default function TimingOffsetModal({
    open,
    onClose,
    currentOffset,
    onApply,
}: TimingOffsetModalProps) {
    const [offsetMs, setOffsetMs] = useState(currentOffset);

    // Reset the offset value when the modal opens
    useEffect(() => {
        if (open) {
            setOffsetMs(currentOffset);
        }
    }, [open, currentOffset]);

    // Handle preset buttons click
    const handlePresetClick = (value: number) => {
        setOffsetMs((prev) => prev + value);
    };

    // Handle direct input change
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value === '' ? 0 : parseInt(e.target.value, 10);
        if (!isNaN(value)) {
            setOffsetMs(value);
        }
    };

    // Apply the offset
    const handleApply = () => {
        onApply(offsetMs);
        onClose();
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{
                sx: {
                    overflowY: 'visible',
                }
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                Adjust Global Timing Offset
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent>
                <Box sx={{ mb: 3, mt: 1 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                        Adjust the timing of all words in the transcription. Positive values delay the timing, negative values advance it.
                    </Typography>
                    
                    <Typography variant="body2" sx={{ fontStyle: 'italic', mb: 2 }}>
                        Note: This offset is applied globally but doesn't modify the original timestamps.
                    </Typography>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Typography variant="body1" sx={{ mr: 2 }}>
                            Offset:
                        </Typography>
                        <TextField
                            value={offsetMs}
                            onChange={handleInputChange}
                            type="number"
                            variant="outlined"
                            size="small"
                            InputProps={{
                                endAdornment: <Typography variant="body2" sx={{ ml: 1 }}>ms</Typography>,
                            }}
                            sx={{ width: 120 }}
                        />
                    </Box>
                    
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Typography variant="body2">Quick adjust:</Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                            <ButtonGroup size="small">
                                <Button onClick={() => handlePresetClick(-100)}>-100ms</Button>
                                <Button onClick={() => handlePresetClick(-50)}>-50ms</Button>
                                <Button onClick={() => handlePresetClick(-10)}>-10ms</Button>
                            </ButtonGroup>
                            <ButtonGroup size="small">
                                <Button onClick={() => handlePresetClick(10)}>+10ms</Button>
                                <Button onClick={() => handlePresetClick(50)}>+50ms</Button>
                                <Button onClick={() => handlePresetClick(100)}>+100ms</Button>
                            </ButtonGroup>
                        </Box>
                    </Box>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button 
                    onClick={handleApply} 
                    variant="contained"
                    color={offsetMs === 0 ? "warning" : "primary"}
                >
                    {offsetMs === 0 ? "Remove Offset" : "Apply Offset"}
                </Button>
            </DialogActions>
        </Dialog>
    );
} 