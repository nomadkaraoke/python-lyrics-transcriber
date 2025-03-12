import { AnchorSequence, GapSequence, HighlightInfo, InteractionMode, CorrectionData, LyricsSegment, ReferenceSource, WordCorrection } from '../../types'
import { ModalContent } from '../LyricsAnalyzer'

// Add FlashType definition directly in shared types
export type FlashType = 'anchor' | 'corrected' | 'uncorrected' | 'word' | 'handler' | null

// Common word click handling
export interface WordClickInfo {
    word_id: string
    type: 'anchor' | 'gap' | 'other'
    anchor?: AnchorSequence
    gap?: GapSequence
}

// Base props shared between components
export interface BaseViewProps {
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
}

// Base word position interface - remove the word property from here
export interface BaseWordPosition {
    type: 'anchor' | 'gap' | 'other'
    sequence?: AnchorSequence | GapSequence
}

// Transcription-specific word position with timing info
export interface TranscriptionWordPosition extends BaseWordPosition {
    word: {
        id: string
        text: string
        start_time?: number
        end_time?: number
    }
    type: 'anchor' | 'gap' | 'other'
    sequence?: AnchorSequence | GapSequence
    isInRange: boolean
    isCorrected?: boolean
}

// Reference-specific word position with simple string word
export interface ReferenceWordPosition extends BaseWordPosition {
    index: number
    isHighlighted: boolean
    word: string  // Simple string word for reference view
}

// Word component props
export interface WordProps {
    word: string
    shouldFlash: boolean
    isAnchor?: boolean
    isCorrectedGap?: boolean
    isUncorrectedGap?: boolean
    isCurrentlyPlaying?: boolean
    padding?: string
    onClick?: () => void
    correction?: {
        originalWord: string
        handler: string
        confidence: number
        source: string
    } | null
}

// Text segment props
export interface TextSegmentProps extends BaseViewProps {
    wordPositions: TranscriptionWordPosition[] | ReferenceWordPosition[]
}

// View-specific props
export interface TranscriptionViewProps {
    data: CorrectionData
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
    onPlaySegment?: (startTime: number) => void
    currentTime?: number
    anchors?: AnchorSequence[]
    flashingHandler?: string | null
    onDataChange?: (updatedData: CorrectionData) => void
}

// Add LinePosition type here since it's used in multiple places
export interface LinePosition {
    position: number
    lineNumber: number
    isEmpty?: boolean
}

// Reference-specific props
export interface ReferenceViewProps extends BaseViewProps {
    referenceSources: Record<string, ReferenceSource>
    anchors: CorrectionData['anchor_sequences']
    gaps: CorrectionData['gap_sequences']
    currentSource: string
    onSourceChange: (source: string) => void
    corrected_segments: LyricsSegment[]
    corrections: WordCorrection[]
    onAddLyrics?: () => void
}

// Update HighlightedTextProps to include linePositions
export interface HighlightedTextProps extends BaseViewProps {
    text?: string
    segments?: LyricsSegment[]
    wordPositions: TranscriptionWordPosition[] | ReferenceWordPosition[]
    anchors: AnchorSequence[]
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    isReference?: boolean
    currentSource?: string
    preserveSegments?: boolean
    linePositions?: LinePosition[]
    currentTime?: number
    referenceCorrections?: Map<string, string>
    gaps?: GapSequence[]
    flashingHandler?: string | null
    corrections?: WordCorrection[]
} 