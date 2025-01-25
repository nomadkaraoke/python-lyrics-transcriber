import { useEffect, useMemo, useRef } from 'react'
import { Paper, Typography, Box, Button, Tooltip } from '@mui/material'
import { AnchorMatchInfo, HighlightInfo, LyricsData, LyricsSegment } from '../types'
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
    currentSource: 'genius' | 'spotify'
    onSourceChange: (source: 'genius' | 'spotify') => void
    onDebugInfoUpdate?: (info: AnchorMatchInfo[]) => void
}

const normalizeWord = (word: string): string =>
    word.toLowerCase().replace(/[.,!?']/g, '')

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
    currentSource,
    onSourceChange,
    onDebugInfoUpdate
}: ReferenceViewProps) {
    // Create a ref to store debug info to avoid dependency cycles
    const debugInfoRef = useRef<AnchorMatchInfo[]>([])

    const { newlineInfo, newlineIndices } = useMemo(() => {
        debugInfoRef.current = corrected_segments.map(segment => ({
            segment: segment.text.trim(),
            lastWord: '',
            normalizedLastWord: '',
            overlappingAnchors: [],
            matchingGap: null,
            debugLog: []
        }));

        const newlineInfo = new Map<number, string>()
        const newlineIndices = new Set(
            corrected_segments.slice(0, -1).map((segment, segmentIndex) => {
                const segmentText = segment.text.trim()
                const segmentWords = segmentText.split(/\s+/)
                const lastWord = segmentWords[segmentWords.length - 1]
                const normalizedLastWord = normalizeWord(lastWord)

                debugInfoRef.current[segmentIndex].debugLog?.push(
                    `Processing segment: "${segmentText}"\n` +
                    `  Words: ${segmentWords.join('|')}\n` +
                    `  Last word: "${lastWord}"\n` +
                    `  Normalized last word: "${normalizedLastWord}"`
                )

                // Calculate word position
                const segmentStartWord = corrected_segments
                    .slice(0, segmentIndex)
                    .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0)
                const lastWordPosition = segmentStartWord + segmentWords.length - 1

                // Try to find the anchor containing this word
                const matchingAnchor = anchors.find(a => {
                    const start = a.transcription_position
                    const end = start + a.length - 1
                    const isMatch = lastWordPosition >= start && lastWordPosition <= end

                    debugInfoRef.current[segmentIndex].debugLog?.push(
                        `Checking anchor: "${a.text}"\n` +
                        `  Position range: ${start}-${end}\n` +
                        `  Last word position: ${lastWordPosition}\n` +
                        `  Is in range: ${isMatch}\n` +
                        `  Words: ${a.words.join('|')}`
                    )

                    return isMatch
                })

                if (matchingAnchor?.reference_positions[currentSource] !== undefined) {
                    const anchorWords = matchingAnchor.words
                    const wordIndex = anchorWords.findIndex(w => {
                        const normalizedAnchorWord = normalizeWord(w)
                        const matches = normalizedAnchorWord === normalizedLastWord

                        debugInfoRef.current[segmentIndex].debugLog?.push(
                            `Comparing words:\n` +
                            `  Anchor word: "${w}" (normalized: "${normalizedAnchorWord}")\n` +
                            `  Segment word: "${lastWord}" (normalized: "${normalizedLastWord}")\n` +
                            `  Matches: ${matches}`
                        )

                        return matches
                    })

                    if (wordIndex !== -1) {
                        const position = matchingAnchor.reference_positions[currentSource] + wordIndex

                        debugInfoRef.current[segmentIndex].debugLog?.push(
                            `Found match:\n` +
                            `  Word index in anchor: ${wordIndex}\n` +
                            `  Reference position: ${matchingAnchor.reference_positions[currentSource]}\n` +
                            `  Final position: ${position}`
                        )

                        // Update debug info with word matching details
                        debugInfoRef.current[segmentIndex] = {
                            ...debugInfoRef.current[segmentIndex],
                            lastWord,
                            normalizedLastWord,
                            overlappingAnchors: [{
                                text: matchingAnchor.text,
                                range: [matchingAnchor.transcription_position, matchingAnchor.transcription_position + matchingAnchor.length - 1],
                                words: anchorWords,
                                hasMatchingWord: true
                            }],
                            wordPositionDebug: {
                                anchorWords,
                                wordIndex,
                                referencePosition: matchingAnchor.reference_positions[currentSource],
                                finalPosition: position,
                                normalizedWords: {
                                    anchor: normalizeWord(anchorWords[wordIndex]),
                                    segment: normalizedLastWord
                                }
                            }
                        }

                        newlineInfo.set(position, segment.text.trim())
                        return position
                    }
                }

                return null
            }).filter((pos): pos is number => pos !== null && pos >= 0)
        )
        return { newlineInfo, newlineIndices }
    }, [corrected_segments, anchors, currentSource])

    // Update debug info whenever it changes
    useEffect(() => {
        onDebugInfoUpdate?.(debugInfoRef.current)
    }, [onDebugInfoUpdate])

    const renderHighlightedText = () => {
        const elements: React.ReactNode[] = []
        const words = referenceTexts[currentSource].split(/\s+/)
        let currentIndex = 0

        words.forEach((word, index) => {
            // Add the word element
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

            elements.push(
                <HighlightedWord
                    key={`${word}-${index}`}
                    shouldFlash={flashingType === 'word' && highlightedWordIndex === thisWordIndex}
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

            // Check if we need to add a newline after this word
            if (newlineIndices.has(thisWordIndex)) {
                elements.push(<br key={`br-${index}`} />)
            } else {
                // Only add space if not adding newline
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