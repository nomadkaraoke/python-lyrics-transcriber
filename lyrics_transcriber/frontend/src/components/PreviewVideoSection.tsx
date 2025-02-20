import { Box, Typography, CircularProgress, Alert, Button } from '@mui/material'
import { useState, useEffect } from 'react'
import { ApiClient } from '../api'
import { CorrectionData } from '../types'

interface PreviewVideoSectionProps {
    apiClient: ApiClient | null
    isModalOpen: boolean
    updatedData: CorrectionData
    videoRef?: React.RefObject<HTMLVideoElement>
}

export default function PreviewVideoSection({
    apiClient,
    isModalOpen,
    updatedData,
    videoRef
}: PreviewVideoSectionProps) {
    const [previewState, setPreviewState] = useState<{
        status: 'loading' | 'ready' | 'error';
        videoUrl?: string;
        error?: string;
    }>({ status: 'loading' });

    // Generate preview when modal opens
    useEffect(() => {
        if (isModalOpen && apiClient) {
            const generatePreview = async () => {
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

            generatePreview();
        }
    }, [isModalOpen, apiClient, updatedData]);

    if (!apiClient) return null;

    return (
        <Box sx={{ mb: 2 }}>
            {previewState.status === 'loading' && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
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
                                onClick={() => {
                                    // Re-trigger the effect by toggling isModalOpen
                                    setPreviewState({ status: 'loading' });
                                }}
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
                <Box sx={{
                    width: '100%',
                    margin: '0',
                }}>
                    <video
                        ref={videoRef}
                        controls
                        autoPlay
                        src={previewState.videoUrl}
                        style={{
                            display: 'block',
                            width: '100%',
                            height: 'auto',
                        }}
                    >
                        Your browser does not support the video tag.
                    </video>
                </Box>
            )}
        </Box>
    );
} 