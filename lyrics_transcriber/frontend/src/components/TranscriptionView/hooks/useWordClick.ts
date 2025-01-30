import { useCallback } from 'react'
import { AnchorSequence, GapSequence, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo } from '../types'

interface UseWordClickProps {
    mode: InteractionMode;
    onElementClick: (content: ModalContent) => void;
    onWordClick?: (info: WordClickInfo) => void;
}

export function useWordClick({ mode, onElementClick, onWordClick }: UseWordClickProps) {
    const handleWordClick = useCallback((
        word: string,
        position: number,
        anchor?: AnchorSequence,
        gap?: GapSequence
    ) => {
        // Check if position falls within anchor or gap range
        const belongsToAnchor = anchor &&
            position >= anchor.transcription_position &&
            position < (anchor.transcription_position + anchor.length)

        const belongsToGap = gap &&
            position >= gap.transcription_position &&
            position < (gap.transcription_position + gap.length)

        const debugInfo = {
            word,
            position,
            mode,
            hasAnchor: Boolean(anchor),
            hasGap: Boolean(gap),
            anchor: anchor ? {
                text: anchor.text,
                position: anchor.transcription_position,
                length: anchor.length
            } : null,
            gap: gap ? {
                text: gap.text,
                position: gap.transcription_position,
                length: gap.length
            } : null,
            belongsToAnchor,
            belongsToGap
        }

        console.log('Word Click Debug:', JSON.stringify(debugInfo, null, 2))

        if (mode === 'highlight') {
            onWordClick?.({
                wordIndex: position,
                type: belongsToAnchor ? 'anchor' : belongsToGap ? 'gap' : 'other',
                anchor: belongsToAnchor ? anchor : undefined,
                gap: belongsToGap ? gap : undefined
            })
        } else if (mode === 'details') {
            if (belongsToAnchor && anchor) {
                onElementClick({
                    type: 'anchor',
                    data: {
                        ...anchor,
                        position,
                        word
                    }
                })
            } else if (belongsToGap && gap) {
                onElementClick({
                    type: 'gap',
                    data: {
                        ...gap,
                        position,
                        word
                    }
                })
            } else {
                // Create synthetic gap for non-sequence words
                const syntheticGap: GapSequence = {
                    text: word,
                    words: [word],
                    transcription_position: position,
                    length: 1,
                    corrections: [],
                    preceding_anchor: null,
                    following_anchor: null,
                    reference_words: {}
                }
                onElementClick({
                    type: 'gap',
                    data: {
                        ...syntheticGap,
                        position: 0,
                        word
                    }
                })
            }
        }
    }, [mode, onWordClick, onElementClick])

    return { handleWordClick }
} 