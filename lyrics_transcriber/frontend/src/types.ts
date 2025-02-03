export interface Word {
    text: string
    start_time: number
    end_time: number
    confidence?: number
}

export interface LyricsSegment {
    text: string
    words: Word[]
    start_time: number
    end_time: number
}

export interface WordCorrection {
    original_word: string
    corrected_word: string
    segment_index: number
    original_position: number
    source: string
    confidence: number
    reason: string
    alternatives: Record<string, number>
    is_deletion: boolean
    split_index?: number
    split_total?: number
    reference_positions?: Record<string, number>
    length: number
}

export interface PhraseScore {
    phrase_type: string
    natural_break_score: number
    length_score: number
    total_score: number
}

export interface AnchorSequence {
    words: string[]
    text: string
    length: number
    transcription_position: number
    reference_positions: Record<string, number>
    confidence: number
    phrase_score: PhraseScore
    total_score: number
}

export interface GapSequence {
    words: string[]
    text: string
    length: number
    transcription_position: number
    preceding_anchor: AnchorSequence | null
    following_anchor: AnchorSequence | null
    reference_words: Record<string, string[]>
    reference_words_original?: Record<string, string[]>
    corrections: WordCorrection[]
}

export interface LyricsData {
    transcribed_text: string
    corrected_text: string
    original_segments: LyricsSegment[]
    metadata: {
        anchor_sequences_count: number
        gap_sequences_count: number
        total_words: number
        correction_ratio: number
    }
    anchor_sequences: AnchorSequence[]
    gap_sequences: GapSequence[]
    corrected_segments: LyricsSegment[]
    corrections_made: number
    confidence: number
    corrections: WordCorrection[]
    reference_texts: Record<string, string>
}

export interface CorrectionData {
    transcribed_text: string
    original_segments: LyricsSegment[]
    reference_texts: Record<string, string>
    anchor_sequences: AnchorSequence[]
    gap_sequences: GapSequence[]
    resized_segments?: LyricsSegment[]
    corrected_text: string
    corrections_made: number
    confidence: number
    corrections: WordCorrection[]
    corrected_segments: LyricsSegment[]
    metadata: {
        anchor_sequences_count: number
        gap_sequences_count: number
        total_words: number
        correction_ratio: number
    }
}

export interface HighlightInfo {
    transcriptionIndex?: number
    transcriptionLength?: number
    referenceIndices: Record<string, number>
    referenceLength?: number
    type: 'single' | 'gap' | 'anchor'
}

export type InteractionMode = 'highlight' | 'details' | 'edit'
