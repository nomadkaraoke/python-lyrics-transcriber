import { Typography, Box } from '@mui/material'
import { Word as WordComponent } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import { AnchorSequence, GapSequence, HighlightInfo, InteractionMode, LyricsSegment, Word } from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import type { FlashType, LinePosition, TranscriptionWordPosition, WordClickInfo } from '../types'
import React from 'react'
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import IconButton from '@mui/material/IconButton';

export interface HighlightedTextProps {
    text?: string
    segments?: LyricsSegment[]
    wordPositions: TranscriptionWordPosition[]
    anchors: AnchorSequence[]
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    isReference?: boolean
    currentSource?: string
    preserveSegments?: boolean
    linePositions?: LinePosition[]
    currentTime?: number
    referenceCorrections?: Map<string, string>
    gaps?: GapSequence[]
}

export function HighlightedText({
    text,
    segments,
    wordPositions = [] as TranscriptionWordPosition[],
    anchors,
    highlightInfo,
    mode,
    onElementClick,
    onWordClick,
    flashingType,
    isReference,
    currentSource = '',
    preserveSegments = false,
    linePositions = [],
    currentTime = 0,
    referenceCorrections = new Map(),
    gaps = []
}: HighlightedTextProps) {
    const { handleWordClick } = useWordClick({
        mode,
        onElementClick,
        onWordClick,
        isReference,
        currentSource,
        gaps,
        anchors
    })

    const shouldWordFlash = (wordPos: TranscriptionWordPosition | { word: string; id: string }): boolean => {
        if (!flashingType) return false

        if ('type' in wordPos) {
            const gap = wordPos.sequence as GapSequence
            const isCorrected = (
                // Check gap corrections
                (wordPos.type === 'gap' &&
                    gap?.corrections?.some(correction =>
                        correction.word_id === wordPos.word.id)) ||
                // Also check main corrections array
                wordPos.isCorrected
            )

            return Boolean(
                (flashingType === 'anchor' && wordPos.type === 'anchor') ||
                (flashingType === 'corrected' && isCorrected) ||
                (flashingType === 'uncorrected' && wordPos.type === 'gap' && !isCorrected) ||
                (flashingType === 'word' && (
                    // For anchors
                    (highlightInfo?.type === 'anchor' && wordPos.type === 'anchor' &&
                        (isReference && currentSource
                            ? (highlightInfo.sequence as AnchorSequence).reference_words[currentSource]?.some(w => w.id === wordPos.word.id)
                            : highlightInfo.sequence?.transcribed_words.some(w => w.id === wordPos.word.id)
                        )) ||
                    // For gaps
                    (highlightInfo?.type === 'gap' && wordPos.type === 'gap' &&
                        (isReference && currentSource
                            ? (highlightInfo.sequence as GapSequence).reference_words[currentSource]?.some(w => w.id === wordPos.word.id)
                            : (highlightInfo.sequence as GapSequence)?.transcribed_words.some(w => w.id === wordPos.word.id))
                    ) ||
                    // For corrections
                    (highlightInfo?.type === 'correction' && isReference && currentSource &&
                        highlightInfo.correction?.reference_positions?.[currentSource]?.toString() === wordPos.word.id)
                ))
            )
        }
        return false
    }

    const shouldHighlightWord = (wordPos: TranscriptionWordPosition | { word: string; id: string }): boolean => {
        if ('type' in wordPos && currentTime !== undefined && 'start_time' in wordPos.word) {
            const word = wordPos.word as Word  // Type assertion to ensure we have the full Word type
            return word.start_time !== null &&
                word.end_time !== null &&
                currentTime >= word.start_time &&
                currentTime <= word.end_time
        }
        return false
    }

    const handleCopyLine = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const renderContent = () => {
        if (wordPositions && !segments) {
            return wordPositions.map((wordPos, index) => (
                <React.Fragment key={wordPos.word.id}>
                    <WordComponent
                        key={`${wordPos.word.id}-${index}`}
                        word={wordPos.word.text}
                        shouldFlash={shouldWordFlash(wordPos)}
                        isAnchor={wordPos.type === 'anchor'}
                        isCorrectedGap={wordPos.isCorrected}
                        isUncorrectedGap={wordPos.type === 'gap' && !wordPos.isCorrected}
                        isCurrentlyPlaying={shouldHighlightWord(wordPos)}
                        onClick={() => handleWordClick(
                            wordPos.word.text,
                            wordPos.word.id,
                            wordPos.type === 'anchor' ? wordPos.sequence as AnchorSequence : undefined,
                            wordPos.type === 'gap' ? wordPos.sequence as GapSequence : undefined
                        )}
                    />
                    {index < wordPositions.length - 1 && ' '}
                </React.Fragment>
            ))
        } else if (segments) {
            return segments.map((segment) => (
                <Box key={segment.id} sx={{ display: 'flex', alignItems: 'flex-start' }}>
                    <Box sx={{ flex: 1 }}>
                        {segment.words.map((word, wordIndex) => {
                            const wordPos = wordPositions.find((pos: TranscriptionWordPosition) =>
                                pos.word.id === word.id
                            );

                            const anchor = wordPos?.type === 'anchor' ? anchors?.find(a =>
                                a.reference_words[currentSource]?.some(w => w.id === word.id)
                            ) : undefined;

                            const hasCorrection = referenceCorrections.has(word.id);
                            const isUncorrectedGap = wordPos?.type === 'gap' && !hasCorrection;

                            const sequence = wordPos?.type === 'gap' ? wordPos.sequence as GapSequence : undefined;

                            return (
                                <React.Fragment key={word.id}>
                                    <WordComponent
                                        word={word.text}
                                        shouldFlash={shouldWordFlash(wordPos || { word: word.text, id: word.id })}
                                        isAnchor={Boolean(anchor)}
                                        isCorrectedGap={hasCorrection}
                                        isUncorrectedGap={isUncorrectedGap}
                                        isCurrentlyPlaying={shouldHighlightWord(wordPos || { word: word.text, id: word.id })}
                                        onClick={() => handleWordClick(word.text, word.id, anchor, sequence)}
                                    />
                                    {wordIndex < segment.words.length - 1 && ' '}
                                </React.Fragment>
                            );
                        })}
                    </Box>
                </Box>
            ));
        } else if (text) {
            const lines = text.split('\n')
            let wordCount = 0

            return lines.map((line, lineIndex) => {
                const currentLinePosition = linePositions?.find(pos => pos.position === wordCount)
                if (currentLinePosition?.isEmpty) {
                    wordCount++
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
                            {currentLinePosition?.lineNumber ?? lineIndex}
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

                                const wordId = `${currentSource}-word-${wordCount}`
                                wordCount++

                                const anchor = currentSource ? anchors?.find(a =>
                                    a.reference_words[currentSource]?.some(w => w.id === wordId)
                                ) : undefined

                                const hasCorrection = referenceCorrections.has(wordId)

                                return (
                                    <WordComponent
                                        key={wordId}
                                        word={word}
                                        shouldFlash={shouldWordFlash({ word, id: wordId })}
                                        isAnchor={Boolean(anchor)}
                                        isCorrectedGap={hasCorrection}
                                        isUncorrectedGap={false}
                                        isCurrentlyPlaying={shouldHighlightWord({ word, id: wordId })}
                                        onClick={() => handleWordClick(word, wordId, anchor, undefined)}
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