import { Paper, Typography } from '@mui/material'
import { LyricsData, HighlightInfo } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: LyricsData['anchor_sequences'][0]
    gap?: LyricsData['gap_sequences'][0]
}

interface TranscriptionViewProps {
    data: LyricsData
    onElementClick: (content: ModalContent) => void
    onWordClick?: (info: WordClickInfo) => void
    flashingType: FlashType
    highlightInfo: HighlightInfo | null
}

export default function TranscriptionView({
    data,
    onElementClick,
    onWordClick,
    flashingType,
    highlightInfo
}: TranscriptionViewProps) {
    const renderHighlightedText = () => {
        const normalizedText = data.corrected_text.replace(/\n\n+/g, '\n')
        const words = normalizedText.split(/(\s+)/)
        let wordIndex = 0  // Track actual word positions, ignoring whitespace

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

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word
            }

            const currentWordIndex = wordIndex
            const anchor = data.anchor_sequences.find(a => {
                const start = a.transcription_position
                const end = start + a.length
                return currentWordIndex >= start && currentWordIndex < end
            })

            const gap = data.gap_sequences.find(g => {
                const start = g.transcription_position
                const end = start + g.length
                return currentWordIndex >= start && currentWordIndex < end
            })

            const hasCorrections = gap ? gap.corrections.length > 0 : false

            const shouldFlash = Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'corrected' && hasCorrections) ||
                (flashingType === 'uncorrected' && gap && !hasCorrections) ||
                (flashingType === 'word' && highlightInfo?.type === 'anchor' && anchor && (
                    anchor.transcription_position === highlightInfo.transcriptionIndex &&
                    currentWordIndex >= anchor.transcription_position &&
                    currentWordIndex < anchor.transcription_position + anchor.length
                ))
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
                        cursor: 'pointer',
                    }}
                    onClick={(e) => {
                        if (e.detail === 1) {
                            setTimeout(() => {
                                if (!e.defaultPrevented) {
                                    onWordClick?.({
                                        wordIndex: currentWordIndex,
                                        type: anchor ? 'anchor' : gap ? 'gap' : 'other',
                                        anchor,
                                        gap
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
                                    position: currentWordIndex
                                }
                            })
                        } else if (gap) {
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...gap,
                                    position: currentWordIndex,
                                    word: word
                                }
                            })
                        }
                    }}
                >
                    {word}
                </HighlightedWord>
            )

            wordIndex++
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