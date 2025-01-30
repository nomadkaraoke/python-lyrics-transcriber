import React from 'react'
import { Typography } from '@mui/material'
import { Word } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import { WordPosition, WordClickInfo } from '../types'
import { FlashType, ModalContent } from '../../LyricsAnalyzer'
import { AnchorSequence, GapSequence, HighlightInfo } from '../../../types'

interface TextSegmentProps {
    wordPositions: WordPosition[]
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
}

function TextSegmentComponent({
    wordPositions,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo,
}: TextSegmentProps) {
    const { handleWordClick, handleWordDoubleClick } = useWordClick({
        onElementClick,
        onWordClick
    })

    const shouldWordFlash = (wordPos: WordPosition): boolean => {
        const hasCorrections = 'corrections' in (wordPos.sequence || {}) &&
            (wordPos.sequence as GapSequence)?.corrections?.length > 0

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
    }

    return (
        <Typography
            component="pre"
            sx={{
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                lineHeight: 1.5,
            }}
        >
            {wordPositions.map((wordPos, index) => {
                const anchorSequence = wordPos.type === 'anchor' ? wordPos.sequence as AnchorSequence : undefined
                const gapSequence = wordPos.type === 'gap' ? wordPos.sequence as GapSequence : undefined

                return (
                    <Word
                        key={`${wordPos.word}-${index}`}
                        word={wordPos.word}
                        shouldFlash={shouldWordFlash(wordPos)}
                        isAnchor={Boolean(anchorSequence)}
                        isCorrectedGap={Boolean(gapSequence)}
                        onClick={() => handleWordClick(
                            wordPos.word,
                            wordPos.position,
                            anchorSequence,
                            gapSequence
                        )}
                        onDoubleClick={() => handleWordDoubleClick(
                            wordPos.word,
                            wordPos.position,
                            anchorSequence,
                            gapSequence
                        )}
                    />
                )
            })}
        </Typography>
    )
}

// Memoize the component to prevent unnecessary re-renders
export const TextSegment = React.memo(TextSegmentComponent) 