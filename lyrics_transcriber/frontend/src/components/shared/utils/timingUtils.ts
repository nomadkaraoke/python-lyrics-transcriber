import { LyricsSegment, Word, CorrectionData } from '../../../types';

/**
 * Apply the timing offset to a single timestamp
 * @param time The original timestamp in seconds
 * @param offsetMs The offset in milliseconds
 * @returns The adjusted timestamp in seconds
 */
export const applyOffsetToTime = (time: number | null, offsetMs: number): number | null => {
    if (time === null) return null;
    // Convert ms to seconds and add to the time
    return time + (offsetMs / 1000);
};

/**
 * Apply the timing offset to a word
 * @param word The original word object
 * @param offsetMs The offset in milliseconds
 * @returns A new word object with adjusted timestamps
 */
export const applyOffsetToWord = (word: Word, offsetMs: number): Word => {
    if (offsetMs === 0) return word;
    
    return {
        ...word,
        start_time: applyOffsetToTime(word.start_time, offsetMs),
        end_time: applyOffsetToTime(word.end_time, offsetMs)
    };
};

/**
 * Apply the timing offset to all words in a segment
 * Also updates the segment's start and end times based on the first and last word
 * @param segment The original segment
 * @param offsetMs The offset in milliseconds
 * @returns A new segment with adjusted timestamps
 */
export const applyOffsetToSegment = (segment: LyricsSegment, offsetMs: number): LyricsSegment => {
    if (offsetMs === 0) return segment;
    
    const adjustedWords = segment.words.map(word => applyOffsetToWord(word, offsetMs));
    
    // Update segment start/end times based on first/last word
    const validStartTimes = adjustedWords.map(w => w.start_time).filter((t): t is number => t !== null);
    const validEndTimes = adjustedWords.map(w => w.end_time).filter((t): t is number => t !== null);

    const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : null;
    const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : null;
    
    return {
        ...segment,
        words: adjustedWords,
        start_time: segmentStartTime,
        end_time: segmentEndTime
    };
};

/**
 * Apply the timing offset to the entire correction data
 * This creates a new data object with all timestamps adjusted by the offset
 * @param data The original correction data
 * @param offsetMs The offset in milliseconds
 * @returns A new correction data object with all timestamps adjusted
 */
export const applyOffsetToCorrectionData = (data: CorrectionData, offsetMs: number): CorrectionData => {
    console.log(`[TIMING] applyOffsetToCorrectionData called with offset: ${offsetMs}ms`);
    
    if (offsetMs === 0) {
        console.log('[TIMING] Offset is 0, returning original data');
        return data;
    }
    
    // Log some examples of original timestamps
    if (data.corrected_segments.length > 0) {
        const firstSegment = data.corrected_segments[0];
        console.log(`[TIMING] First segment before offset - id: ${firstSegment.id}`);
        console.log(`[TIMING] - start_time: ${firstSegment.start_time}, end_time: ${firstSegment.end_time}`);
        
        if (firstSegment.words.length > 0) {
            const firstWord = firstSegment.words[0];
            const lastWord = firstSegment.words[firstSegment.words.length - 1];
            console.log(`[TIMING] - first word "${firstWord.text}" time: ${firstWord.start_time} -> ${firstWord.end_time}`);
            console.log(`[TIMING] - last word "${lastWord.text}" time: ${lastWord.start_time} -> ${lastWord.end_time}`);
        }
    }
    
    const result = {
        ...data,
        corrected_segments: data.corrected_segments.map(segment => 
            applyOffsetToSegment(segment, offsetMs)
        )
    };
    
    // Log some examples of adjusted timestamps
    if (result.corrected_segments.length > 0) {
        const firstSegment = result.corrected_segments[0];
        console.log(`[TIMING] First segment AFTER offset - id: ${firstSegment.id}`);
        console.log(`[TIMING] - start_time: ${firstSegment.start_time}, end_time: ${firstSegment.end_time}`);
        
        if (firstSegment.words.length > 0) {
            const firstWord = firstSegment.words[0];
            const lastWord = firstSegment.words[firstSegment.words.length - 1];
            console.log(`[TIMING] - first word "${firstWord.text}" time: ${firstWord.start_time} -> ${firstWord.end_time}`);
            console.log(`[TIMING] - last word "${lastWord.text}" time: ${lastWord.start_time} -> ${lastWord.end_time}`);
        }
    }
    
    console.log(`[TIMING] Finished applying offset of ${offsetMs}ms to data`);
    return result;
}; 