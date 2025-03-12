import { Typography, Box } from '@mui/material'
import { WordComponent } from './Word'
import { useWordClick } from '../hooks/useWordClick'
import {
    AnchorSequence,
    GapSequence,
    HighlightInfo,
    InteractionMode,
    LyricsSegment,
    Word,
    WordCorrection
} from '../../../types'
import { ModalContent } from '../../LyricsAnalyzer'
import type { FlashType, LinePosition, TranscriptionWordPosition, WordClickInfo } from '../types'
import React from 'react'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import IconButton from '@mui/material/IconButton'
import { getWordsFromIds } from '../utils/wordUtils'

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
    flashingHandler?: string | null
    corrections?: WordCorrection[]
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
    gaps = [],
    flashingHandler,
    corrections = [],
}: HighlightedTextProps) {
    const { handleWordClick } = useWordClick({
        mode,
        onElementClick,
        onWordClick,
        isReference,
        currentSource,
        gaps,
        anchors,
        corrections
    })

    const shouldWordFlash = (wordPos: TranscriptionWordPosition | { word: string; id: string }): boolean => {
        if (!flashingType) {
            return false;
        }

        if ('type' in wordPos) {
            // Add handler-specific flashing
            if (flashingType === 'handler' && flashingHandler) {
                console.log('Checking handler flash for word:', wordPos.word.text);
                console.log('Current flashingHandler:', flashingHandler);
                console.log('Word ID:', wordPos.word.id);

                const shouldFlash = corrections.some(correction =>
                    correction.handler === flashingHandler &&
                    (correction.corrected_word_id === wordPos.word.id ||
                        correction.word_id === wordPos.word.id)
                );

                console.log('Should flash:', shouldFlash);
                return shouldFlash;
            }

            const gap = wordPos.sequence as GapSequence
            const isCorrected = (
                // Check corrections array for this word
                corrections.some(correction =>
                    (correction.word_id === wordPos.word.id ||
                        correction.corrected_word_id === wordPos.word.id) &&
                    gap.transcribed_word_ids.includes(correction.word_id)
                ) ||
                // Also check if marked as corrected in wordPos
                wordPos.isCorrected
            )

            return Boolean(
                (flashingType === 'anchor' && wordPos.type === 'anchor') ||
                (flashingType === 'corrected' && isCorrected) ||
                (flashingType === 'uncorrected' && wordPos.type === 'gap' && !isCorrected) ||
                (flashingType === 'word' && (
                    // For anchors
                    (highlightInfo?.type === 'anchor' && wordPos.type === 'anchor' &&
                        (isReference && currentSource && highlightInfo.sequence
                            ? getWordsFromIds(segments || [],
                                (highlightInfo.sequence as AnchorSequence).reference_word_ids[currentSource] || []
                            ).some(w => w.id === wordPos.word.id)
                            : getWordsFromIds(segments || [],
                                (highlightInfo.sequence as AnchorSequence).transcribed_word_ids
                            ).some(w => w.id === wordPos.word.id)
                        )) ||
                    // For gaps
                    (highlightInfo?.type === 'gap' && wordPos.type === 'gap' &&
                        (isReference && currentSource && highlightInfo.sequence
                            ? getWordsFromIds(segments || [],
                                (highlightInfo.sequence as GapSequence).reference_word_ids[currentSource] || []
                            ).some(w => w.id === wordPos.word.id)
                            : getWordsFromIds(segments || [],
                                (highlightInfo.sequence as GapSequence).transcribed_word_ids
                            ).some(w => w.id === wordPos.word.id))
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
        // Don't highlight words in reference view
        if (isReference) return false

        if ('type' in wordPos && currentTime !== undefined && 'start_time' in wordPos.word) {
            const word = wordPos.word as Word
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
                        correction={(() => {
                            const correction = corrections?.find(c => 
                                c.corrected_word_id === wordPos.word.id || 
                                c.word_id === wordPos.word.id
                            );
                            return correction ? {
                                originalWord: correction.original_word,
                                handler: correction.handler,
                                confidence: correction.confidence,
                                source: correction.source
                            } : null;
                        })()}
                    />
                    {index < wordPositions.length - 1 && ' '}
                </React.Fragment>
            ))
        } else if (segments) {
            return segments.map((segment) => (
                <Box key={segment.id} sx={{ 
                    display: 'flex', 
                    alignItems: 'flex-start',
                    mb: 0
                }}>
                    <Box sx={{ flex: 1 }}>
                        {segment.words.map((word, wordIndex) => {
                            const wordPos = wordPositions.find((pos: TranscriptionWordPosition) =>
                                pos.word.id === word.id
                            );

                            const anchor = wordPos?.type === 'anchor' ? anchors?.find(a =>
                                (a.reference_word_ids[currentSource] || []).includes(word.id)
                            ) : undefined;

                            const hasCorrection = referenceCorrections.has(word.id);
                            const isUncorrectedGap = wordPos?.type === 'gap' && !hasCorrection;

                            const sequence = wordPos?.type === 'gap' ? wordPos.sequence as GapSequence : undefined;

                            // Find correction information for the tooltip
                            const correction = corrections?.find(c => 
                                c.corrected_word_id === word.id || 
                                c.word_id === word.id
                            );
                            
                            const correctionInfo = correction ? {
                                originalWord: correction.original_word,
                                handler: correction.handler,
                                confidence: correction.confidence,
                                source: correction.source
                            } : null;

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
                                        correction={correctionInfo}
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
                        <Box key={`empty-${lineIndex}`} sx={{ 
                            display: 'flex', 
                            alignItems: 'flex-start',
                            mb: 0,
                            lineHeight: 1
                        }}>
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
                                    paddingTop: '1px',
                                    fontSize: '0.8rem',
                                    lineHeight: 1
                                }}
                            >
                                {currentLinePosition.lineNumber}
                            </Typography>
                            <Box sx={{ width: '18px' }} />
                            <Box sx={{ flex: 1, height: '1em' }} />
                        </Box>
                    )
                }

                const words = line.split(' ')
                const lineWords: React.ReactNode[] = []
                
                words.forEach((word, wordIndex) => {
                    if (word === '') return null
                    if (/^\s+$/.test(word)) {
                        return lineWords.push(<span key={`space-${lineIndex}-${wordIndex}`}> </span>)
                    }

                    const wordId = `${currentSource}-word-${wordCount}`
                    wordCount++

                    const anchor = currentSource ? anchors?.find(a =>
                        a.reference_word_ids[currentSource]?.includes(wordId)
                    ) : undefined

                    const hasCorrection = referenceCorrections.has(wordId)

                    lineWords.push(
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
                })

                return (
                    <Box key={`line-${lineIndex}`} sx={{ 
                        display: 'flex', 
                        alignItems: 'flex-start',
                        mb: 0,
                        lineHeight: 1
                    }}>
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
                                paddingTop: '1px',
                                fontSize: '0.8rem',
                                lineHeight: 1
                            }}
                        >
                            {currentLinePosition?.lineNumber ?? lineIndex}
                        </Typography>
                        <IconButton
                            size="small"
                            onClick={() => handleCopyLine(line)}
                            sx={{
                                padding: '1px',
                                marginRight: 0.5,
                                height: '18px',
                                width: '18px',
                                minHeight: '18px',
                                minWidth: '18px'
                            }}
                        >
                            <ContentCopyIcon sx={{ fontSize: '0.9rem' }} />
                        </IconButton>
                        <Box sx={{ flex: 1 }}>
                            {lineWords}
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