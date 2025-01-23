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
    const renderHighlightedText = () => {
        const normalizedText = data.corrected_text.replace(/\n\n+/g, '\n')
        const words = normalizedText.split(/(\s+)/)
        let correctedIndex = 0  // Position in the corrected text
        let originalIndex = 0   // Position in the original text

        // Build a map of original positions to their corrections
        const correctionMap = new Map()
        data.gap_sequences.forEach(gap => {
            gap.corrections.forEach(c => {
                correctionMap.set(c.original_position, {
                    original: c.original_word,
                    corrected: c.corrected_word,
                    is_deletion: c.is_deletion,
                    split_total: c.split_total
                })
            })
        })

        console.log('Debug: Starting render with correction map:', correctionMap)

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word
            }

            // Find the corresponding gap or anchor in the original text
            const anchor = data.anchor_sequences.find(a => {
                const start = a.transcription_position
                const end = start + a.length
                return originalIndex >= start && originalIndex < end
            })

            const gap = data.gap_sequences.find(g => {
                const start = g.transcription_position
                const end = start + g.length
                return originalIndex >= start && originalIndex < end
            })

            // Get correction info for current position
            const correction = correctionMap.get(originalIndex)
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
                                    position: anchor.transcription_position
                                }
                            })
                        } else if (gap) {
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...gap,
                                    position: gap.transcription_position,
                                    word: word
                                }
                            })
                        }
                    }}
                >
                    {word}
                </HighlightedWord>
            )

            // Update indexes based on corrections
            correctedIndex++
            if (!correction?.split_total || correction?.is_deletion) {
                originalIndex++
            }

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