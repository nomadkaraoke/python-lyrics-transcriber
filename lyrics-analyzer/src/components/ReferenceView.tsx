import { useState } from 'react'
import { Paper, Typography, Box, Button } from '@mui/material'
import { LyricsData } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface ReferenceViewProps {
    referenceTexts: Record<string, string>
    anchors: LyricsData['anchor_sequences']
    gaps: LyricsData['gap_sequences']
    onElementClick: (content: ModalContent) => void
    flashingType: FlashType
}

export default function ReferenceView({
    referenceTexts,
    anchors,
    gaps,
    onElementClick,
    flashingType,
}: ReferenceViewProps) {
    const [currentSource, setCurrentSource] = useState<'genius' | 'spotify'>('genius')

    const renderHighlightedText = () => {
        const text = referenceTexts[currentSource]
        if (!text) return null

        const words = text.split(/(\s+)/)
        let currentIndex = 0

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word
            }

            const anchor = anchors.find(a => {
                const position = a.reference_positions[currentSource]
                if (position === undefined) return false
                return currentIndex >= position && currentIndex < position + a.length
            })

            const correctedGap = gaps.find(g => {
                if (!g.corrections.length) return false
                const correction = g.corrections[0]
                const position = correction.reference_positions?.[currentSource]
                if (position === undefined) return false
                return currentIndex >= position && currentIndex < position + correction.length
            })

            const shouldFlash = Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'corrected' && correctedGap)
            )

            const wordElement = (
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
                                    position: currentIndex
                                }
                            })
                        } else if (correctedGap) {
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...correctedGap,
                                    position: currentIndex,
                                    word: word
                                }
                            })
                        }
                    }}
                >
                    {word}
                </HighlightedWord>
            )

            currentIndex++
            return wordElement
        })
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