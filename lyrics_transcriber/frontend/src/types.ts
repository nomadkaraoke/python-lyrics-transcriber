export interface Word {
    id: string
    text: string
    start_time: number | null
    end_time: number | null
    confidence?: number
    created_during_correction?: boolean
}

export interface LyricsSegment {
    id: string
    text: string
    words: Word[]
    start_time: number | null
    end_time: number | null
}

export interface WordCorrection {
    id?: string
    handler: string
    original_word: string
    corrected_word: string
    segment_id?: string
    word_id: string
    corrected_word_id: string | null
    source: string
    confidence: number
    reason: string
    alternatives: Record<string, number>
    is_deletion: boolean
    split_index?: number | null
    split_total?: number | null
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
    id: string
    transcribed_word_ids: string[]
    transcription_position: number
    reference_positions: Record<string, number>
    reference_word_ids: {
        [source: string]: string[]
    }
    confidence: number
    phrase_score?: PhraseScore
    total_score?: number
}

export interface GapSequence {
    id: string
    transcribed_word_ids: string[]
    transcription_position: number
    preceding_anchor_id: string | null
    following_anchor_id: string | null
    reference_word_ids: {
        [source: string]: string[]
    }
}

export interface ReferenceSource {
    segments: LyricsSegment[]
    metadata: {
        source: string
        track_name: string | null
        artist_names: string | null
        album_name: string | null
        duration_ms: number | null
        explicit: boolean | null
        language: string | null
        is_synced: boolean
        lyrics_provider: string
        lyrics_provider_id: string
        provider_metadata: Record<string, unknown>
    }
    source: string
}

export interface CorrectionStep {
    handler_name: string
    affected_word_ids: string[]
    affected_segment_ids: string[]
    corrections: WordCorrection[]
    segments_before: LyricsSegment[]
    segments_after: LyricsSegment[]
    created_word_ids: string[]
    deleted_word_ids: string[]
}

export interface CorrectionHandler {
    id: string
    name: string
    description: string
    enabled: boolean
}

export interface CorrectionData {
    original_segments: LyricsSegment[]
    reference_lyrics: Record<string, ReferenceSource>
    anchor_sequences: AnchorSequence[]
    gap_sequences: GapSequence[]
    resized_segments: LyricsSegment[]
    corrections_made: number
    confidence: number
    corrections: WordCorrection[]
    corrected_segments: LyricsSegment[]
    metadata: {
        anchor_sequences_count: number
        gap_sequences_count: number
        total_words: number
        correction_ratio: number
        audio_filepath?: string
        audio_hash?: string
        available_handlers?: CorrectionHandler[]
        enabled_handlers?: string[]
    }
    correction_steps: CorrectionStep[]
    word_id_map: Record<string, string>
    segment_id_map: Record<string, string>
}

export interface HighlightInfo {
    type: 'single' | 'gap' | 'anchor' | 'correction'
    sequence?: AnchorSequence | GapSequence
    transcribed_words: Word[]
    reference_words?: {
        [source: string]: Word[]
    }
    correction?: WordCorrection
}

export type InteractionMode = 'highlight' | 'edit' | 'delete_word'
