import { useCallback } from 'react'
import { AnchorSequence, GapSequence } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo } from '../types'

interface UseWordClickProps {
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
}

export function useWordClick({ onElementClick, onWordClick }: UseWordClickProps) {
    const handleWordClick = useCallback((
        word: string,
        position: number,
        anchor?: AnchorSequence,
        gap?: GapSequence
    ) => {
        const belongsToAnchor = anchor && anchor.words.includes(word)
        const belongsToGap = gap && gap.words.includes(word)
        const sequencePosition = belongsToAnchor
            ? anchor.transcription_position
            : belongsToGap
                ? gap.transcription_position
                : position

        const wordPosition = belongsToAnchor
            ? anchor.words.indexOf(word) + sequencePosition
            : belongsToGap
                ? gap.words.indexOf(word) + sequencePosition
                : position

        onWordClick?.({
            wordIndex: wordPosition,
            type: belongsToAnchor ? 'anchor' : belongsToGap ? 'gap' : 'other',
            anchor: belongsToAnchor ? anchor : undefined,
            gap: belongsToGap ? gap : undefined
        })
    }, [onWordClick])

    const handleWordDoubleClick = useCallback((
        word: string,
        position: number,
        anchor?: AnchorSequence,
        gap?: GapSequence
    ) => {
        if (anchor) {
            const relativePosition = position - anchor.transcription_position
            onElementClick({
                type: 'anchor',
                data: {
                    ...anchor,
                    position: relativePosition,
                    word
                }
            })
        } else if (gap) {
            const relativePosition = position - gap.transcription_position
            onElementClick({
                type: 'gap',
                data: {
                    ...gap,
                    position: relativePosition,
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
    }, [onElementClick])

    return {
        handleWordClick,
        handleWordDoubleClick
    }
} 