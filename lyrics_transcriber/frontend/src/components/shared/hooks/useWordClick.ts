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
    gaps = [] }: UseWordClickProps) {
    const handleWordClick = useCallback((
        word: string,
        wordId: string,
        anchor?: AnchorSequence,
        gap?: GapSequence
    ) => {

        // Check if word belongs to anchor
        const belongsToAnchor = anchor && (
            isReference
                ? anchor.reference_words[currentSource]?.some(w => w.id === wordId)
                : anchor.transcribed_words.some(w => w.id === wordId)
        )

        // Check if word belongs to gap
        const belongsToGap = gap && (
            isReference
                ? Object.entries(gap.reference_words).some(([source, words]) =>
                    source === currentSource && words.some(w => w.id === wordId)
                )
                : gap.transcribed_words.some(w => w.id === wordId)
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
                transcribedWords: anchor.transcribed_words,
                referenceWords: anchor.reference_words,
                belongsToAnchor
            },
            gapInfo: gap && {
                id: gap.id,
                transcribedWords: gap.transcribed_words,
                referenceWords: gap.reference_words,
                belongsToGap
            }
        })

        // For reference view clicks, find the corresponding gap
        if (isReference && currentSource) {
            const matchingGap = gaps?.find(g =>
                g.reference_words[currentSource]?.some(w => w.id === wordId)
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
                    transcribed_words: [{
                        id: wordId,
                        text: word,
                        start_time: null,
                        end_time: null
                    }],
                    length: 1,
                    transcription_position: -1,
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
    }, [mode, onWordClick, onElementClick, isReference, currentSource, gaps])

    return { handleWordClick }
} 