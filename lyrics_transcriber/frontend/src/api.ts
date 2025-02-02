import { CorrectionData } from './types';

// New file to handle API communication
export interface ApiClient {
    getCorrectionData: () => Promise<CorrectionData>;
    submitCorrections: (data: CorrectionData) => Promise<void>;
    getAudioUrl: () => string;
}

// Add new interface for the minimal update payload
interface CorrectionUpdate {
    corrections: CorrectionData['corrections'];
    corrected_segments: CorrectionData['corrected_segments'];
}

export class LiveApiClient implements ApiClient {
    constructor(private baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\/$/, '')
    }

    async getCorrectionData(): Promise<CorrectionData> {
        const response = await fetch(`${this.baseUrl}/correction-data`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        const data = await response.json();
        return data;
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

    getAudioUrl(): string {
        return `${this.baseUrl}/audio`
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

    getAudioUrl(): string {
        throw new Error('Not supported in file-only mode');
    }
}
