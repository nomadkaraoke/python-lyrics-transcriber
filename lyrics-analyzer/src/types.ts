export interface Word {
    text: string
    start_time: number
    end_time: number
    confidence?: number
}

export interface Segment {
    text: string
    words: Word[]
    start_time: number
    end_time: number
}

export interface Correction {
    original_word: string
    corrected_word: string
    segment_index: number
    word_index: number
    source: string
    confidence: number
    reason: string
    alternatives: Record<string, number>
}

export interface GapSequence {
    words: string[]
    text: string
    length: number
    transcription_position: number
    preceding_anchor: {
        words: string[]
        text: string
        length: number
        transcription_position: number
        reference_positions: Record<string, number>
        confidence: number
    } | null
    following_anchor: {
        words: string[]
        text: string
        length: number
        transcription_position: number
        reference_positions: Record<string, number>
        confidence: number
    } | null
    reference_words: {
        spotify?: string[]
        genius?: string[]
    }
    corrections: Correction[]
}

export interface LyricsData {
    transcribed_text: string
    corrected_text: string
    original_segments: Segment[]
    metadata: {
        correction_strategy: string
        anchor_sequences_count: number
        gap_sequences_count: number
        total_words: number
        correction_ratio: number
    }
    anchor_sequences: Array<{
        words: string[]
        text: string
        length: number
        transcription_position: number
        reference_positions: Record<string, number>
        confidence: number
        phrase_score: {
            phrase_type: string
            natural_break_score: number
            length_score: number
            total_score: number
        }
        total_score: number
    }>
    gap_sequences: GapSequence[]
    corrected_segments: Segment[]
    corrections_made: number
    confidence: number
    corrections: Correction[]
    reference_texts: Record<string, string>
} 