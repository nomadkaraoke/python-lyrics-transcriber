import { nanoid } from 'nanoid'
import { CorrectionData, LyricsSegment } from '../../../types'

export const addSegmentBefore = (
    data: CorrectionData,
    beforeIndex: number
): CorrectionData => {
    const newData = { ...data }
    const beforeSegment = newData.corrected_segments[beforeIndex]

    // Create new segment starting 1 second before the target segment
    // Use 0 as default if start_time is null
    const newStartTime = Math.max(0, (beforeSegment.start_time ?? 1) - 1)
    const newEndTime = newStartTime + 1

    const newSegment: LyricsSegment = {
        id: nanoid(),
        text: "REPLACE",
        start_time: newStartTime,
        end_time: newEndTime,
        words: [{
            id: nanoid(),
            text: "REPLACE",
            start_time: newStartTime,
            end_time: newEndTime,
            confidence: 1.0
        }]
    }

    // Insert the new segment before the current one
    newData.corrected_segments.splice(beforeIndex, 0, newSegment)

    return newData
}

export const splitSegment = (
    data: CorrectionData,
    segmentIndex: number,
    afterWordIndex: number
): CorrectionData | null => {
    const newData = { ...data }
    const segment = newData.corrected_segments[segmentIndex]

    // Split the words array
    const firstHalfWords = segment.words.slice(0, afterWordIndex + 1)
    const secondHalfWords = segment.words.slice(afterWordIndex + 1)

    if (secondHalfWords.length === 0) return null // Nothing to split

    const lastFirstWord = firstHalfWords[firstHalfWords.length - 1]
    const firstSecondWord = secondHalfWords[0]
    const lastSecondWord = secondHalfWords[secondHalfWords.length - 1]

    // Create two segments from the split
    const firstSegment: LyricsSegment = {
        ...segment,
        words: firstHalfWords,
        text: firstHalfWords.map(w => w.text).join(' '),
        end_time: lastFirstWord.end_time ?? null
    }

    const secondSegment: LyricsSegment = {
        id: nanoid(),
        words: secondHalfWords,
        text: secondHalfWords.map(w => w.text).join(' '),
        start_time: firstSecondWord.start_time ?? null,
        end_time: lastSecondWord.end_time ?? null
    }

    // Replace the original segment with the two new segments
    newData.corrected_segments.splice(segmentIndex, 1, firstSegment, secondSegment)

    return newData
}

export const deleteSegment = (
    data: CorrectionData,
    segmentIndex: number
): CorrectionData => {
    const newData = { ...data }
    const deletedSegment = newData.corrected_segments[segmentIndex]

    // Remove segment
    newData.corrected_segments = newData.corrected_segments.filter((_, index) => index !== segmentIndex)

    // Update anchor sequences to remove references to deleted words
    newData.anchor_sequences = newData.anchor_sequences.map(anchor => ({
        ...anchor,
        transcribed_word_ids: anchor.transcribed_word_ids.filter(wordId =>
            !deletedSegment.words.some(deletedWord => deletedWord.id === wordId)
        )
    }))

    // Update gap sequences to remove references to deleted words
    newData.gap_sequences = newData.gap_sequences.map(gap => ({
        ...gap,
        transcribed_word_ids: gap.transcribed_word_ids.filter(wordId =>
            !deletedSegment.words.some(deletedWord => deletedWord.id === wordId)
        )
    }))

    return newData
}

export const updateSegment = (
    data: CorrectionData,
    segmentIndex: number,
    updatedSegment: LyricsSegment
): CorrectionData => {
    const newData = { ...data }

    // Ensure new words have IDs
    updatedSegment.words = updatedSegment.words.map(word => ({
        ...word,
        id: word.id || nanoid()
    }))

    newData.corrected_segments[segmentIndex] = updatedSegment

    return newData
} 