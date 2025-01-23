import { useState } from 'react'
import { Paper, Typography, Box, Button, Tooltip } from '@mui/material'
import { HighlightInfo, LyricsData, LyricsSegment } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: LyricsData['anchor_sequences'][0]
    gap?: LyricsData['gap_sequences'][0]
}

interface ReferenceViewProps {
    referenceTexts: Record<string, string>
    anchors: LyricsData['anchor_sequences']
    gaps: LyricsData['gap_sequences']
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    corrected_segments: LyricsSegment[]
    highlightedWordIndex?: number
    highlightInfo: HighlightInfo | null
}

export default function ReferenceView({
    referenceTexts,
    anchors,
    gaps,
    onElementClick,
    onWordClick,
    flashingType,
    corrected_segments,
    highlightedWordIndex,
    highlightInfo,
}: ReferenceViewProps) {
    const [currentSource, setCurrentSource] = useState<'genius' | 'spotify'>('genius')

    const renderHighlightedText = () => {
        const text = referenceTexts[currentSource]
        if (!text) return null

        // Normalize reference text by removing all newlines and reducing multiple spaces to single
        const normalizedRefText = text.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim()

        // Split into words while preserving spaces
        const words = normalizedRefText.split(/(\s+)/)
        let currentIndex = 0

        // Find the end-of-line anchors from corrected_segments and store segment info
        const newlineInfo = new Map<number, string>()
        const newlineIndices = new Set(
            corrected_segments.slice(0, -1).map((segment, segmentIndex) => {
                // Get the last word position in this segment
                const segmentWords = segment.text.trim().split(/\s+/)
                const lastWord = segmentWords[segmentWords.length - 1]

                // Find the anchor that contains this last word
                const matchingAnchor = anchors.find(a => {
                    const transcriptionStart = a.transcription_position
                    const transcriptionEnd = transcriptionStart + a.length
                    const lastWordPosition = corrected_segments
                        .slice(0, segmentIndex)
                        .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0) + segmentWords.length - 1

                    return lastWordPosition >= transcriptionStart && lastWordPosition < transcriptionEnd
                })

                if (!matchingAnchor) {
                    console.warn(`Could not find anchor for segment end: "${segment.text.trim()}"`)
                    return null
                }

                const refPosition = matchingAnchor.reference_positions[currentSource]
                if (refPosition === undefined) return null

                // Calculate the offset from the anchor's start to our word
                const wordOffsetInAnchor = matchingAnchor.words.indexOf(lastWord)
                const finalPosition = refPosition + wordOffsetInAnchor + 1  // Add 1 to get position after the word

                // Store the segment text for this position
                newlineInfo.set(finalPosition, segment.text.trim())

                // console.log(
                //     `Segment ${segmentIndex}: "${segment.text.trim()}" → ` +
                //     `Last word "${lastWord}" found in anchor "${matchingAnchor.text}" → ` +
                //     `Newline after reference position ${finalPosition} (ref_pos ${refPosition} + offset ${wordOffsetInAnchor} + 1)`
                // )

                return finalPosition
            }).filter((pos): pos is number => pos !== null)
        )

        const elements: React.ReactNode[] = []

        words.forEach((word, index) => {
            // Skip whitespace without incrementing word index
            if (/^\s+$/.test(word)) {
                elements.push(word)
                return
            }

            const thisWordIndex = currentIndex

            if (newlineIndices.has(thisWordIndex)) {
                elements.push(
                    <Tooltip
                        key={`newline-${thisWordIndex}`}
                        title={
                            `Newline inserted after word position ${thisWordIndex}\n` +
                            `End of segment: "${newlineInfo.get(thisWordIndex)}"`
                        }
                    >
                        <span
                            style={{
                                cursor: 'help',
                                color: '#666',
                                backgroundColor: '#eee',
                                padding: '0 4px',
                                borderRadius: '3px',
                                margin: '0 2px'
                            }}
                        >
                            ↵
                        </span>
                    </Tooltip>
                )
                elements.push('\n')
            }

            const anchor = anchors.find(a => {
                const position = a.reference_positions[currentSource]
                if (position === undefined) return false
                return thisWordIndex >= position && thisWordIndex < position + a.length
            })

            const correctedGap = gaps.find(g => {
                if (!g.corrections.length) return false
                const correction = g.corrections[0]
                const position = correction.reference_positions?.[currentSource]
                if (position === undefined) return false
                return thisWordIndex >= position && thisWordIndex < position + correction.length
            })

            const shouldHighlight = (() => {
                if (flashingType === 'anchor' && anchor) {
                    return true
                }
                
                if (flashingType === 'word' && highlightInfo?.type === 'anchor' && anchor) {
                    // Check if this word is part of the highlighted anchor sequence
                    const refPos = anchor.reference_positions[currentSource]
                    const highlightPos = highlightInfo.referenceIndices[currentSource]
                    
                    console.log('Checking word highlight:', {
                        wordIndex: thisWordIndex,
                        refPos,
                        highlightPos,
                        anchorLength: anchor.length,
                        isInRange: thisWordIndex >= refPos && thisWordIndex < refPos + anchor.length
                    })
                    
                    return refPos === highlightPos && 
                           anchor.length === highlightInfo.referenceLength &&
                           thisWordIndex >= refPos && 
                           thisWordIndex < refPos + anchor.length
                }
                
                return false
            })()

            elements.push(
                <HighlightedWord
                    key={`${word}-${index}-${shouldHighlight}`}
                    shouldFlash={shouldHighlight}
                    style={{
                        backgroundColor: flashingType === 'word' && highlightedWordIndex === thisWordIndex
                            ? COLORS.highlighted
                            : anchor
                                ? COLORS.anchor
                                : correctedGap
                                    ? COLORS.corrected
                                    : 'transparent',
                        padding: (anchor || correctedGap) ? '2px 4px' : '0',
                        borderRadius: '3px',
                        cursor: 'pointer',
                    }}
                    onClick={(e) => {
                        if (e.detail === 1) {
                            setTimeout(() => {
                                if (!e.defaultPrevented) {
                                    onWordClick?.({
                                        wordIndex: thisWordIndex,
                                        type: anchor ? 'anchor' : correctedGap ? 'gap' : 'other',
                                        anchor,
                                        gap: correctedGap
                                    })
                                }
                            }, 200)
                        }
                    }}
                    onDoubleClick={(e) => {
                        e.preventDefault()  // Prevent single-click from firing
                        if (anchor) {
                            onElementClick({
                                type: 'anchor',
                                data: {
                                    ...anchor,
                                    position: thisWordIndex
                                }
                            })
                        } else if (correctedGap) {
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...correctedGap,
                                    position: thisWordIndex,
                                    word: word
                                }
                            })
                        }
                    }}
                >
                    {word}
                </HighlightedWord>
            )

            currentIndex++ // Increment after using the current position
        })

        return elements
    }

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    Reference Text
                </Typography>
                <Box>
                    <Button
                        size="small"
                        variant={currentSource === 'genius' ? 'contained' : 'outlined'}
                        onClick={() => setCurrentSource('genius')}
                        sx={{ mr: 1 }}
                    >
                        Genius
                    </Button>
                    <Button
                        size="small"
                        variant={currentSource === 'spotify' ? 'contained' : 'outlined'}
                        onClick={() => setCurrentSource('spotify')}
                    >
                        Spotify
                    </Button>
                </Box>
            </Box>
            <Typography
                component="pre"
                sx={{
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    margin: 0,
                    lineHeight: 1.5,
                }}
            >
                {renderHighlightedText()}
            </Typography>
        </Paper>
    )
} 