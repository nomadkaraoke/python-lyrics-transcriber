import { CorrectionData } from './types';

// New file to handle API communication
export interface ApiClient {
    getCorrectionData: () => Promise<CorrectionData>;
    submitCorrections: (data: CorrectionData) => Promise<void>;
}

export class LiveApiClient implements ApiClient {
    constructor(private baseUrl: string) {
        // Ensure baseUrl doesn't end with a slash
        this.baseUrl = baseUrl.replace(/\/$/, '')
    }

    async getCorrectionData(): Promise<CorrectionData> {
        const response = await fetch(`${this.baseUrl}/correction-data`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    }

    async submitCorrections(data: CorrectionData): Promise<void> {
        const response = await fetch(`${this.baseUrl}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
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
}
