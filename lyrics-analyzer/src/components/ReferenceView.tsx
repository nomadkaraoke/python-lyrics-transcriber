import { useState } from 'react'
import { Box, Button, Paper, Typography } from '@mui/material'
import { LyricsData } from '../types'
import { ModalContent } from './LyricsAnalyzer'
import { COLORS } from './LyricsAnalyzer'

interface ReferenceViewProps {
    referenceTexts: Record<string, string>
    anchors: LyricsData['anchor_sequences']
    onElementClick: (content: ModalContent) => void
}

export default function ReferenceView({
    referenceTexts,
    anchors,
    onElementClick,
}: ReferenceViewProps) {
    const [currentSource, setCurrentSource] = useState<'genius' | 'spotify'>('genius')

    const toggleSource = () => {
        setCurrentSource(current => (current === 'genius' ? 'spotify' : 'genius'))
    }

    const renderHighlightedText = () => {
        const text = referenceTexts[currentSource]
        if (!text) return null

        const words = text.split(/(\s+)/)
        let currentIndex = 0

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word // Return whitespace as-is
            }

            // Find anchor that contains this word position
            const anchor = anchors.find(a => {
                const position = a.reference_positions[currentSource]
                if (position === undefined) return false
                return currentIndex >= position && currentIndex < position + a.length
            })

            const wordElement = anchor ? (
                <span
                    key={index}
                    className="anchor"
                    onClick={() => onElementClick({
                        type: 'anchor',
                        data: {
                            ...anchor,
                            position: currentIndex
                        }
                    })}
                    style={{
                        backgroundColor: COLORS.anchor,
                        padding: '2px 4px',
                        borderRadius: '3px',
                        cursor: 'pointer',
                        display: 'inline-block',
                        marginRight: '0.25em',
                    }}
                >
                    {word}
                </span>
            ) : (
                <span
                    key={index}
                    style={{
                        display: 'inline-block',
                        marginRight: '0.25em',
                    }}
                >
                    {word}
                </span>
            )

            currentIndex++ // Increment for all non-whitespace words
            return wordElement
        })
    }

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Reference Text</Typography>
                <Button
                    variant="outlined"
                    size="small"
                    onClick={toggleSource}
                    sx={{ textTransform: 'capitalize' }}
                >
                    {currentSource}
                </Button>
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