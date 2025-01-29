// Add type declaration at the top of the file
declare global {
    interface Window {
        _debugWord?: string;
    }
}

import { Paper, Typography } from '@mui/material'
import { CorrectionData, AnchorSequence, HighlightInfo, GapSequence } from '../types'
import { FlashType, ModalContent } from './LyricsAnalyzer'
import { COLORS } from './constants'
import { HighlightedWord } from './styles'

interface WordClickInfo {
    wordIndex: number
    type: 'anchor' | 'gap' | 'other'
    anchor?: AnchorSequence
    gap?: CorrectionData['gap_sequences'][0]
}

interface TranscriptionViewProps {
    data: CorrectionData
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
        // Define interface for word position tracking
        interface WordPosition {
            word: string;
            position: number;
        }

        let currentPosition = 0;
        const wordPositions: WordPosition[] = [];

        // Create a type that captures the common properties we need
        type SequenceWithWords = {
            text: string;
            words: string[];
            transcription_position: number;
        };

        // Cast sequences to common type for concat
        const allSequences = (data.anchor_sequences as SequenceWithWords[])
            .concat(data.gap_sequences as SequenceWithWords[])
            .sort((a, b) => a.transcription_position - b.transcription_position);

        // Debug the position calculation
        allSequences.forEach(sequence => {
            sequence.words.forEach(word => {
                wordPositions.push({
                    word,
                    position: currentPosition++
                });
            });
        });

        console.log('Word position map:', wordPositions);

        // Debug the initial data state
        console.log('Initial sequence data:', {
            anchors: data.anchor_sequences.map(a => ({
                text: a.text,
                position: a.transcription_position,
                wordCount: a.words.length
            })),
            gaps: data.gap_sequences.map(g => ({
                text: g.text,
                position: g.transcription_position,
                wordCount: g.words.length,
                corrections: g.corrections
            }))
        })

        // Create a copy of the data without gap corrections
        const uncorrectedData = {
            ...data,
            gap_sequences: data.gap_sequences.map(g => ({
                ...g,
                corrections: []
            }))
        }

        // Debug the data after removing corrections
        console.log('Data without corrections:', {
            anchors: uncorrectedData.anchor_sequences.map(a => ({
                text: a.text,
                position: a.transcription_position,
                wordCount: a.words.length
            })),
            gaps: uncorrectedData.gap_sequences.map(g => ({
                text: g.text,
                position: g.transcription_position,
                wordCount: g.words.length
            }))
        })

        // Use uncorrectedData for rendering
        const normalizedText = uncorrectedData.corrected_text.replace(/\n\n+/g, '\n')
        const words = normalizedText.split(/(\s+)/)
        let wordIndex = 0

        // Inside renderHighlightedText, before processing words
        console.log('All anchor sequences:', data.anchor_sequences.map(a => ({
            text: a.text,
            position: a.transcription_position,
            wordCount: a.words.length,
            words: a.words
        })));

        return words.map((word, index) => {
            if (/^\s+$/.test(word)) {
                return word
            }

            // Increment wordIndex first, before any boundary checks
            wordIndex++
            const adjustedPosition = wordIndex - 1  // Use previous index since we just incremented

            // Debug the word index calculation when it's our target word
            if (window._debugWord === word) {
                const matchingAnchor = data.anchor_sequences.find(a => a.text.includes(word))
                const matchingGap = data.gap_sequences.find(g => g.text.includes(word))

                console.log('Word position debug:', {
                    word,
                    rawIndex: index,
                    wordIndex: wordIndex - 1,
                    adjustedPosition,
                    matchingSequences: {
                        anchor: matchingAnchor ? {
                            text: matchingAnchor.text,
                            start: matchingAnchor.transcription_position,
                            wordPosition: matchingAnchor.words.indexOf(word),
                            words: matchingAnchor.words,
                            expectedEnd: matchingAnchor.transcription_position + matchingAnchor.words.length
                        } : null,
                        gap: matchingGap ? {
                            text: matchingGap.text,
                            start: matchingGap.transcription_position,
                            wordPosition: matchingGap.words.indexOf(word),
                            words: matchingGap.words,
                            expectedEnd: matchingGap.transcription_position + matchingGap.words.length
                        } : null
                    }
                })
            }

            const anchor = data.anchor_sequences.find(anchor => {
                const start = anchor.transcription_position;
                const end = start + anchor.words.length;

                // Debug boundary check for our target word
                if (word === 'hand' || word === 'Two' || word === 'in' || word === 'the') {
                    console.group(`Anchor check for "${word}" at position ${adjustedPosition}`)
                    console.log('Checking anchor:', {
                        text: anchor.text,
                        words: anchor.words,
                        start,
                        end,
                        position: adjustedPosition,
                        isInRange: adjustedPosition >= start && adjustedPosition < end,
                        includesWord: anchor.words.includes(word),
                        wordIndex: anchor.words.indexOf(word),
                        expectedPosition: start + anchor.words.indexOf(word)
                    });
                    console.groupEnd();
                }

                // Check if the word is in this anchor's word list AND
                // if its position matches where we expect it to be
                const wordIndex = anchor.words.indexOf(word);
                if (wordIndex !== -1) {
                    const expectedPosition = start + wordIndex;
                    return Math.abs(expectedPosition - adjustedPosition) <= 1; // Allow 1 position of wiggle room
                }
                return false;
            })

            const gap = !anchor ? data.gap_sequences.find(g => {
                const start = g.transcription_position
                const end = start + g.words.length

                // Debug boundary check for our target word
                if (window._debugWord === word) {
                    console.log(`Gap boundary check for "${word}":`, {
                        gap: g.text,
                        words: g.words,
                        start,
                        end,
                        position: adjustedPosition,
                        isInRange: adjustedPosition >= start && adjustedPosition < end
                    })
                }
                return adjustedPosition >= start && adjustedPosition < end
            }) : undefined

            // Fixed type safety for corrections check
            const hasCorrections = Boolean(gap?.corrections?.length)

            const shouldFlash = Boolean(
                (flashingType === 'anchor' && anchor) ||
                (flashingType === 'corrected' && hasCorrections) ||
                (flashingType === 'uncorrected' && gap && !hasCorrections) ||
                (flashingType === 'word' && highlightInfo?.type === 'anchor' && anchor && (
                    anchor.transcription_position === highlightInfo.transcriptionIndex &&
                    adjustedPosition >= anchor.transcription_position &&
                    adjustedPosition < anchor.transcription_position + anchor.length
                ))
            )

            const wordElement = (
                <HighlightedWord
                    key={`${word}-${index}-${shouldFlash}`}
                    shouldFlash={shouldFlash}
                    style={{
                        backgroundColor: (anchor && anchor.words.includes(word))
                            ? COLORS.anchor
                            : hasCorrections
                                ? COLORS.corrected
                                : (gap && gap.words.includes(word))
                                    ? COLORS.uncorrectedGap
                                    : 'transparent',
                        padding: (anchor && anchor.words.includes(word)) || (gap && gap.words.includes(word)) ? '2px 4px' : '0',
                        borderRadius: '3px',
                        cursor: 'pointer',
                    }}
                    onClick={(e) => {
                        if (e.detail === 1) {
                            setTimeout(() => {
                                if (!e.defaultPrevented) {
                                    // First determine which sequence the word actually belongs to
                                    const belongsToAnchor = anchor && anchor.words.includes(word);
                                    const belongsToGap = gap && gap.words.includes(word);

                                    // Calculate position based on the correct sequence
                                    const sequencePosition = belongsToAnchor
                                        ? anchor.transcription_position
                                        : belongsToGap
                                            ? gap.transcription_position
                                            : adjustedPosition;

                                    const wordPosition = belongsToAnchor
                                        ? anchor.words.indexOf(word) + sequencePosition
                                        : belongsToGap
                                            ? gap.words.indexOf(word) + sequencePosition
                                            : adjustedPosition;

                                    console.group('Word Click Position Debug')
                                    console.log('Clicked word:', {
                                        word,
                                        calculatedPosition: wordPosition,
                                        originalPosition: adjustedPosition,
                                        type: belongsToAnchor ? 'anchor' : belongsToGap ? 'gap' : 'other',
                                        inAnchor: belongsToAnchor ? {
                                            text: anchor.text,
                                            start: anchor.transcription_position,
                                            end: anchor.transcription_position + anchor.length
                                        } : null,
                                        inGap: belongsToGap ? {
                                            text: gap.text,
                                            start: gap.transcription_position,
                                            end: gap.transcription_position + gap.length
                                        } : null
                                    })

                                    if (belongsToGap) {
                                        console.log('Gap details:', {
                                            position: gap.transcription_position,
                                            length: gap.length,
                                            words: gap.words,
                                            corrections: gap.corrections.map(c => ({
                                                original: c.original_word,
                                                corrected: c.corrected_word,
                                                position: c.original_position
                                            }))
                                        })
                                    }
                                    console.groupEnd()

                                    onWordClick?.({
                                        wordIndex: wordPosition,
                                        type: belongsToAnchor ? 'anchor' : belongsToGap ? 'gap' : 'other',
                                        anchor: belongsToAnchor ? anchor : undefined,
                                        gap: belongsToGap ? gap : undefined
                                    })
                                }
                            }, 200)
                        }
                    }}
                    onDoubleClick={(e) => {
                        e.preventDefault()
                        if (anchor) {
                            // Calculate relative position within the anchor
                            const relativePosition = adjustedPosition - anchor.transcription_position
                            onElementClick({
                                type: 'anchor',
                                data: {
                                    ...anchor,
                                    position: relativePosition  // Use relative position instead of absolute
                                }
                            })
                        } else if (gap) {
                            // For gaps, calculate relative position within the gap
                            const relativePosition = adjustedPosition - gap.transcription_position
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...gap,
                                    position: relativePosition,
                                    word: word
                                }
                            })
                        } else {
                            // Create a synthetic gap for non-gap/anchor words
                            const syntheticGap: GapSequence = {
                                text: word,
                                words: [word],
                                transcription_position: adjustedPosition,
                                length: 1,
                                corrections: [],
                                preceding_anchor: null,
                                following_anchor: null,
                                reference_words: {}
                            }
                            onElementClick({
                                type: 'gap',
                                data: {
                                    ...syntheticGap,
                                    position: 0,  // Single word, so position is always 0
                                    word: word
                                }
                            })
                        }
                    }}
                >
                    {word}
                </HighlightedWord>
            )

            // After finding the anchor/gap
            if (word === 'hand') {
                console.log(`Gap boundary check for "${word}":`, {
                    gap: gap?.text,
                    words: gap?.words,
                    start: gap?.transcription_position,
                    end: gap ? gap.transcription_position + gap.length : null,
                    position: adjustedPosition,
                    isInRange: gap ? adjustedPosition >= gap.transcription_position && adjustedPosition < gap.transcription_position + gap.length : false
                });

                console.log('Sequence at 109:', data.anchor_sequences.find(a => a.transcription_position === 109));
                console.log('Sequence at 118:', data.anchor_sequences.find(a => a.transcription_position === 118));
                console.log('Sequence at 125:', data.anchor_sequences.find(a => a.transcription_position === 125));
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