import { Typography, Box } from '@mui/material'
import { Word } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import { AnchorSequence, GapSequence, HighlightInfo, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo, TranscriptionWordPosition, FlashType, LinePosition } from '../types'
import React from 'react'

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
    preserveSegments?: boolean
    linePositions?: LinePosition[]
}

export function HighlightedText({
    text,
    wordPositions,
    anchors,
    highlightInfo,
    mode,
    onElementClick,
    onWordClick,
    flashingType,
    isReference,
    currentSource,
    preserveSegments = false,
    linePositions = []
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
                        (wordPos.sequence as AnchorSequence).transcription_position === highlightInfo.transcriptionIndex ||
                        (isReference && currentSource &&
                            (wordPos.sequence as AnchorSequence).reference_positions[currentSource] === highlightInfo.referenceIndices?.[currentSource])
                    ))
            )
        } else {
            // Handle raw text word
            const thisWordIndex = wordPos.index
            const anchor = anchors.find(a => {
                const position = isReference
                    ? a.reference_positions[currentSource!]
                    : a.transcription_position
                if (position === undefined) return false
                return thisWordIndex >= position && thisWordIndex < position + a.length
            })

            return Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'word' && highlightInfo?.type === 'anchor' && anchor && (
                    anchor.transcription_position === highlightInfo.transcriptionIndex ||
                    (isReference && currentSource && anchor.reference_positions[currentSource] === highlightInfo.referenceIndices?.[currentSource])
                ))
            )
        }
    }

    const renderContent = () => {
        if (wordPositions) {
            // Render from word positions (for transcription view)
            return wordPositions.map((wordPos, index) => (
                <React.Fragment key={`${wordPos.word}-${index}`}>
                    <Word
                        word={wordPos.word}
                        shouldFlash={shouldWordFlash(wordPos)}
                        isAnchor={wordPos.type === 'anchor'}
                        isCorrectedGap={wordPos.type === 'gap' && Boolean((wordPos.sequence as GapSequence)?.corrections?.length)}
                        isUncorrectedGap={wordPos.type === 'gap' && !(wordPos.sequence as GapSequence)?.corrections?.length}
                        onClick={() => handleWordClick(
                            wordPos.word,
                            wordPos.position,
                            wordPos.type === 'anchor' ? wordPos.sequence as AnchorSequence : undefined,
                            wordPos.type === 'gap' ? wordPos.sequence as GapSequence : undefined
                        )}
                    />
                    {index < wordPositions.length - 1 && ' '}
                </React.Fragment>
            ))
        } else if (text) {
            // Render from raw text (for reference view)
            const lines = text.split('\n')
            let globalWordIndex = 0  // Keep track of overall word position

            return lines.map((line, lineIndex) => {
                // Find if this should be an empty line
                const currentLinePosition = linePositions?.find((pos: LinePosition) => pos.position === globalWordIndex)
                if (currentLinePosition?.isEmpty) {
                    globalWordIndex++ // Still increment for empty lines
                    return (
                        <Box key={`empty-${lineIndex}`} sx={{ display: 'flex', alignItems: 'flex-start' }}>
                            <Typography
                                component="span"
                                sx={{
                                    color: 'text.secondary',
                                    width: '2em',
                                    minWidth: '2em',
                                    textAlign: 'right',
                                    marginRight: 1,
                                    userSelect: 'none',
                                    fontFamily: 'monospace',
                                    paddingTop: '4px',
                                }}
                            >
                                {currentLinePosition.lineNumber}
                            </Typography>
                            <Box sx={{ flex: 1, height: '1.5em' }} /> {/* Empty space to maintain line height */}
                        </Box>
                    )
                }

                const lineContent = line.split(/(\s+)/)
                return (
                    <Box key={`line-${lineIndex}`} sx={{ display: 'flex', alignItems: 'flex-start' }}>
                        <Typography
                            component="span"
                            sx={{
                                color: 'text.secondary',
                                width: '2em',
                                minWidth: '2em',
                                textAlign: 'right',
                                marginRight: 1,
                                userSelect: 'none',
                                fontFamily: 'monospace',
                                paddingTop: '4px',
                            }}
                        >
                            {lineIndex}
                        </Typography>
                        <Box sx={{ flex: 1 }}>
                            {lineContent.map((word, wordIndex) => {
                                if (word === '') return null
                                if (/^\s+$/.test(word)) {
                                    return <span key={`space-${lineIndex}-${wordIndex}`}> </span>
                                }

                                const position = globalWordIndex++  // Use and increment global word counter
                                const anchor = anchors.find(a => {
                                    const refPos = a.reference_positions[currentSource!]
                                    if (refPos === undefined) return false
                                    return position >= refPos && position < refPos + a.length
                                })

                                return (
                                    <Word
                                        key={`${word}-${lineIndex}-${wordIndex}`}
                                        word={word}
                                        shouldFlash={shouldWordFlash({ word, index: position })}
                                        isAnchor={Boolean(anchor)}
                                        isCorrectedGap={false}
                                        isUncorrectedGap={false}
                                        onClick={() => handleWordClick(word, position, anchor, undefined)}
                                    />
                                )
                            })}
                        </Box>
                        {lineIndex < lines.length - 1 && <br />}
                    </Box>
                )
            })
        }

        return null
    }

    return (
        <Typography
            component="div"
            sx={{
                fontFamily: 'monospace',
                whiteSpace: preserveSegments ? 'normal' : 'pre-wrap',
                margin: 0,
                lineHeight: 1.5,
            }}
        >
            {renderContent()}
        </Typography>
    )
} 