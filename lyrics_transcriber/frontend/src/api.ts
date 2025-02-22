import { CorrectionData } from './types';
import { validateCorrectionData } from './validation';

// New file to handle API communication
export interface ApiClient {
    getCorrectionData: () => Promise<CorrectionData>;
    submitCorrections: (data: CorrectionData) => Promise<void>;
    getAudioUrl: (audioHash: string) => string;
    generatePreviewVideo: (data: CorrectionData) => Promise<PreviewVideoResponse>;
    getPreviewVideoUrl: (previewHash: string) => string;
    updateHandlers: (enabledHandlers: string[]) => Promise<CorrectionData>;
    isUpdatingHandlers?: boolean;
    addLyrics: (source: string, lyrics: string) => Promise<CorrectionData>;
}

// Add new interface for the minimal update payload
interface CorrectionUpdate {
    corrections: CorrectionData['corrections'];
    corrected_segments: CorrectionData['corrected_segments'];
}

// Add new interface for preview response
interface PreviewVideoResponse {
    status: "success" | "error";
    preview_hash?: string;
    message?: string;
}

// Add new interface for adding lyrics
interface AddLyricsRequest {
    source: string;
    lyrics: string;
}

export class LiveApiClient implements ApiClient {
    constructor(private baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\/$/, '')
    }

    public isUpdatingHandlers = false;

    async getCorrectionData(): Promise<CorrectionData> {
        const response = await fetch(`${this.baseUrl}/correction-data`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        const rawData = await response.json();

        try {
            // This will throw if validation fails
            return validateCorrectionData(rawData);
        } catch (error) {
            console.error('Data validation failed:', error);
            throw new Error('Invalid data received from server: missing or incorrect fields');
        }
    }

    async submitCorrections(data: CorrectionData): Promise<void> {
        // Extract only the needed fields
        const updatePayload: CorrectionUpdate = {
            corrections: data.corrections,
            corrected_segments: data.corrected_segments
        };

        const response = await fetch(`${this.baseUrl}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatePayload)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
    }

    getAudioUrl(audioHash: string): string {
        return `${this.baseUrl}/audio/${audioHash}`
    }

    async generatePreviewVideo(data: CorrectionData): Promise<PreviewVideoResponse> {
        // Extract only the needed fields, just like in submitCorrections
        const updatePayload: CorrectionUpdate = {
            corrections: data.corrections,
            corrected_segments: data.corrected_segments
        };

        const response = await fetch(`${this.baseUrl}/preview-video`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatePayload)
        });

        if (!response.ok) {
            return {
                status: 'error',
                message: `API error: ${response.statusText}`
            };
        }

        return await response.json();
    }

    getPreviewVideoUrl(previewHash: string): string {
        return `${this.baseUrl}/preview-video/${previewHash}`;
    }

    async updateHandlers(enabledHandlers: string[]): Promise<CorrectionData> {
        console.log('API: Starting handler update...');
        this.isUpdatingHandlers = true;
        console.log('API: Set isUpdatingHandlers to', this.isUpdatingHandlers);
        
        try {
            const response = await fetch(`${this.baseUrl}/handlers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(enabledHandlers)
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.status === 'error') {
                throw new Error(data.message || 'Failed to update handlers');
            }

            console.log('API: Handler update successful');
            return validateCorrectionData(data.data);
        } finally {
            this.isUpdatingHandlers = false;
            console.log('API: Set isUpdatingHandlers to', this.isUpdatingHandlers);
        }
    }

    async addLyrics(source: string, lyrics: string): Promise<CorrectionData> {
        const payload: AddLyricsRequest = {
            source,
            lyrics
        };

        const response = await fetch(`${this.baseUrl}/add-lyrics`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.status === 'error') {
            throw new Error(data.message || 'Failed to add lyrics');
        }

        return validateCorrectionData(data.data);
    }
}

export class FileOnlyClient implements ApiClient {
    async getCorrectionData(): Promise<CorrectionData> {
        throw new Error('Not supported in file-only mode');
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async submitCorrections(_data: CorrectionData): Promise<void> {
        throw new Error('Not supported in file-only mode');
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    getAudioUrl(_audioHash: string): string {
        throw new Error('Not supported in file-only mode');
    }

    async generatePreviewVideo(): Promise<PreviewVideoResponse> {
        throw new Error('Not supported in file-only mode');
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    getPreviewVideoUrl(_previewHash: string): string {
        throw new Error('Not supported in file-only mode');
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async updateHandlers(_enabledHandlers: string[]): Promise<CorrectionData> {
        throw new Error('Not supported in file-only mode');
    }

    async addLyrics(): Promise<CorrectionData> {
        throw new Error('Not supported in file-only mode');
    }
}

