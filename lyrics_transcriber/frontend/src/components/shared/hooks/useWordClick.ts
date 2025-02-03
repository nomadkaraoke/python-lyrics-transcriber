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
        position: number,
        anchor?: AnchorSequence,
        gap?: GapSequence,
        debugInfo?: any
    ) => {
        console.log(JSON.stringify({
            debug: {
                clickedWord: word,
                position,
                isReference,
                currentSource,
                wordInfo: debugInfo?.wordSplitInfo,
                nearbyAnchors: debugInfo?.nearbyAnchors,
                anchorInfo: anchor && {
                    transcriptionPos: anchor.transcription_position,
                    length: anchor.length,
                    words: anchor.words,
                    refPositions: anchor.reference_positions
                },
                gapInfo: gap && {
                    transcriptionPos: gap.transcription_position,
                    length: gap.length,
                    words: gap.words,
                    corrections: gap.corrections.map(c => ({
                        length: c.length,
                        refPositions: c.reference_positions
                    }))
                },
                belongsToAnchor: anchor && (
                    isReference
                        ? position >= (anchor.reference_positions[currentSource!] ?? -1) &&
                        position < ((anchor.reference_positions[currentSource!] ?? -1) + anchor.length)
                        : position >= anchor.transcription_position &&
                        position < (anchor.transcription_position + anchor.length)
                ),
                belongsToGap: gap && (
                    isReference
                        ? gap.corrections[0]?.reference_positions?.[currentSource!] !== undefined &&
                        position >= (gap.corrections[0].reference_positions![currentSource!]) &&
                        position < (gap.corrections[0].reference_positions![currentSource!] + gap.corrections[0].length)
                        : position >= gap.transcription_position &&
                        position < (gap.transcription_position + gap.length)
                )
            }
        }, null, 2))

        const belongsToAnchor = anchor && (
            isReference
                ? position >= (anchor.reference_positions[currentSource!] ?? -1) &&
                position < ((anchor.reference_positions[currentSource!] ?? -1) + anchor.length)
                : position >= anchor.transcription_position &&
                position < (anchor.transcription_position + anchor.length)
        )

        const belongsToGap = gap && (
            isReference
                ? gap.corrections[0]?.reference_positions?.[currentSource!] !== undefined &&
                position >= (gap.corrections[0].reference_positions![currentSource!]) &&
                position < (gap.corrections[0].reference_positions![currentSource!] + gap.corrections[0].length)
                : position >= gap.transcription_position &&
                position < (gap.transcription_position + gap.length)
        )

        if (mode === 'highlight' || mode === 'edit') {
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
            } else if (!isReference) {
                // Create synthetic gap for non-sequence words (transcription view only)
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
    }, [mode, onWordClick, onElementClick, isReference, currentSource])

    return { handleWordClick }
} 