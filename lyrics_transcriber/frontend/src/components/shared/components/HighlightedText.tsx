import { Typography, Box } from '@mui/material'
import { Word } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import { AnchorSequence, GapSequence, HighlightInfo, InteractionMode } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import { WordClickInfo, TranscriptionWordPosition, FlashType, LinePosition } from '../types'
import React from 'react'
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import IconButton from '@mui/material/IconButton';

export interface HighlightedTextProps {
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
    currentSource?: string
    preserveSegments?: boolean
    linePositions?: LinePosition[]
    currentTime?: number
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
    linePositions = [],
    currentTime = 0
}: HighlightedTextProps) {
    const { handleWordClick } = useWordClick({
        mode,
        onElementClick,
        onWordClick,
        isReference,
        currentSource
    })

    const shouldWordFlash = (wordPos: TranscriptionWordPosition | { word: string; index: number }): boolean => {
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
                            (wordPos.sequence as AnchorSequence).reference_positions[currentSource as keyof typeof highlightInfo.referenceIndices] === 
                            highlightInfo.referenceIndices?.[currentSource as keyof typeof highlightInfo.referenceIndices])
                    ))
            )
        } else {
            // Handle reference word
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
                    (isReference && currentSource && 
                        anchor.reference_positions[currentSource as keyof typeof highlightInfo.referenceIndices] === 
                        highlightInfo.referenceIndices?.[currentSource as keyof typeof highlightInfo.referenceIndices])
                ))
            )
        }
    }

    const shouldHighlightWord = (wordPos: TranscriptionWordPosition): boolean => {
        if (!currentTime || !wordPos.word.start_time || !wordPos.word.end_time) return false
        return currentTime >= wordPos.word.start_time && currentTime <= wordPos.word.end_time
    }

    const handleCopyLine = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const renderContent = () => {
        if (wordPositions) {
            return wordPositions.map((wordPos, index) => (
                <React.Fragment key={`${wordPos.word.text}-${index}`}>
                    <Word
                        word={wordPos.word.text}
                        shouldFlash={shouldWordFlash(wordPos)}
                        isCurrentlyPlaying={shouldHighlightWord(wordPos)}
                        isAnchor={wordPos.type === 'anchor'}
                        isCorrectedGap={wordPos.type === 'gap' && Boolean((wordPos.sequence as GapSequence)?.corrections?.length)}
                        isUncorrectedGap={wordPos.type === 'gap' && !(wordPos.sequence as GapSequence)?.corrections?.length}
                        onClick={() => handleWordClick(
                            wordPos.word.text,
                            wordPos.position,
                            wordPos.type === 'anchor' ? wordPos.sequence as AnchorSequence : undefined,
                            wordPos.type === 'gap' ? wordPos.sequence as GapSequence : undefined
                        )}
                    />
                    {index < wordPositions.length - 1 && ' '}
                </React.Fragment>
            ))
        } else if (text) {
            const lines = text.split('\n')
            let globalWordIndex = 0

            return lines.map((line, lineIndex) => {
                const currentLinePosition = linePositions?.find((pos: LinePosition) => pos.position === globalWordIndex)
                if (currentLinePosition?.isEmpty) {
                    globalWordIndex++
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
                            <Box sx={{ width: '28px' }} /> {/* Space for copy button */}
                            <Box sx={{ flex: 1, height: '1.5em' }} />
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
                        <IconButton
                            size="small"
                            onClick={() => handleCopyLine(line)}
                            sx={{
                                padding: '2px',
                                marginRight: 1,
                                height: '24px',
                                width: '24px'
                            }}
                        >
                            <ContentCopyIcon sx={{ fontSize: '1rem' }} />
                        </IconButton>
                        <Box sx={{ flex: 1 }}>
                            {lineContent.map((word, wordIndex) => {
                                if (word === '') return null
                                if (/^\s+$/.test(word)) {
                                    return <span key={`space-${lineIndex}-${wordIndex}`}> </span>
                                }

                                const position = globalWordIndex++
                                const anchor = anchors.find(a => {
                                    const refPos = a.reference_positions[currentSource!]
                                    if (refPos === undefined) return false
                                    return position >= refPos && position < refPos + a.length
                                })

                                // Create a mock TranscriptionWordPosition for highlighting
                                const wordPos: TranscriptionWordPosition = {
                                    word: { text: word },
                                    position,
                                    type: anchor ? 'anchor' : 'other',
                                    sequence: anchor,
                                    isInRange: true
                                }

                                return (
                                    <Word
                                        key={`${word}-${lineIndex}-${wordIndex}`}
                                        word={word}
                                        shouldFlash={shouldWordFlash({ word, index: position })}
                                        isCurrentlyPlaying={shouldHighlightWord(wordPos)}
                                        isAnchor={Boolean(anchor)}
                                        isCorrectedGap={false}
                                        isUncorrectedGap={false}
                                        onClick={() => handleWordClick(word, position, anchor, undefined)}
                                    />
                                )
                            })}
                        </Box>
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
                lineHeight: 1.5
            }}
        >
            {renderContent()}
        </Typography>
    )
} 