import { useMemo } from 'react'
import { Paper, Typography, Box, Button } from '@mui/material'
import { HighlightInfo, LyricsData, LyricsSegment, InteractionMode } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { Word } from './TranscriptionView/components/Word'

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
    currentSource: 'genius' | 'spotify'
    onSourceChange: (source: 'genius' | 'spotify') => void
    highlightInfo: HighlightInfo | null
    mode: InteractionMode
}

export default function ReferenceView({
    referenceTexts,
    anchors,
    gaps,
    onElementClick,
    onWordClick,
    corrected_segments,
    currentSource,
    onSourceChange,
    highlightInfo,
    mode
}: ReferenceViewProps) {
    const { newlineIndices } = useMemo(() => {
        const newlineIndices = new Set(
            corrected_segments.slice(0, -1).map((segment, segmentIndex) => {
                const segmentText = segment.text.trim()
                const segmentWords = segmentText.split(/\s+/)
                const segmentStartWord = corrected_segments
                    .slice(0, segmentIndex)
                    .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0)
                const lastWordPosition = segmentStartWord + segmentWords.length - 1

                const matchingAnchor = anchors.find(a => {
                    const start = a.transcription_position
                    const end = start + a.length - 1
                    return lastWordPosition >= start && lastWordPosition <= end
                })

                if (matchingAnchor?.reference_positions[currentSource] !== undefined) {
                    const anchorWords = matchingAnchor.words
                    const wordIndex = anchorWords.findIndex(w =>
                        w.toLowerCase() === segmentWords[segmentWords.length - 1].toLowerCase()
                    )

                    if (wordIndex !== -1) {
                        return matchingAnchor.reference_positions[currentSource] + wordIndex
                    }
                }

                return null
            }).filter((pos): pos is number => pos !== null && pos >= 0)
        )
        return { newlineIndices }
    }, [corrected_segments, anchors, currentSource])

    const renderHighlightedText = () => {
        const elements: React.ReactNode[] = []
        const words = referenceTexts[currentSource].split(/\s+/)
        let currentIndex = 0

        words.forEach((word, index) => {
            const thisWordIndex = currentIndex
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

            const isHighlighted = Boolean(
                highlightInfo &&
                highlightInfo.type === 'anchor' &&
                highlightInfo.referenceIndices[currentSource] !== undefined &&
                thisWordIndex >= highlightInfo.referenceIndices[currentSource] &&
                thisWordIndex < highlightInfo.referenceIndices[currentSource] + highlightInfo.referenceLength!
            )

            elements.push(
                <Word
                    key={`${word}-${index}`}
                    word={word}
                    shouldFlash={isHighlighted}
                    isAnchor={Boolean(anchor)}
                    isCorrectedGap={Boolean(correctedGap)}
                    onClick={() => {
                        if (mode === 'highlight') {
                            onWordClick?.({
                                wordIndex: thisWordIndex,
                                type: anchor ? 'anchor' : correctedGap ? 'gap' : 'other',
                                anchor,
                                gap: correctedGap
                            })
                        } else if (mode === 'details') {
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
                        }
                    }}
                />
            )

            if (newlineIndices.has(thisWordIndex)) {
                elements.push(<br key={`br-${index}`} />)
            } else {
                elements.push(' ')
            }

            currentIndex++
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
                        onClick={() => onSourceChange('genius')}
                        sx={{ mr: 1 }}
                    >
                        Genius
                    </Button>
                    <Button
                        size="small"
                        variant={currentSource === 'spotify' ? 'contained' : 'outlined'}
                        onClick={() => onSourceChange('spotify')}
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