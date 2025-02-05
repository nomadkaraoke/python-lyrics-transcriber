export interface Word {
    id: string
    text: string
    start_time: number
    end_time: number
    confidence?: number
}

export interface LyricsSegment {
    id: string
    text: string
    words: Word[]
    start_time: number
    end_time: number
}

export interface WordCorrection {
    id: string
    original_word: string
    corrected_word: string
    segment_id: string
    word_id: string
    source: string
    confidence: number
    reason: string
    alternatives: Record<string, number>
    is_deletion: boolean
    split_index?: number
    split_total?: number
    reference_positions?: Record<string, string>
    length: number
}

export interface PhraseScore {
    phrase_type: string
    natural_break_score: number
    length_score: number
    total_score: number
}

export interface AnchorSequence {
    id: string
    words: string[]
    text: string
    length: number
    word_ids: string[]
    reference_word_ids: Record<string, string[]>
    confidence: number
    phrase_score: PhraseScore
    total_score: number
}

export interface AnchorReference {
    text: string
    word_ids: string[]
    confidence: number
}

export interface GapSequence {
    id: string
    text: string
    words: string[]
    word_ids: string[]
    length: number
    corrections: WordCorrection[]
    preceding_anchor: AnchorReference | null
    following_anchor: AnchorReference | null
    reference_words: {
        [source: string]: string[]
    }
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
    word_ids?: string[]
    reference_word_ids?: Record<string, string[]>
    type: 'single' | 'gap' | 'anchor'
}

export type InteractionMode = 'highlight' | 'details' | 'edit'
