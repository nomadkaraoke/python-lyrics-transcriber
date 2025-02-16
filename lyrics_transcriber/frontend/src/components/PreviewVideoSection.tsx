import { Box, Button, Typography, CircularProgress, Alert } from '@mui/material'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import { useState, useEffect } from 'react'
import { ApiClient } from '../api'
import { CorrectionData } from '../types';

interface PreviewVideoSectionProps {
    apiClient: ApiClient | null
    isModalOpen: boolean
    updatedData: CorrectionData
}

export default function PreviewVideoSection({ apiClient, isModalOpen, updatedData }: PreviewVideoSectionProps) {
    const [previewState, setPreviewState] = useState<{
        status: 'idle' | 'loading' | 'ready' | 'error';
        videoUrl?: string;
        error?: string;
    }>({ status: 'idle' });

    // Reset preview state when modal closes
    useEffect(() => {
        if (!isModalOpen) {
            setPreviewState({ status: 'idle' });
        }
    }, [isModalOpen]);

    const handleGeneratePreview = async () => {
        if (!apiClient) return;

        setPreviewState({ status: 'loading' });
        try {
            const response = await apiClient.generatePreviewVideo(updatedData);

            if (response.status === 'error') {
                setPreviewState({
                    status: 'error',
                    error: response.message || 'Failed to generate preview video'
                });
                return;
            }

            if (!response.preview_hash) {
                setPreviewState({
                    status: 'error',
                    error: 'No preview hash received from server'
                });
                return;
            }

            const videoUrl = apiClient.getPreviewVideoUrl(response.preview_hash);
            setPreviewState({
                status: 'ready',
                videoUrl
            });
        } catch (error) {
            setPreviewState({
                status: 'error',
                error: (error as Error).message || 'Failed to generate preview video'
            });
        }
    };

    if (!apiClient) return null;

    return (
        <Box sx={{ mt: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
                Preview Video
            </Typography>

            {previewState.status === 'idle' && (
                <Button
                    variant="outlined"
                    startIcon={<PlayArrowIcon />}
                    onClick={handleGeneratePreview}
                    sx={{ mb: 2 }}
                >
                    Generate Preview Video
                </Button>
            )}

            {previewState.status === 'loading' && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <CircularProgress size={24} />
                    <Typography>Generating preview video...</Typography>
                </Box>
            )}

            {previewState.status === 'error' && (
                <Box sx={{ mb: 2 }}>
                    <Alert
                        severity="error"
                        action={
                            <Button
                                color="inherit"
                                size="small"
                                onClick={handleGeneratePreview}
                            >
                                Retry
                            </Button>
                        }
                    >
                        {previewState.error}
                    </Alert>
                </Box>
            )}

            {previewState.status === 'ready' && previewState.videoUrl && (
                <Box sx={{ mb: 2 }}>
                    <video
                        controls
                        width="100%"
                        src={previewState.videoUrl}
                        style={{ maxHeight: '400px' }}
                    >
                        Your browser does not support the video tag.
                    </video>
                </Box>
            )}
        </Box>
    );
} 