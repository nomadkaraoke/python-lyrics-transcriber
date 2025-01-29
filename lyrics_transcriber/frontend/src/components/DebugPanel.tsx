import { Box, Typography, Accordion, AccordionSummary, AccordionDetails } from '@mui/material'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { CorrectionData } from '../types'
import { useMemo, useRef, useState } from 'react'

export interface AnchorMatchInfo {
    segment: string
    lastWord: string
    normalizedLastWord: string
    overlappingAnchors: Array<{
        text: string
        range: [number, number]
        words: string[]
        hasMatchingWord: boolean
    }>
    matchingGap: {
        text: string
        position: number
        length: number
        corrections: Array<{
            word: string
            referencePosition: number | undefined
        }>
        followingAnchor: {
            text: string
            position: number | undefined
        } | null
    } | null
    highlightDebug?: Array<{
        wordIndex: number
        refPos: number | undefined
        highlightPos: number | undefined
        anchorLength: number
        isInRange: boolean
    }>
    wordPositionDebug?: {
        anchorWords: string[]
        wordIndex: number
        referencePosition: number
        finalPosition: number
    }
    debugLog?: string[]
}

interface DebugPanelProps {
    data: CorrectionData
    currentSource: 'genius' | 'spotify'
    anchorMatchInfo: AnchorMatchInfo[]
}

export default function DebugPanel({ data, currentSource, anchorMatchInfo }: DebugPanelProps) {
    // Create a ref to hold the content div
    const contentRef = useRef<HTMLDivElement>(null)
    const [expanded, setExpanded] = useState(false)

    // Calculate newline positions for reference text using useMemo
    const { newlineInfo, newlineIndices } = useMemo(() => {
        const newlineInfo = new Map<number, string>()
        const newlineIndices = new Set(
            data.corrected_segments.slice(0, -1).map((segment, segmentIndex) => {
                const segmentWords = segment.text.trim().split(/\s+/)
                const lastWord = segmentWords[segmentWords.length - 1]

                const matchingScoredAnchor = data.anchor_sequences.find(anchor => {
                    const transcriptionStart = anchor.transcription_position
                    const transcriptionEnd = transcriptionStart + anchor.length - 1
                    const lastWordPosition = data.corrected_segments
                        .slice(0, segmentIndex)
                        .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0) + segmentWords.length - 1

                    return lastWordPosition >= transcriptionStart && lastWordPosition <= transcriptionEnd
                })

                if (!matchingScoredAnchor) {
                    console.warn(`Could not find anchor for segment end: "${segment.text.trim()}"`)
                    return null
                }

                const refPosition = matchingScoredAnchor.reference_positions[currentSource]
                if (refPosition === undefined) return null

                const wordOffsetInAnchor = matchingScoredAnchor.words.indexOf(lastWord)
                const finalPosition = refPosition + wordOffsetInAnchor

                newlineInfo.set(finalPosition, segment.text.trim())
                return finalPosition
            }).filter((pos): pos is number => pos !== null)
        )
        return { newlineInfo, newlineIndices }
    }, [data.corrected_segments, data.anchor_sequences, currentSource])

    // Memoize the first 5 segments data
    const firstFiveSegmentsData = useMemo(() =>
        data.corrected_segments.slice(0, 5).map((segment, i) => {
            const segmentWords = segment.text.trim().split(/\s+/)
            const previousWords = data.corrected_segments
                .slice(0, i)
                .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0)
            const lastWordPosition = previousWords + segmentWords.length - 1

            const matchingScoredAnchor = data.anchor_sequences.find(anchor => {
                const start = anchor.transcription_position
                const end = start + anchor.length
                return lastWordPosition >= start && lastWordPosition < end
            })

            return {
                segment,
                segmentWords,
                previousWords,
                lastWordPosition,
                matchingAnchor: matchingScoredAnchor
            }
        }), [data.corrected_segments, data.anchor_sequences])

    // Memoize relevant anchors
    const relevantAnchors = useMemo(() =>
        data.anchor_sequences
            .filter(anchor => anchor.transcription_position < 50),
        [data.anchor_sequences]
    )

    // Memoize relevant gaps
    const relevantGaps = useMemo(() =>
        data.gap_sequences.filter(g => g.transcription_position < 50),
        [data.gap_sequences]
    )

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation()  // Prevent accordion from toggling

        // Temporarily expand to get content
        setExpanded(true)

        // Use setTimeout to allow the content to render
        setTimeout(() => {
            if (contentRef.current) {
                const debugText = contentRef.current.innerText
                navigator.clipboard.writeText(debugText)

                // Restore previous state if it was collapsed
                setExpanded(false)
            }
        }, 100)
    }

    return (
        <Box sx={{ mb: 3 }}>
            <Accordion
                expanded={expanded}
                onChange={(_, isExpanded) => setExpanded(isExpanded)}
            >
                <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{
                        '& .MuiAccordionSummary-content': {
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            width: '100%'
                        }
                    }}
                >
                    <Typography>Debug Information</Typography>
                    <Box
                        onClick={(e) => e.stopPropagation()}  // Prevent accordion toggle
                        sx={{ display: 'flex', alignItems: 'center', mr: 2 }}
                    >
                        <Typography
                            component="span"
                            variant="body2"
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                cursor: 'pointer',
                                '&:hover': { opacity: 0.7 }
                            }}
                            onClick={handleCopy}
                        >
                            <ContentCopyIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
                            Copy All
                        </Typography>
                    </Box>
                </AccordionSummary>
                <AccordionDetails>
                    <Box ref={contentRef} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Debug Logs */}
                        <Box>
                            <Typography variant="h6" gutterBottom>Debug Logs (first 5 segments)</Typography>
                            <Typography component="pre" sx={{
                                fontSize: '0.75rem',
                                whiteSpace: 'pre-wrap',
                                backgroundColor: '#f5f5f5',
                                padding: 2,
                                borderRadius: 1
                            }}>
                                {anchorMatchInfo.slice(0, 5).map((info, i) =>
                                    `Segment ${i + 1}: "${info.segment}"\n` +
                                    (info.debugLog ? info.debugLog.map(log => `  ${log}`).join('\n') : '  No debug logs\n')
                                ).join('\n')}
                            </Typography>
                        </Box>

                        {/* First 5 Segments */}
                        <Box>
                            <Typography variant="h6" gutterBottom>First 5 Segments (with position details)</Typography>
                            <Typography component="pre" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                {firstFiveSegmentsData.map(({ segment, segmentWords, previousWords, lastWordPosition, matchingAnchor }, index) => {
                                    return `Segment ${index + 1}: "${segment.text.trim()}"\n` +
                                        `  Words: ${segment.words.length} (${segmentWords.length} after trimming)\n` +
                                        `  Word count before segment: ${previousWords}\n` +
                                        `  Last word position: ${lastWordPosition}\n` +
                                        `  Matching anchor: ${matchingAnchor ?
                                            `"${matchingAnchor.text}"\n    Position: ${matchingAnchor.transcription_position}\n` +
                                            `    Length: ${matchingAnchor.length}\n` +
                                            `    Reference positions: genius=${matchingAnchor.reference_positions.genius}, spotify=${matchingAnchor.reference_positions.spotify}`
                                            : 'None'}\n`
                                }).join('\n')}
                            </Typography>
                        </Box>

                        {/* Relevant Anchors */}
                        <Box>
                            <Typography variant="h6" gutterBottom>Relevant Anchors</Typography>
                            <Typography component="pre" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                {relevantAnchors.map((anchor, i) => {
                                    return `Anchor ${i}: "${anchor.text}"\n` +
                                        `  Position: ${anchor.transcription_position}\n` +
                                        `  Length: ${anchor.length}\n` +
                                        `  Words: ${anchor.words.join(' ')}\n` +
                                        `  Reference Positions: genius=${anchor.reference_positions.genius}, spotify=${anchor.reference_positions.spotify}\n`
                                }).join('\n')}
                            </Typography>
                        </Box>

                        {/* Relevant Gaps */}
                        <Box>
                            <Typography variant="h6" gutterBottom>Relevant Gaps</Typography>
                            <Typography component="pre" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                {relevantGaps.map((gap, i) => {
                                    return `Gap ${i}: "${gap.text}"\n` +
                                        `  Position: ${gap.transcription_position}\n` +
                                        `  Length: ${gap.length}\n` +
                                        `  Words: ${gap.words.join(' ')}\n` +
                                        `  Corrections: ${gap.corrections.length}\n`
                                }).join('\n')}
                            </Typography>
                        </Box>

                        {/* First 5 Newlines */}
                        <Box>
                            <Typography variant="h6" gutterBottom>First 5 Newlines (with detailed anchor matching)</Typography>
                            <Typography component="pre" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                {Array.from(newlineIndices).sort((a, b) => a - b).slice(0, 5).map(pos => {
                                    const matchingAnchor = data.anchor_sequences.find(anchor => {
                                        const start = anchor.reference_positions[currentSource]
                                        const end = start + anchor.length
                                        return pos >= start && pos < end
                                    })

                                    const matchingSegment = data.corrected_segments.find(segment =>
                                        newlineInfo.get(pos) === segment.text.trim()
                                    )

                                    const segmentIndex = matchingSegment ? data.corrected_segments.indexOf(matchingSegment) : -1
                                    const lastWord = matchingSegment?.text.trim().split(/\s+/).pop()
                                    const wordIndex = matchingAnchor?.words.indexOf(lastWord ?? '') ?? -1
                                    const expectedPosition = matchingAnchor && wordIndex !== -1 ?
                                        matchingAnchor.reference_positions[currentSource] + wordIndex :
                                        'Unknown'

                                    return `Position ${pos}: "${newlineInfo.get(pos)}"\n` +
                                        `  In Anchor: ${matchingAnchor ? `"${matchingAnchor.text}"` : 'None'}\n` +
                                        `  Anchor Position: ${matchingAnchor?.reference_positions[currentSource]}\n` +
                                        `  Matching Segment Index: ${segmentIndex}\n` +
                                        `  Expected Position in Reference: ${expectedPosition}\n`
                                }).join('\n')}
                            </Typography>
                        </Box>

                        {/* Anchor Matching Debug section */}
                        <Box>
                            <Typography variant="h6" gutterBottom>Anchor Matching Debug (first 5 segments)</Typography>
                            <Typography component="pre" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                {anchorMatchInfo.slice(0, 5).map((info, i) => `
Segment ${i}: "${info.segment}"
  Last word: "${info.lastWord}" (normalized: "${info.normalizedLastWord}")
  Debug Log:
${info.debugLog ? info.debugLog.map(log => `    ${log}`).join('\n') : '    none'}
  Overlapping anchors:
${info.overlappingAnchors.map(anchor => `    "${anchor.text}"
      Range: ${anchor.range[0]}-${anchor.range[1]}
      Words: ${anchor.words.join(', ')}
      Has matching word: ${anchor.hasMatchingWord}
`).join('\n')}
  Word Position Debug: ${info.wordPositionDebug ?
                                        `\n    Anchor words: ${info.wordPositionDebug.anchorWords.join(', ')}
    Word index in anchor: ${info.wordPositionDebug.wordIndex}
    Reference position: ${info.wordPositionDebug.referencePosition}
    Final position: ${info.wordPositionDebug.finalPosition}`
                                        : 'none'}
`).join('\n')}
                            </Typography>
                        </Box>
                    </Box>
                </AccordionDetails>
            </Accordion>
        </Box>
    )
} 