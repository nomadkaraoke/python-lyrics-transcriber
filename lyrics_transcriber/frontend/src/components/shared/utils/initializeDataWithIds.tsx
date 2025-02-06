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

// Add this at the top of the file
const logWordMatching = (segments: LyricsSegment[], correction: { original_word: string }, foundId: string | null) => {
    const allWords = segments.flatMap(s => s.words);
    console.log('Word ID Assignment:', {
        searchingFor: correction.original_word,
        allWordsWithIds: allWords.map(w => ({
            text: w.text,
            id: w.id
        })),
        matchedId: foundId,
        matchedWord: foundId ? allWords.find(w => w.id === foundId)?.text : null
    });
};

// Modify findWordIdForCorrection to include logging
function findWordIdForCorrection(
    segments: LyricsSegment[],
    correction: {
        original_word: string;
        original_position?: number;
    }
): string {
    const allWords = segments.flatMap(s => s.words);

    // If we have position information, use it to find the exact word
    if (typeof correction.original_position === 'number') {
        const word = allWords[correction.original_position];
        if (word && word.text === correction.original_word) {
            logWordMatching(segments, correction, word.id);
            return word.id;
        }
    }

    // Fallback to finding by text (but log a warning)
    for (const segment of segments) {
        const word = segment.words.find(w => w.text === correction.original_word);
        if (word) {
            console.warn(
                'Warning: Had to find word by text match rather than position.',
                correction.original_word,
                'Consider using position information for more accurate matching.'
            );
            logWordMatching(segments, correction, word.id);
            return word.id;
        }
    }

    const newId = nanoid();
    logWordMatching(segments, correction, null);
    console.log('Generated new ID:', newId, 'for word:', correction.original_word);
    return newId;
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
        console.log('Processing gap sequence:', {
            words: gap.words,
            word_ids: gap.word_ids,
            corrections: gap.corrections,
            foundWordIds: findWordIdsForSequence(newData.corrected_segments, serverGap)
        });

        return {
            ...gap,
            id: gap.id || nanoid(),
            word_ids: gap.word_ids || findWordIdsForSequence(newData.corrected_segments, serverGap),
            corrections: gap.corrections.map((correction: WordCorrection) => {
                const wordId = correction.word_id || findWordIdForCorrection(newData.corrected_segments, correction);
                console.log('Correction word ID assignment:', {
                    original_word: correction.original_word,
                    corrected_word: correction.corrected_word,
                    assigned_id: wordId
                });
                return {
                    ...correction,
                    id: correction.id || nanoid(),
                    word_id: wordId
                };
            })
        } as GapSequence;
    });

    return newData;
}
