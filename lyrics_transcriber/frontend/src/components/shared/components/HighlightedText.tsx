import React from 'react'
import { Typography } from '@mui/material'
import { Word } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import { AnchorSequence, GapSequence, HighlightInfo, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo, TranscriptionWordPosition, FlashType } from '../types'

interface HighlightedTextProps {
    // Input can be either raw text or pre-processed word positions
    text?: string
    wordPositions?: TranscriptionWordPosition[]
    // Common props
    anchors: AnchorSequence[]
    gaps: GapSequence[]
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    // Reference-specific props
    isReference?: boolean
    currentSource?: 'genius' | 'spotify'
    newlineIndices?: Set<number>
}

// Helper function to safely check reference indices
function hasValidReferenceIndex(
    highlightInfo: HighlightInfo,
    currentSource: 'genius' | 'spotify'
): boolean {
    return (
        highlightInfo.type === 'anchor' &&
        highlightInfo.referenceIndices !== undefined &&
        currentSource in highlightInfo.referenceIndices &&
        typeof highlightInfo.referenceIndices[currentSource] === 'number'
    )
}

export function HighlightedText({
    text,
    wordPositions,
    anchors,
    gaps,
    highlightInfo,
    mode,
    onElementClick,
    onWordClick,
    flashingType,
    isReference,
    currentSource,
    newlineIndices
}: HighlightedTextProps) {
    const { handleWordClick } = useWordClick({
        mode,
        onElementClick,
        onWordClick,
        isReference,
        currentSource
    })

    const shouldWordFlash = (wordPos: TranscriptionWordPosition | { word: string, index: number }): boolean => {
        if (!flashingType) return false

        if ('type' in wordPos) {
            // Handle TranscriptionWordPosition
            const hasCorrections = wordPos.type === 'gap' &&
                Boolean((wordPos.sequence as GapSequence)?.corrections?.length)

            return Boolean(
                (flashingType === 'anchor' && wordPos.type === 'anchor') ||
                (flashingType === 'corrected' && hasCorrections) ||
                (flashingType === 'uncorrected' && wordPos.type === 'gap' && !hasCorrections) ||
                (flashingType === 'word' && highlightInfo?.type === 'anchor' &&
                    wordPos.type === 'anchor' && wordPos.sequence && (
                        wordPos.sequence.transcription_position === highlightInfo.transcriptionIndex &&
                        wordPos.position >= wordPos.sequence.transcription_position &&
                        wordPos.position < wordPos.sequence.transcription_position + wordPos.sequence.length
                    ))
            )
        } else {
            // Handle raw text word
            if (!highlightInfo || !currentSource) return false

            return Boolean(
                highlightInfo.type === 'anchor' && (
                    isReference
                        ? hasValidReferenceIndex(highlightInfo, currentSource) &&
                        wordPos.index >= (highlightInfo.referenceIndices[currentSource] ?? 0) &&
                        wordPos.index < (highlightInfo.referenceIndices[currentSource] ?? 0) + (highlightInfo.referenceLength ?? 0)
                        : highlightInfo.transcriptionIndex !== undefined &&
                        wordPos.index >= highlightInfo.transcriptionIndex &&
                        wordPos.index < highlightInfo.transcriptionIndex + (highlightInfo.transcriptionLength ?? 0)
                )
            )
        }
    }

    const renderContent = () => {
        if (wordPositions) {
            return wordPositions.map((wordPos, index) => {
                const anchorSequence = wordPos.type === 'anchor' ? wordPos.sequence as AnchorSequence : undefined
                const gapSequence = wordPos.type === 'gap' ? wordPos.sequence as GapSequence : undefined
                const hasCorrections = Boolean(gapSequence?.corrections?.length)

                return (
                    <Word
                        key={`${wordPos.word}-${index}`}
                        word={wordPos.word}
                        shouldFlash={shouldWordFlash(wordPos)}
                        isAnchor={Boolean(anchorSequence)}
                        isCorrectedGap={hasCorrections}
                        isUncorrectedGap={wordPos.type === 'gap' && !hasCorrections}
                        onClick={() => handleWordClick(
                            wordPos.word,
                            wordPos.position,
                            anchorSequence,
                            gapSequence
                        )}
                    />
                )
            })
        } else if (text) {
            const elements: React.ReactNode[] = []
            const words = text.split(/\s+/)
            let currentIndex = 0

            words.forEach((word, index) => {
                const thisWordIndex = currentIndex

                // Find matching anchor and gap based on view type
                const anchor = anchors.find(a => {
                    const position = isReference
                        ? a.reference_positions[currentSource!]
                        : a.transcription_position
                    if (position === undefined) return false
                    return thisWordIndex >= position && thisWordIndex < position + a.length
                })

                const correctedGap = gaps.find(g => {
                    if (!g.corrections.length) return false
                    if (isReference) {
                        const correction = g.corrections[0]
                        const position = correction.reference_positions?.[currentSource!]
                        if (position === undefined) return false
                        return thisWordIndex >= position && thisWordIndex < position + correction.length
                    } else {
                        return thisWordIndex >= g.transcription_position &&
                            thisWordIndex < g.transcription_position + g.length
                    }
                })

                // Determine if word should be highlighted
                const isHighlighted = Boolean(
                    highlightInfo &&
                    highlightInfo.type === 'anchor' && (
                        isReference
                            ? hasValidReferenceIndex(highlightInfo, currentSource!) &&
                            thisWordIndex >= (highlightInfo.referenceIndices[currentSource!] ?? 0) &&
                            thisWordIndex < (highlightInfo.referenceIndices[currentSource!] ?? 0) + (highlightInfo.referenceLength ?? 0)
                            : highlightInfo.transcriptionIndex !== undefined &&
                            thisWordIndex >= highlightInfo.transcriptionIndex &&
                            thisWordIndex < highlightInfo.transcriptionIndex + (highlightInfo.transcriptionLength ?? 0)
                    )
                )

                elements.push(
                    <Word
                        key={`${word}-${index}`}
                        word={word}
                        shouldFlash={isHighlighted}
                        isAnchor={Boolean(anchor)}
                        isCorrectedGap={Boolean(correctedGap)}
                        isUncorrectedGap={!isReference && Boolean(!correctedGap && gaps.some(g =>
                            thisWordIndex >= g.transcription_position &&
                            thisWordIndex < g.transcription_position + g.length
                        ))}
                        onClick={() => handleWordClick(
                            word,
                            thisWordIndex,
                            anchor,
                            correctedGap
                        )}
                    />
                )

                // Only add space/newline if not the last word
                if (index < words.length - 1) {
                    if (newlineIndices?.has(thisWordIndex)) {
                        elements.push(<br key={`br-${index}`} />)
                    } else {
                        elements.push(' ')
                    }
                }

                currentIndex++
            })

            return elements
        }

        return null
    }

    return (
        <Typography
            component="pre"
            sx={{
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                margin: 0,
                lineHeight: 1.5,
            }}
        >
            {renderContent()}
        </Typography>
    )
} 