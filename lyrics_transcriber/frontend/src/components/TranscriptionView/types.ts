import { AnchorSequence, GapSequence, CorrectionData, HighlightInfo } from '../../types'
import { ModalContent, FlashType } from '../LyricsAnalyzer'

export interface WordPosition {
    word: string
    position: number
    type: 'anchor' | 'gap' | 'other'
    sequence?: AnchorSequence | GapSequence
    isInRange: boolean
}

export interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: AnchorSequence
    gap?: GapSequence
}

export interface TranscriptionViewProps {
    data: CorrectionData
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
}

export interface WordProps {
    word: string
    position: number
    anchor?: AnchorSequence
    gap?: GapSequence
    shouldFlash: boolean
    onClick: (e: React.MouseEvent) => void
    onDoubleClick: (e: React.MouseEvent) => void
}

export interface SequenceMatch {
    type: 'anchor' | 'gap' | 'other'
    sequence?: AnchorSequence | GapSequence
    position: number
    length: number
} 