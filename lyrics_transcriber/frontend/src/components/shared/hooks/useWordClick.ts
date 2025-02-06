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
    gaps?: GapSequence[]
}

export function useWordClick({
    mode,
    onElementClick,
    onWordClick,
    isReference,
    currentSource,
    gaps = []
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
                    referenceWordIds: anchor.reference_word_ids,
                    matchesWordId: isReference
                        ? anchor.reference_word_ids[currentSource!]?.includes(wordId)
                        : anchor.word_ids.includes(wordId)
                },
                gapInfo: gap && {
                    wordIds: gap.word_ids,
                    length: gap.length,
                    words: gap.words,
                    referenceWords: gap.reference_words,
                    corrections: gap.corrections,
                    matchesWordId: isReference
                        ? gap.reference_words[currentSource!]?.includes(wordId)
                        : gap.word_ids.includes(wordId)
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

        // For reference view clicks, find the corresponding gap
        if (isReference && currentSource) {
            // Extract position from wordId (e.g., "genius-word-3" -> 3)
            const position = parseInt(wordId.split('-').pop() || '', 10);

            // Find gap that has a correction matching this reference position
            const matchingGap = gaps?.find(g =>
                g.corrections.some(c => {
                    const refPosition = c.reference_positions?.[currentSource];
                    return typeof refPosition === 'number' && refPosition === position;
                })
            );

            if (matchingGap) {
                console.log('Found matching gap for reference click:', {
                    position,
                    gap: matchingGap
                });
                gap = matchingGap;
            }
        }

        const belongsToAnchor = anchor && (
            isReference
                ? anchor.reference_word_ids[currentSource!]?.includes(wordId)
                : anchor.word_ids.includes(wordId)
        )

        const belongsToGap = gap && (
            isReference
                ? gap.corrections.some(c => {
                    const refPosition = c.reference_positions?.[currentSource!];
                    const clickedPosition = parseInt(wordId.split('-').pop() || '', 10);
                    return typeof refPosition === 'number' && refPosition === clickedPosition;
                })
                : gap.word_ids.includes(wordId)
        )

        if (mode === 'highlight' || mode === 'edit') {
            if (belongsToAnchor && anchor) {
                onWordClick?.({
                    word_id: wordId,
                    type: 'anchor',
                    anchor,
                    gap: undefined
                })
            } else if (belongsToGap && gap) {
                // Create highlight info that includes both transcription and reference IDs
                const referenceWords: Record<string, string[]> = {};

                // For each correction in the gap, add its reference positions
                gap.corrections.forEach(correction => {
                    Object.entries(correction.reference_positions || {}).forEach(([source, position]) => {
                        if (typeof position === 'number') {
                            const refId = `${source}-word-${position}`;
                            if (!referenceWords[source]) {
                                referenceWords[source] = [];
                            }
                            if (!referenceWords[source].includes(refId)) {
                                referenceWords[source].push(refId);
                            }
                        }
                    });
                });

                onWordClick?.({
                    word_id: wordId,
                    type: 'gap',
                    anchor: undefined,
                    gap: {
                        ...gap,
                        reference_words: referenceWords // Use reference_words instead of reference_word_ids
                    }
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
    }, [mode, onWordClick, onElementClick, isReference, currentSource, gaps])

    return { handleWordClick }
} 