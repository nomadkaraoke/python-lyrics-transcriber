import { useCallback } from 'react'
import { AnchorSequence, GapSequence, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo } from '../types'

// Define debug info type
interface WordDebugInfo {
    wordSplitInfo?: {
        text: string
        startIndex: number
        endIndex: number
    }
    nearbyAnchors?: AnchorSequence[]
}

export interface UseWordClickProps {
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    isReference?: boolean
    currentSource?: string
}

export function useWordClick({
    mode,
    onElementClick,
    onWordClick,
    isReference,
    currentSource
}: UseWordClickProps) {
    const handleWordClick = useCallback((
        word: string,
        wordId: string,
        anchor?: AnchorSequence,
        gap?: GapSequence,
        debugInfo?: WordDebugInfo
    ) => {
        console.log(JSON.stringify({
            debug: {
                clickedWord: word,
                wordId,
                isReference,
                currentSource,
                wordInfo: debugInfo?.wordSplitInfo,
                nearbyAnchors: debugInfo?.nearbyAnchors,
                anchorInfo: anchor && {
                    wordIds: anchor.word_ids,
                    length: anchor.length,
                    words: anchor.words,
                    referenceWordIds: anchor.reference_word_ids
                },
                gapInfo: gap && {
                    wordIds: gap.word_ids,
                    length: gap.length,
                    words: gap.words,
                    corrections: gap.corrections.map(c => ({
                        original_word: c.original_word,
                        corrected_word: c.corrected_word,
                        word_id: c.word_id,
                        length: c.length,
                        is_deletion: c.is_deletion,
                        split_index: c.split_index,
                        split_total: c.split_total
                    }))
                },
                belongsToAnchor: anchor && (
                    isReference
                        ? anchor.reference_word_ids[currentSource!]?.includes(wordId)
                        : anchor.word_ids.includes(wordId)
                ),
                belongsToGap: gap && (
                    isReference
                        ? gap.corrections.some(c => c.word_id === wordId)
                        : gap.word_ids.includes(wordId)
                ),
                wordIndexInGap: gap && gap.words.indexOf(word),
                hasMatchingCorrection: gap && gap.corrections.some(c => c.word_id === wordId)
            }
        }, null, 2))

        const belongsToAnchor = anchor && (
            isReference
                ? anchor.reference_word_ids[currentSource!]?.includes(wordId)
                : anchor.word_ids.includes(wordId)
        )

        const belongsToGap = gap && (
            isReference
                ? gap.corrections.some(c => c.word_id === wordId)
                : gap.word_ids.includes(wordId)
        )

        if (mode === 'highlight' || mode === 'edit') {
            onWordClick?.({
                word_id: wordId,
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
                        wordId,
                        word
                    }
                })
            } else if (belongsToGap && gap) {
                onElementClick({
                    type: 'gap',
                    data: {
                        ...gap,
                        wordId,
                        word
                    }
                })
            } else if (!isReference) {
                // Create synthetic gap for non-sequence words (transcription view only)
                const syntheticGap: GapSequence = {
                    id: `synthetic-${wordId}`,
                    text: word,
                    words: [word],
                    word_ids: [wordId],
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
                        wordId,
                        word
                    }
                })
            }
        }
    }, [mode, onWordClick, onElementClick, isReference, currentSource])

    return { handleWordClick }
} 