import { CorrectionData, LyricsSegment, Word, AnchorSequence, GapSequence, WordCorrection } from '@/types';
import { nanoid } from 'nanoid';

// Define server-side types just for this file
interface ServerData {
    transcription_position: number;
    length: number;
    words: string[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

export function normalizeDataForSubmission(data: CorrectionData): CorrectionData {
    // Create a deep clone to avoid modifying the original
    const normalized = JSON.parse(JSON.stringify(data));

    // Preserve floating point numbers with original precision
    const preserveFloats = (obj: Record<string, unknown>): void => {
        for (const key in obj) {
            const value = obj[key];
            if (typeof value === 'number') {
                // Handle integers and floats differently
                let formatted: string;
                if (Number.isInteger(value)) {
                    formatted = value.toFixed(1); // Force decimal point for integers
                } else {
                    formatted = value.toString(); // Keep original precision for floats
                }
                obj[key] = parseFloat(formatted);
            } else if (typeof value === 'object' && value !== null) {
                preserveFloats(value as Record<string, unknown>);
            }
        }
    };
    preserveFloats(normalized);
    return normalized;
}

// Helper function to find word IDs for a sequence based on original positions
function findWordIdsForSequence(
    segments: LyricsSegment[],
    sequence: ServerData
): string[] {
    const allWords = segments.flatMap(s => s.words);
    const startIndex = sequence.transcription_position;
    const endIndex = startIndex + sequence.length;

    console.log('Finding word IDs for sequence:', JSON.stringify({
        position: sequence.transcription_position,
        length: sequence.length,
        words: allWords.slice(startIndex, endIndex).map(w => w.text)
    }));

    return allWords.slice(startIndex, endIndex).map(word => word.id);
}

// Helper function to find word ID for a correction
function findWordIdForCorrection(
    segments: LyricsSegment[],
    correction: { original_word: string; }
): string {
    for (const segment of segments) {
        const word = segment.words.find(w => w.text === correction.original_word);
        if (word) return word.id;
    }
    return nanoid(); // Fallback if word not found
}

// Helper function to find word IDs in reference text
function findReferenceWordIds(
    referenceSource: string,
    sequence: ServerData
): string[] {
    const referencePosition = sequence.reference_positions?.[referenceSource];
    if (typeof referencePosition !== 'number') {
        return [];
    }

    // Generate IDs in the same format as HighlightedText
    const wordIds = Array.from({ length: sequence.length },
        (_, i) => `${referenceSource}-word-${referencePosition + i}`
    );

    return wordIds;
}

export function initializeDataWithIds(data: CorrectionData): CorrectionData {
    const newData = JSON.parse(JSON.stringify(data)) as CorrectionData;

    // Initialize segment and word IDs
    newData.corrected_segments = newData.corrected_segments.map((segment: LyricsSegment) => ({
        ...segment,
        id: segment.id || nanoid(),
        words: segment.words.map((word: Word) => ({
            ...word,
            id: word.id || nanoid()
        }))
    }));

    console.log('Segments after ID initialization:', JSON.stringify({
        segmentCount: newData.corrected_segments.length,
        totalWords: newData.corrected_segments.reduce((sum, seg) => sum + seg.words.length, 0),
        sampleWords: newData.corrected_segments[0].words.map(w => ({ id: w.id, text: w.text }))
    }));

    // Update anchor sequences with word IDs based on positions
    newData.anchor_sequences = newData.anchor_sequences.map((anchor) => {
        const serverAnchor = anchor as unknown as ServerData;

        // Get reference word IDs for each source
        const referenceWordIds: Record<string, string[]> = {};
        Object.keys(data.reference_texts || {}).forEach(source => {
            referenceWordIds[source] = findReferenceWordIds(source, serverAnchor);
        });

        console.log('Processing anchor with references:', JSON.stringify({
            words: anchor.words,
            reference_positions: serverAnchor.reference_positions,
            reference_word_ids: referenceWordIds
        }));

        return {
            ...anchor,
            id: anchor.id || nanoid(),
            word_ids: findWordIdsForSequence(newData.corrected_segments, serverAnchor),
            reference_word_ids: referenceWordIds
        } as AnchorSequence;
    });

    // Update gap sequences to use word IDs
    newData.gap_sequences = newData.gap_sequences.map((gap) => {
        const serverGap = gap as unknown as ServerData;
        return {
            ...gap,
            id: gap.id || nanoid(),
            word_ids: gap.word_ids || findWordIdsForSequence(newData.corrected_segments, serverGap),
            corrections: gap.corrections.map((correction: WordCorrection) => ({
                ...correction,
                id: correction.id || nanoid(),
                word_id: correction.word_id || findWordIdForCorrection(newData.corrected_segments, correction)
            }))
        } as GapSequence;
    });

    return newData;
}
