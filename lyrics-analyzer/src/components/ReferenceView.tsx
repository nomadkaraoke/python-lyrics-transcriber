import { useState } from 'react'
import { Paper, Typography, Box, Button, Tooltip } from '@mui/material'
import { LyricsData, LyricsSegment } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface ReferenceViewProps {
    referenceTexts: Record<string, string>
    anchors: LyricsData['anchor_sequences']
    gaps: LyricsData['gap_sequences']
    onElementClick: (content: ModalContent) => void
    flashingType: FlashType
    corrected_segments: LyricsSegment[]
}

export default function ReferenceView({
    referenceTexts,
    anchors,
    gaps,
    onElementClick,
    flashingType,
    corrected_segments,
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

        // Track which indices should have line breaks based on segments
        const newlineIndices = new Set(
            corrected_segments.slice(0, -1).map(segment => 
                segment.text.split(/\s+/).length
            ).reduce<number[]>((acc, len) => {
                const lastIndex = acc.length ? acc[acc.length - 1] : 0
                acc.push(lastIndex + len)
                return acc
            }, [])
        )

        const elements: React.ReactNode[] = []

        words.forEach((word, index) => {
            // Skip whitespace without incrementing word index
            if (/^\s+$/.test(word)) {
                elements.push(word)
                return
            }

            const thisWordIndex = currentIndex // Store current position for this word

            if (newlineIndices.has(currentIndex)) {
                elements.push(
                    <Tooltip 
                        key={`newline-${currentIndex}`}
                        title={`Newline inserted after word position ${currentIndex}`}
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

            const shouldFlash = Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'corrected' && correctedGap)
            )

            elements.push(
                <HighlightedWord
                    key={`${word}-${index}-${shouldFlash}`}
                    shouldFlash={shouldFlash}
                    style={{
                        backgroundColor: anchor
                            ? COLORS.anchor
                            : correctedGap
                                ? COLORS.corrected
                                : 'transparent',
                        padding: (anchor || correctedGap) ? '2px 4px' : '0',
                        borderRadius: '3px',
                        cursor: (anchor || correctedGap) ? 'pointer' : 'default',
                    }}
                    onClick={() => {
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