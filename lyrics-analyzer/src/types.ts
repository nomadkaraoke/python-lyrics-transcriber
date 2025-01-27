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
    reference_words: {
        spotify?: string[]
        genius?: string[]
    }
    reference_words_original?: {
        spotify?: string[]
        genius?: string[]
    }
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
    resized_segments: LyricsSegment[]
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
    referenceIndices: {
        genius?: number
        spotify?: number
    }
    referenceLength?: number
    type: 'single' | 'gap' | 'anchor'
}

export interface AnchorMatchInfo {
    segment: string
    lastWord: string
    normalizedLastWord: string
    overlappingAnchors: Array<{
        text: string
        range: [number, number]
        words: string[]
        hasMatchingWord: boolean
    }>
    matchingGap: {
        text: string
        position: number
        length: number
        corrections: Array<{
            word: string
            referencePosition: number | undefined
        }>
        followingAnchor: {
            text: string
            position: number | undefined
        } | null
    } | null
    highlightDebug?: Array<{
        wordIndex: number
        refPos: number | undefined
        highlightPos: number | undefined
        anchorLength: number
        isInRange: boolean
    }>
    wordPositionDebug?: {
        anchorWords: string[]
        wordIndex: number
        referencePosition: number
        finalPosition: number
        normalizedWords: {
            anchor: string
            segment: string
        }
    }
    debugLog?: string[]
}
