import { useCallback } from 'react'
import { AnchorSequence, GapSequence, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo } from '../types'

export interface UseWordClickProps {
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    isReference?: boolean
    currentSource?: string
    gaps?: GapSequence[]
    anchors?: AnchorSequence[]
}

export function useWordClick({
    mode,
    onElementClick,
    onWordClick,
    isReference = false,
    currentSource = '',
    gaps = [],
    anchors = []
}: UseWordClickProps) {
    const handleWordClick = useCallback((
        word: string,
        wordId: string,
        anchor?: AnchorSequence,
        gap?: GapSequence
    ) => {
        // Check if word belongs to anchor
        const belongsToAnchor = anchor && (
            isReference
                ? anchor.reference_word_ids[currentSource]?.includes(wordId)
                : anchor.transcribed_word_ids.includes(wordId)
        )

        // Check if word belongs to gap
        const belongsToGap = gap && (
            isReference
                ? gap.reference_word_ids[currentSource]?.includes(wordId)
                : gap.transcribed_word_ids.includes(wordId)
        )

        // Debug info
        console.log('Word Click Debug:', {
            clickInfo: {
                word,
                wordId,
                isReference,
                currentSource,
                mode
            },
            anchorInfo: anchor && {
                id: anchor.id,
                transcribedWordIds: anchor.transcribed_word_ids,
                referenceWordIds: anchor.reference_word_ids,
                belongsToAnchor
            },
            gapInfo: gap && {
                id: gap.id,
                transcribedWordIds: gap.transcribed_word_ids,
                referenceWordIds: gap.reference_word_ids,
                belongsToGap
            }
        })

        // For reference view clicks, find the corresponding gap
        if (isReference && currentSource) {
            const matchingGap = gaps?.find(g =>
                g.reference_word_ids[currentSource]?.includes(wordId)
            );

            if (matchingGap) {
                console.log('Found matching gap for reference click:', {
                    wordId,
                    gap: matchingGap
                });
                gap = matchingGap;
            }
        }

        if (mode === 'highlight' || mode === 'edit') {
            if (belongsToAnchor && anchor) {
                onWordClick?.({
                    word_id: wordId,
                    type: 'anchor',
                    anchor,
                    gap: undefined
                })
            } else if (belongsToGap && gap) {
                onWordClick?.({
                    word_id: wordId,
                    type: 'gap',
                    anchor: undefined,
                    gap
                })
            } else if (gap?.corrections?.some(c => c.corrected_word_id === wordId) ||
                gap?.corrections?.some(c => c.word_id === wordId)) {
                // If the word is part of a correction, mark it as a gap
                onWordClick?.({
                    word_id: wordId,
                    type: 'gap',
                    anchor: undefined,
                    gap
                })
            } else {
                onWordClick?.({
                    word_id: wordId,
                    type: 'other',
                    anchor: undefined,
                    gap: undefined
                })
            }
        } else if (mode === 'details') {
            if (belongsToAnchor && anchor) {
                onElementClick({
                    type: 'anchor',
                    data: {
                        ...anchor,
                        wordId,
                        word,
                        anchor_sequences: anchors
                    }
                })
            } else if (belongsToGap && gap) {
                onElementClick({
                    type: 'gap',
                    data: {
                        ...gap,
                        wordId,
                        word,
                        anchor_sequences: anchors
                    }
                })
            } else if (!isReference) {
                // Create synthetic gap for non-sequence words (transcription view only)
                const syntheticGap: GapSequence = {
                    id: `synthetic-${wordId}`,
                    transcribed_word_ids: [wordId],
                    transcription_position: -1,
                    corrections: [],
                    preceding_anchor_id: null,
                    following_anchor_id: null,
                    reference_word_ids: {}
                }
                onElementClick({
                    type: 'gap',
                    data: {
                        ...syntheticGap,
                        wordId,
                        word,
                        anchor_sequences: anchors
                    }
                })
            }
        }
    }, [mode, onWordClick, onElementClick, isReference, currentSource, gaps, anchors])

    return { handleWordClick }
} 