import { Paper, Typography } from '@mui/material'
import { LyricsData } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface TranscriptionViewProps {
    data: LyricsData
    onElementClick: (content: ModalContent) => void
    flashingType: FlashType
}

export default function TranscriptionView({ data, onElementClick, flashingType }: TranscriptionViewProps) {
    console.log('TranscriptionView rendered with flashingType:', flashingType)

    const renderHighlightedText = () => {
        const normalizedText = data.corrected_text.replace(/\n\n+/g, '\n')
        const words = normalizedText.split(/(\s+)/)
        let currentIndex = 0

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word
            }

            const anchor = data.anchor_sequences.find(a => {
                const start = a.transcription_position
                const end = start + a.length
                return currentIndex >= start && currentIndex < end
            })

            const gap = data.gap_sequences.find(g => {
                const start = g.transcription_position
                const end = start + g.length
                return currentIndex >= start && currentIndex < end
            })

            const hasCorrections = gap ? gap.corrections.length > 0 : false

            const shouldFlash = Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'corrected' && hasCorrections) ||
                (flashingType === 'uncorrected' && gap && !hasCorrections)
            )

            const wordElement = (
                <HighlightedWord
                    key={`${word}-${index}-${shouldFlash}`}
                    shouldFlash={shouldFlash}
                    style={{
                        backgroundColor: anchor
                            ? COLORS.anchor
                            : hasCorrections
                                ? COLORS.corrected
                                : gap
                                    ? COLORS.uncorrectedGap
                                    : 'transparent',
                        padding: anchor || gap ? '2px 4px' : '0',
                        borderRadius: '3px',
                        cursor: anchor || gap ? 'pointer' : 'default',
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
                        } else if (gap) {
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...gap,
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
            <Typography variant="h6" gutterBottom>
                Corrected Transcription
            </Typography>
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